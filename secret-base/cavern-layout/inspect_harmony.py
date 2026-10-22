import bpy,bmesh,math,json
from pathlib import Path
from mathutils import Vector,Matrix
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P/'cavern-approved-terrain.blend'))
F=Matrix.Translation((21.299999237,0,0))@Matrix.Rotation(-math.atan2(12,19),4,'Z');I=F.inverted()
out={'center':{},'outer':{},'rail_components':[]}
for name in ['deck_floor_b','deck_railing_b','deck_desk_b','deck_desk_dark_b','deck_desk_metal_b','deck_desk_neon_b','deck_braziers_b','deck_brazier_flames_b']:
 o=bpy.data.objects[name];bb=[I@(o.matrix_world@Vector(v)) for v in o.bound_box]
 out['center'][name]={'bounds':[[min(v[i] for v in bb),max(v[i] for v in bb)] for i in range(3)],'materials':[]}
 for m in o.data.materials:
  p=m.node_tree.nodes.get('Principled BSDF') if m and m.use_nodes else None
  out['center'][name]['materials'].append({'name':m.name,'color':list(m.diffuse_color),'principled':{k:list(p.inputs[k].default_value) if k in ['Base Color','Emission Color'] else p.inputs[k].default_value for k in ['Base Color','Metallic','Roughness','Emission Color','Emission Strength']} if p else {}})
for role in ['Contact','Experiences','About','Workshop']:
 arr=[]
 for o in bpy.data.collections['Platform | '+role].objects:
  if o.type not in {'MESH','CURVE','FONT'}:continue
  bb=[I@(o.matrix_world@Vector(v)) for v in o.bound_box]
  arr.append({'name':o.name,'type':o.type,'bounds':[[min(v[i] for v in bb),max(v[i] for v in bb)] for i in range(3)],'materials':[m.name if m else '' for m in o.data.materials],'matrix':[list(v) for v in (I@o.matrix_world)]})
 out['outer'][role]=arr
ob=bpy.data.objects['deck_railing_b'];bm=bmesh.new();bm.from_mesh(ob.data);seen=set(bm.verts)
while seen:
 root=seen.pop();stack=[root];comp=[root]
 while stack:
  v=stack.pop()
  for e in v.link_edges:
   q=e.other_vert(v)
   if q in seen:seen.remove(q);stack.append(q);comp.append(q)
 ps=[I@(ob.matrix_world@v.co) for v in comp]
 mid=sum(ps,Vector())/len(ps);bb=[[min(p[i] for p in ps),max(p[i] for p in ps)] for i in range(3)]
 out['rail_components'].append({'mid':list(mid),'bounds':bb,'count':len(comp),'angle':math.degrees(math.atan2(mid.y,mid.x))})
bm.free()
(P/'harmony-inventory.json').write_text(json.dumps(out,indent=2))
print('CENTER',json.dumps(out['center']))
for role,arr in out['outer'].items():
 print('PLATFORM',role)
 for o in arr:
  if any(s in o['name'] for s in ['structural frame','floor tile','floor disc','deck slab','solid slab','Nameplate','nameplate']) and not '.0' in o['name']:print(json.dumps(o))
print('RAIL',json.dumps(out['rail_components']))
