import bpy,math,random,bmesh,ast
from mathutils import Vector,noise
from mathutils.bvhtree import BVHTree
random.seed(692)
s=bpy.context.scene;col=bpy.data.collections['Natural_Wired_Cavern'];base=bpy.data.objects['Cave_Composition_Camera'];q=base.matrix_world.to_quaternion();R=q@Vector((1,0,0));H=q@Vector((0,0,1));H.z=0;H.normalize();Z=Vector((0,0,1));center=Vector((21,0,0))
rock=bpy.data.materials['Natural cave | weathered slate'];metal=bpy.data.materials['Natural cave | dark inset alloy'];trim=bpy.data.materials['Natural cave | machined trim'];cyan=bpy.data.materials['Natural cave | cyan wire'];black=bpy.data.materials['Natural cave | recess darkness']
tree=ast.parse(open('/Users/danielku/mywebsite/secret-base/build_natural_wired_cave.py').read());exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['w','mesh','area','tube','cuboid']],type_ignores=[]),'helpers','exec'))
# Extend the entrance into a natural arched approach so the interior camera is enclosed.
vs=[];fs=[];NA=91;ND=28
for j in range(ND):
 d=12+j*.85
 for k in range(NA):
  a=-math.pi/2+k*math.pi/(NA-1);x=math.sin(a)*(17.5+.045*(d-12));z=-10+30*math.cos(a)
  n=noise.fractal(Vector((x*.22,d*.22,z*.2)),1,2,3);x+=math.sin(a)*n;z+=n*.8
  vs.append(w(x,d,z))
for j in range(ND-1):
 for k in range(NA-1):
  a=j*NA+k;fs.extend([(a,a+1,a+NA),(a+1,a+NA+1,a+NA)])
mesh('Natural cave | enclosing arched approach',vs,fs)
# Remove concentric tunnel geometry by adding natural asymmetry and a pronounced bend.
shell=bpy.data.objects['Natural cave | continuous enclosing wall and vaulted roof'];N=50;start=len(shell.data.vertices)-1250
c1=sum((shell.data.vertices[start+k].co for k in range(N)),Vector())/N;c0=c1+H*.65
for v in list(shell.data.vertices)[:start]:
 rel=v.co-c0;x=rel.dot(R);z=rel.z;d=rel.dot(H)
 if abs(d)<3 and abs(x)<7 and abs(z)<7:
  f=math.exp(-(x*x+z*z)/34)*math.exp(-d*d/5);v.co+=R*(z*.17*f)+Z*(.4*math.sin(x*.65)*f)
for j in range(25):
 ids=range(start+j*N,start+(j+1)*N);cc=sum((shell.data.vertices[i].co for i in ids),Vector())/N;t=(j+1)*.65
 for i in ids:
  v=shell.data.vertices[i];rel=v.co-cc;x=rel.dot(R);z=rel.z;a=math.atan2(z,x);r=1+.13*math.sin(a*3+t*.4)+.06*math.sin(a*7-t*.3)
  v.co=cc+R*(x*r+z*.16)+Z*(z*r*.91)+H*rel.dot(H)+R*(max(0,t-2)**2*.055)+Z*(.15*math.sin(t*.6))
shell.data.update()
# Quiet the brighter roof wash and the tunnel's distant cap.
for o in col.objects:
 if o.type=='LIGHT':
  if any(k in o.name for k in ['overhead reflected blue','broad rear reflected light']):o.data.energy*=.65
  if 'passage far glow' in o.name:o.data.energy=120
  if 'passage inner bounce' in o.name:o.data.energy=160
for n in bpy.data.materials['Natural cave | passage haze'].node_tree.nodes:
 if n.type=='PRINCIPLED_VOLUME':n.inputs['Emission Strength'].default_value=.003;n.inputs['Density'].default_value=.022
# Natural asymmetrical basal buttresses, rather than vertical concrete-like plinths.
for i,o in enumerate([o for o in col.objects if o.type=='MESH' and 'bedrock buttress' in o.name]):
 ctr=sum((v.co for v in o.data.vertices),Vector())/len(o.data.vertices);phase=i*1.7+.6
 for v in o.data.vertices:
  if v.co.z<-.4:
   a=math.atan2(v.co.y-ctr.y,v.co.x-ctr.x);t=min(1,(-v.co.z-.4)/4);mult=1+t*(.2*math.cos(a-phase)+.1*math.sin(a*3+v.co.z*.3));v.co.x=ctr.x+(v.co.x-ctr.x)*mult;v.co.y=ctr.y+(v.co.y-ctr.y)*mult
 o.data.update()
# Replace buried service equipment with three deliberately fitted wall inserts.
for o in list(col.objects):
 if any(k in o.name for k in ['inset service panel','panel armored jamb','cyan ventilation aperture','small status indicator','wall following cyan cable']):bpy.data.objects.remove(o,do_unlink=True)
bvh=BVHTree.FromPolygons([v.co for v in shell.data.vertices],[list(f.vertices) for f in shell.data.polygons])
def hitwall(a,z):
 direction=R*math.sin(a)+H*math.cos(a);hit,n,idx,dist=bvh.ray_cast(w(0,0,z),direction,40)
 if hit is None:return None,None
 if n.dot(direction)>0:n=-n
 return hit,n.normalized()
for a,z,width,height in [(1.27,5.5,1.0,3.7),(4.9,5,1.0,4),(2.28,8,.7,3)]:
 hit,N=hitwall(a,z)
 if hit is None:continue
 X=Z.cross(N).normalized();Y=N.cross(X).normalized();hit+=N*.17
 cuboid('Natural cave | fitted wall service cassette',hit,X,Y,N,(width,height,.18),metal)
 for side in [-1,1]:cuboid('Natural cave | cassette frame',hit+X*(side*width*.49)+N*.1,X,Y,N,(.1,height+.12,.22),trim)
 for k in range(4):cuboid('Natural cave | fitted cyan slit',hit+X*((k-1.5)*width*.13)+Y*height*.28+N*.101,X,Y,N,(.02,height*.13,.02),cyan)
 for k in range(5):cuboid('Natural cave | fitted status light',hit-X*width*.2+Y*(-height*.33+k*height*.11)+N*.102,X,Y,N,(.04,.07,.02),cyan)
for a,top,length in [(1.35,13,5),(2.6,16,4),(4.55,14,5)]:
 points=[]
 for k in range(54):
  t=k/53;aa=a+(.02 if .28<t<.55 else(-.014 if t>.7 else 0));hit,N=hitwall(aa,top-length*t)
  if hit is not None:points.append(hit+N*.025)
 if points:tube('Natural cave | seated wall cyan vein',points,.012,cyan)
# Broader and broken floor formations mixed with the narrow growths.
for i,o in enumerate([o for o in col.objects if o.type=='MESH' and 'rooted mineral formation' in o.name]):
 if i%3==0:
  cc=sum((v.co for v in o.data.vertices),Vector())/len(o.data.vertices);zmin=min(v.co.z for v in o.data.vertices)
  for v in o.data.vertices:v.co.x=cc.x+(v.co.x-cc.x)*1.65;v.co.y=cc.y+(v.co.y-cc.y)*1.65;v.co.z=zmin+(v.co.z-zmin)*.6
  o.data.update()
area('Natural cave | diffuse lower chamber light',w(0,6,-4),w(0,-2,-10),550,10,(.15,.33,.54))
s.render.filepath='/Users/danielku/mywebsite/secret-base/wired-review/natural-cave-5.png'
bpy.ops.wm.save_as_mainfile(filepath='/Users/danielku/mywebsite/secret-base/base.blend')
