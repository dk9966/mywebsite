import bpy,json,math
import numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
Q=Path(__file__).resolve().parent;P=Q.parent
f=Matrix(json.loads((P/'surface-before.json').read_text())['frame']);iv=f.inverted();r=bpy.data.objects['150 | continuous cave with oblique carved rooms'];mx=iv@r.matrix_world;ix=mx.inverted();key=r.data.shape_keys.key_blocks['Left landing | 70 percent bearing foundation']
a=np.array([tuple(mx@v.co) for v in key.data]);edges=np.array([tuple(e.vertices) for e in r.data.edges]);i=np.r_[edges[:,0],edges[:,1]];j=np.r_[edges[:,1],edges[:,0]];degree=np.bincount(i,minlength=len(a))
def sm(t):
 t=np.clip(t,0,1);return t*t*(3-2*t)
x,y,z=a.T
w=sm((x+2)/1.2)*sm((5.2-x)/.9)*sm((y+2.4)/.8)*sm((2.8-y)/1.2)*sm((z+5)/1.3)*sm((1.95-z)/.65)
for step in range(60):
 avg=np.column_stack([np.bincount(i,weights=a[j,k],minlength=len(a))/np.maximum(degree,1) for k in range(3)])
 a+=(avg-a)*(w*.43)[:,None]
for v,p in zip(key.data,a):v.co=ix@Vector(p)
bpy.context.view_layer.update()
ev=r.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();rt=BVHTree.FromPolygons([iv@ev.matrix_world@v.co for v in me.vertices],[list(p.vertices) for p in me.polygons]);ev.to_mesh_clear()
report=json.loads((Q/'build-report.json').read_text());BOTTOM=2.156750679

def setcoords(ob,ps):
 m=(iv@ob.matrix_world).inverted()
 for v,p in zip(ob.data.vertices,ps):v.co=m@p
 ob.data.update()
def beam_coords(a,b,width,depth):
 a,b=Vector(a),Vector(b);axis=(b-a).normalized();helper=Vector((0,0,1)) if abs(axis.z)<.95 else Vector((0,1,0));u=axis.cross(helper).normalized()*width/2;v=axis.cross(u).normalized()*depth/2
 return [p+su*u+sv*v for p in (a,b) for su,sv in [(-1,-1),(1,-1),(1,1),(-1,1)]]
for side,positions in [('long',[1.85,5.15,8.45,11.8]),('front',[1.25,3.25])]:
 for num,pos in enumerate(positions,1):
  label='%s %02d'%(side,num);zc=.62+.05*math.sin(pos) if side=='long' else .70
  origin=Vector((7,pos,zc)) if side=='long' else Vector((pos,-2.5,zc));direction=Vector((-1,0,0)) if side=='long' else Vector((0,1,0));hit,n,_,_=rt.ray_cast(origin,direction,12)
  assert hit is not None
  if n.dot(direction)>0:n=-n
  n.normalize();axis=Vector((0,1,0)) if abs(n.x)>.5 else Vector((1,0,0));u=(axis-n*axis.dot(n)).normalized()*.16;v=n.cross(u).normalized()*.19;center=hit+n*.025;anchor=hit+n*.05
  shoe=bpy.data.objects['Left platform | short '+label+' rock shoe'];setcoords(shoe,[center+n*d+u*su+v*sv for d in [-.045,.045] for su,sv in [(-1,-1),(1,-1),(1,1),(-1,1)]])
  for letter in 'AB':
   name='Left platform | short '+label+' diagonal '+letter;c=next(c for c in report['connections'] if c['name']==name);top=Vector(c['top']);setcoords(bpy.data.objects[name],beam_coords(anchor,top,.12,.15));c['anchor']=list(anchor);c['length']=(top-anchor).length
   start=Vector((hit.x+.15,top.y,BOTTOM-.045)) if side=='long' else Vector((top.x,hit.y+.17,BOTTOM-.045));end=Vector((top.x,top.y,BOTTOM-.045));setcoords(bpy.data.objects['Left platform | short '+label+' cross bearer '+letter],beam_coords(start,end,.115,.16))
report['new_long_brace_length_range']=[min(c['length'] for c in report['connections'] if c['side']=='long'),max(c['length'] for c in report['connections'] if c['side']=='long')]
(Q/'build-report.json').write_text(json.dumps(report,indent=2));bpy.context.view_layer.update();bpy.ops.wm.save_as_mainfile(filepath=str(Q/'expanded-foundation-preview.blend'),copy=True,compress=True)
result={'relaxed_transition_vertices':int(np.count_nonzero(w)),'reseated_braces':12}
