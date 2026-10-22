import bpy,bmesh,json,math,hashlib
import numpy as np
from pathlib import Path
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
Q=Path(__file__).resolve().parent;P=Q.parent;S=bpy.context.scene
rock=bpy.data.objects['150 | continuous cave with oblique carved rooms'];floor=bpy.data.objects['Front left | beveled rectangle landing'];COL=bpy.data.collections['167 | Left platform cliff supports']
FRAME=Matrix(json.loads((P/'surface-before.json').read_text())['frame']);INV=FRAME.inverted();mx=INV@rock.matrix_world;ix=mx.inverted()
WIDTH,LENGTH=json.loads((P/'surface-before.json').read_text())['dimensions'];BOTTOM=min((floor.matrix_world@v.co).z for v in floor.data.vertices);TOP=BOTTOM+.38
if bpy.context.mode!='OBJECT':bpy.ops.object.mode_set(mode='OBJECT')
def sig(o):
 h=hashlib.sha256(repr([list(r) for r in o.matrix_world]).encode())
 if o.type=='MESH':
  a=np.empty(len(o.data.vertices)*3,dtype=np.float32);o.data.vertices.foreach_get('co',a);h.update(a.tobytes())
 return h.hexdigest()
protected={o.name:sig(o) for o in S.objects if o!=rock and o.name not in COL.objects}
(Q/'protected-originals.json').write_text(json.dumps(protected))
# Keep the previous sculpt in its own data block and in the backup file.
old=rock.data;old.use_fake_user=True;rock['before_70_percent_mesh']=old.name;rock.data=old.copy();rock.data.name='Cave | 70 percent left platform foundation'
key=rock.shape_key_add(name='Left landing | 70 percent bearing foundation',from_mix=True)
for k in rock.data.shape_keys.key_blocks:
 if k not in (rock.data.shape_keys.key_blocks[0],key):k.value=0
key.value=1
source=np.array([tuple(mx@v.co) for v in key.data])
def sm(t):
 t=np.clip(t,0,1);return t*t*(3-2*t)
x,y,z=source.T
weight=sm((z+5.3)/4.8)*sm((2.25-z)/.06)*sm((y+3)/1.2)*sm((15-y)/1.2)*sm((3-x)/.5)*sm((x+.12)/.12)
front=sm((x-.06)/.6)*sm((2.8-y)/2.8)*sm((y+2.0)/1.3)*weight

def tree(ob):
 deps=bpy.context.evaluated_depsgraph_get();ev=ob.evaluated_get(deps);me=ev.to_mesh();t=BVHTree.FromPolygons([INV@ev.matrix_world@v.co for v in me.vertices],[list(f.vertices) for f in me.polygons]);ev.to_mesh_clear();return t
ft=tree(floor)
samples=[]
for yy in np.arange(.045,LENGTH,.09):
 for xx in np.arange(.045,WIDTH,.09):
  p=Vector((float(xx),float(yy),TOP+.15))
  if ft.ray_cast(p,Vector((0,0,-1)),.8)[0] is not None:samples.append(p)

def apply_scale(scale):
 a=source.copy();a[:,0]+=x*(scale-1)*weight;a[:,1]+=.60*front
 for v,p in zip(key.data,a):v.co=ix@Vector(p)
 rock.data.update();bpy.context.view_layer.update()

def coverage(rt):
 support=0
 for p in samples:
  h=rt.ray_cast(p,Vector((0,0,-1)),.75)[0]
  if h is not None and BOTTOM-.025<=h.z<=TOP+.03:support+=1
 return support/len(samples)
lo,hi=1.7,2.8;passes=[]
for iteration in range(9):
 scale=(lo+hi)/2;apply_scale(scale);ratio=coverage(tree(rock));passes.append([scale,ratio])
 if ratio<.70:lo=scale
 else:hi=scale
scale=(lo+hi)/2;apply_scale(scale);rt=tree(rock);ratio=coverage(rt)
# Archive long braces and their attachment details, retaining the perimeter bearer.
ARCH=bpy.data.collections.new('Archive | left supports before 70 percent rock');S.collection.children.link(ARCH);ARCH.hide_viewport=ARCH.hide_render=True
old_lengths=[]
for o in list(COL.objects):
 if 'perimeter underside bearer' in o.name:continue
 if 'splayed diagonal bracket' in o.name:
  ps=[INV@o.matrix_world@v.co for v in o.data.vertices];old_lengths.append(((sum(ps[4:],Vector())-sum(ps[:4],Vector()))/4).length)
 ARCH.objects.link(o);COL.objects.unlink(o)
