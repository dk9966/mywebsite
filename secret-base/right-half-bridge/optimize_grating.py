"""Reuse the scene's packed alpha/normal grating on sparse depth sheets."""
import bpy, json
from pathlib import Path
P=Path(__file__).resolve().parent
S=bpy.context.scene
source=bpy.data.objects['Rear left | bridge bay 01 open grating']
material=source.data.materials[0]
assert source.get('texture_grating')
# Read metres per UV unit from the reference so the grid density is unchanged.
me=source.data;face=me.polygons[0];loops=list(face.loop_indices)
a,b=loops[0],loops[1]
span_u=abs((me.vertices[me.loops[a].vertex_index].co.x-me.vertices[me.loops[b].vertex_index].co.x)/(me.uv_layers.active.data[a].uv.x-me.uv_layers.active.data[b].uv.x))
a,b=loops[0],loops[4]
span_v=abs((me.vertices[me.loops[a].vertex_index].co.y-me.vertices[me.loops[b].vertex_index].co.y)/(me.uv_layers.active.data[a].uv.y-me.uv_layers.active.data[b].uv.y))
report=[]
for ob in bpy.data.collections['181 | Right radial half bridge'].objects:
 if 'open welded grating' not in ob.name:continue
 assert not ob.get('texture_grating')
 old=ob.data;old.calc_loop_triangles();before=len(old.loop_triangles)
 x0,x1=min(v.co.x for v in old.vertices),max(v.co.x for v in old.vertices)
 y0,y1=min(v.co.y for v in old.vertices),max(v.co.y for v in old.vertices)
 z=max(v.co.z for v in old.vertices);mid=(x0+x1)/2
 closed='bay 01' in ob.name
 layers=3 if closed else 5
 verts=[];faces=[]
 for k in range(layers):
  zz=z-.022*k/(layers-1);offset=len(verts)
  corners=[(x0,y0),(x1,y0),(x1,y1),(x0,y1)]
  verts.extend([(x,y,zz) for x,y in corners]);faces.append(tuple(offset+i for i in (0,1,2,3)))
  if closed:
   verts.extend([(x,y,zz-.0008) for x,y in corners])
   faces.extend([tuple(offset+i for i in f) for f in [(7,6,5,4),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)]])
 new=bpy.data.meshes.new(ob.name+' | optimized textured depth sheets');new.from_pydata(verts,[],faces);new.update()
 uv=new.uv_layers.new(name='GratingUV')
 for loop in new.loops:
  x,y,_=new.vertices[loop.vertex_index].co
  uv.data[loop.index].uv=(.5-y/span_u,.5+(x-mid)/span_v)
 new.materials.append(material);ob.data=new
 if not closed:
  for mod in list(ob.modifiers):
   if mod.type=='BOOLEAN':ob.modifiers.remove(mod)
 ob['texture_grating']=True;ob['grating_depth_sheets']=layers;ob['grating_before_triangles']=before
 ob['grating_uv_direction']='Fabrication axes; shared packed rear bridge texture at original world density'
 bpy.context.view_layer.update();e=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());ev=e.to_mesh();ev.calc_loop_triangles()
 assert len(ev.polygons)>0
 report.append({'name':ob.name,'before_triangles':before,'after_triangles':len(ev.loop_triangles),'depth_sheets':layers,'material':material.name})
 e.to_mesh_clear()
images=[n.image for n in material.node_tree.nodes if n.type=='TEX_IMAGE']
assert len(images)==2 and all(im.packed_file for im in images)
assert all(o.get('texture_grating') for o in bpy.data.collections['181 | Right radial half bridge'].objects if 'open welded grating' in o.name)
result={'objects':report,'before_triangles':sum(r['before_triangles'] for r in report),'after_triangles':sum(r['after_triangles'] for r in report),'reuses_packed_images':[im.name for im in images],'added_images':0}
(P/'texture-verification.json').write_text(json.dumps(result,indent=2))
S['right_half_bridge']='Radial half-length bridge beside the table; optimized alpha/normal grating sharing the existing packed maps.'
