import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
Q=Path(__file__).resolve().parent;P=Q.parent
FRAME=Matrix(json.loads((P/'surface-before.json').read_text())['frame']);INV=FRAME.inverted();floor=bpy.data.objects['Front left | beveled rectangle landing'];COL=bpy.data.collections['167 | Left platform cliff supports'];ARCH=bpy.data.collections['Archive | left supports before 70 percent rock'];BOTTOM=2.156750679
r=bpy.data.objects['150 | continuous cave with oblique carved rooms'];ev=r.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();rt=BVHTree.FromPolygons([INV@ev.matrix_world@v.co for v in me.vertices],[list(p.vertices) for p in me.polygons]);ev.to_mesh_clear()
report=json.loads((Q/'build-report.json').read_text())
for o in list(COL.objects):
 if 'short front' in o.name:ARCH.objects.link(o);COL.objects.unlink(o)
report['connections']=[c for c in report['connections'] if c['side']=='long']
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


for number,x in enumerate([1.3,2.1,2.9,3.7],1):
 end=Vector((x,.12,BOTTOM-.075));chosen=None
 for z in [.95,1.15,1.35,1.50]:
  hit,n,_,_=rt.ray_cast(Vector((x,-3,z)),Vector((0,1,0)),7)
  if hit is None:continue
  if n.y>0:n=-n
  anchor=hit+n*.05;d=(end-anchor).normalized();h=rt.ray_cast(anchor+d*.08,d,(end-anchor).length-.12)[0]
  if h is None and rt.find_nearest(anchor.lerp(end,.5))[3]>.095:
   chosen=(hit,n,anchor);break
 assert chosen is not None,x
 hit,n,anchor=chosen;axis=Vector((1,0,0));u=(axis-n*axis.dot(n)).normalized()*.16;v=n.cross(u).normalized()*.19
 label='front short edge %02d'%number
 plate(label+' rock shoe',hit+n*.025,u,v,n)
 ob=beam(label+' diagonal',anchor,end)
 beam(label+' underside bearer',(end.x,hit.y+.15,BOTTOM-.045),(end.x,.12,BOTTOM-.045),.115,.16)
 plate(label+' rim plate',(end.x,.12,BOTTOM-.005),(.15,0,0),(0,.10,0),(0,0,1))
 report['connections'].append({'name':ob.name,'side':'short','anchor':list(anchor),'top':list(end),'length':(end-anchor).length})
bpy.context.view_layer.update();(Q/'build-report.json').write_text(json.dumps(report,indent=2));bpy.ops.wm.save_as_mainfile(filepath=str(Q/'expanded-foundation-preview.blend'),copy=True,compress=True)
result={'front_short_braces':[c for c in report['connections'] if c['side']=='short']}