steel=bpy.data.materials['Metal | dark structural steel'];trim=bpy.data.materials['Lower | aligned architectural trim'];made=[]
faces=[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
def mesh(name,verts,material):
 me=bpy.data.meshes.new('Left platform | '+name);me.from_pydata(verts,[],faces);me.materials.append(material);me.update();bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
 o=bpy.data.objects.new('Left platform | '+name,me);COL.objects.link(o);o.parent=floor;o.matrix_world=FRAME
 m=o.modifiers.new('Small fabricated edge','BEVEL');m.width=.004;m.segments=2;o.modifiers.new('Weighted surface normals','WEIGHTED_NORMAL');made.append(o);return o

def beam(name,a,b,width=.12,depth=.15):
 a,b=Vector(a),Vector(b);axis=(b-a).normalized();helper=Vector((0,0,1)) if abs(axis.z)<.95 else Vector((0,1,0));u=axis.cross(helper).normalized()*width/2;v=axis.cross(u).normalized()*depth/2
 return mesh(name,[tuple(p+su*u+sv*v) for p in (a,b) for su,sv in [(-1,-1),(1,-1),(1,1),(-1,1)]],steel)

def plate(name,c,u,v,n):
 c,u,v,n=map(Vector,(c,u,v,n));return mesh(name,[tuple(c+n*d+u*su+v*sv) for d in (-.045,.045) for su,sv in [(-1,-1),(1,-1),(1,1),(-1,1)]],trim)

connections=[]
def bracket_pair(label,hit,n,ends,bearer_starts):
 n=n.normalized();axis=Vector((0,1,0)) if abs(n.x)>.5 else Vector((1,0,0));u=(axis-n*axis.dot(n)).normalized()*.16;v=n.cross(u).normalized()*.19
 anchor=hit+n*.025;plate('short '+label+' rock shoe',anchor,u,v,n)
 for j,(end,start) in enumerate(zip(ends,bearer_starts)):
  end=Vector(end);a=anchor+n*.025;name='short '+label+' diagonal '+'AB'[j]
  beam(name,a,end)
  beam('short '+label+' cross bearer '+'AB'[j],start,(end.x,end.y,BOTTOM-.045),.115,.16)
  plate('short '+label+' rim plate '+'AB'[j],(end.x,end.y,BOTTOM-.005),(.15,0,0),(0,.13,0),(0,0,1))
  connections.append({'name':'Left platform | '+name,'side':'long' if label.startswith('long') else 'short','anchor':list(a),'top':list(end),'length':(end-a).length})

for number,yc in enumerate([1.85,5.15,8.45,11.8],1):
 zc=.62+.05*math.sin(yc)
 hit,n,_,_=rt.ray_cast(Vector((7,yc,zc)),Vector((-1,0,0)),12);assert hit is not None
 if n.x<0:n=-n
 ends=[];starts=[]
 for dy in [-.43,.43]:
  ey=yc+dy;rim=WIDTH-max(0,1.6207-ey)-max(0,ey-(LENGTH-1.6207));ex=rim-.15
  ends.append((ex,ey,BOTTOM-.075));starts.append((min(hit.x+.15,ex-.2),ey,BOTTOM-.045))
 bracket_pair('long %02d'%number,hit,n,ends,starts)
# Two paired short-edge supports, perpendicular to the front edge.
for number,xc in enumerate([1.25,3.25],1):
 zc=.70
 hit,n,_,_=rt.ray_cast(Vector((xc,-2.5,zc)),Vector((0,1,0)),5);assert hit is not None,(xc,zc)
 if n.y>0:n=-n
 ends=[(xc+dx,.11,BOTTOM-.075) for dx in [-.33,.33]]
 starts=[(e[0],hit.y+.17,BOTTOM-.045) for e in ends]
 bracket_pair('front %02d'%number,hit,n,ends,starts)

bpy.context.view_layer.update()
assert all(sig(bpy.data.objects[n])==h for n,h in protected.items()),'Unrelated geometry changed'
report={'target_coverage':.70,'measured_coverage':ratio,'sample_count':len(samples),'expansion_factor':scale,'coverage_iterations':passes,'old_long_brace_length_range':[min(old_lengths),max(old_lengths)],'new_long_brace_length_range':[min(c['length'] for c in connections if c['side']=='long'),max(c['length'] for c in connections if c['side']=='long')],'connections':connections,'new_parts':len(made),'unrelated_geometry_preserved':True,'shape_key':key.name}
(Q/'build-report.json').write_text(json.dumps(report,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(Q/'expanded-foundation-preview.blend'),copy=True,compress=True)
result=report
