"""Raised, denser cave teeth and straighter side walls; retain island assets."""
import bpy,math,random,os
from mathutils import Vector
random.seed(611)
ROOT='/Users/danielku/mywebsite/secret-base/'
backup=ROOT+'rock-review/before-raised-cave-spikes.blend'
if not os.path.exists(backup):bpy.ops.wm.save_as_mainfile(filepath=backup,copy=True)
s=bpy.context.scene;cam=s.camera;Q=cam.matrix_world.to_quaternion()
R=Q@Vector((1,0,0));U=Q@Vector((0,1,0));D=Q@Vector((0,0,1));C=Vector((21,-.3,4))
def p(x,y,d):return C+R*x+U*y+D*d
def smooth(t):
 t=max(0,min(1,t));return t*t*(3-2*t)
def deform(v):
 q=v-C;x=q.dot(R);y=q.dot(U);d=q.dot(D)
 # Remove the inward swelling of walls, retaining a few broad planar creases.
 if abs(x)>8.4 and y<5.8:
  front=max(0,(d+3)/12)
  wall=11.0+front*3.1+.13*math.sin(d*.75)+.08*math.sin(y*.8)
  t=smooth((abs(x)-8.4)/1.9)*(1-smooth((y-4.1)/1.7))
  x=x*(1-t)+math.copysign(wall,x)*t
 # Raise existing low roof folds and teeth, with a gradual blend at the sides.
 if y>-.2 and abs(x)<10.3:
  y+=1.12*smooth((y+.2)/2.3)*(1-smooth((abs(x)-8.3)/2))
 return p(x,y,d)
vault=bpy.data.objects['Cave | continuous sculpted walls and hanging roof']
for o in [vault]+([bpy.data.objects['Cave | broad stone relief']] if bpy.data.objects.get('Cave | broad stone relief') else []):
 if o.get('raised_roof_wall_pass'):continue
 for v in o.data.vertices:v.co=deform(v.co)
 o.data.update();o['raised_roof_wall_pass']=True
coll=bpy.data.collections.get('Cave_Ceiling_Teeth')
if coll:
 for o in list(coll.objects):bpy.data.objects.remove(o,do_unlink=True)
else:
 coll=bpy.data.collections.new('Cave_Ceiling_Teeth');s.collection.children.link(coll)
roof=[]
for v in vault.data.vertices:
 q=v.co-C
 if q.dot(U)>6:roof.append((v.co.copy(),q.dot(R),q.dot(U),q.dot(D)))
vs=[];fs=[]
for i in range(30):
 x=-9.5+(i%15)*19/14+random.uniform(-.2,.2);d=(-2.4 if i<15 else -6)+random.uniform(-.7,.7)
 root,rx,ry,rd=min(roof,key=lambda e:(e[1]-x)**2+(e[3]-d)**2)
 length=min(random.uniform(.95,1.9),max(.6,ry-5.75))
 width=random.uniform(.24,.49);depth=random.uniform(.3,.6);n=7;start=len(vs)
 phases=[random.uniform(.85,1.15) for _ in range(n)]
 for frac,drop in [(1.18,-.18),(.73,.22),(.3,.67)]:
  for j in range(n):
   a=math.tau*j/n
   vs.append(root+R*(math.cos(a)*width*frac*phases[j])+D*(math.sin(a)*depth*frac*phases[j])-U*(length*drop))
 for ring in range(2):
  for j in range(n):fs.append((start+ring*n+j,start+ring*n+(j+1)%n,start+(ring+1)*n+(j+1)%n,start+(ring+1)*n+j))
 tip=len(vs);vs.append(root-U*length+R*random.uniform(-.12,.12))
 for j in range(n):fs.append((start+2*n+j,start+2*n+(j+1)%n,tip))
me=bpy.data.meshes.new('Raised hanging cave stone');me.from_pydata(vs,[],fs);me.update()
o=bpy.data.objects.new('Cave | thirty raised hanging formations',me);coll.objects.link(o)
for m in vault.data.materials:me.materials.append(m)
for poly in me.polygons:poly.material_index=len(me.materials)//2
import bmesh
bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
def area(name,loc,target,power,size):
 data=bpy.data.lights.new(name,'AREA');data.energy=power;data.color=(.16,.42,.85);data.shape='DISK';data.size=size
 o=bpy.data.objects.new(name,data);coll.objects.link(o);o.location=loc;o.rotation_euler=(target-o.location).to_track_quat('-Z','Y').to_euler()
area('Cave | raised ceiling blue fill',p(0,3.5,3),p(0,8,-3),900,8)
area('Cave | west hanging stone light',p(-7,3,1),p(-7,7.5,-3),400,5)
area('Cave | east hanging stone light',p(7,3,1),p(7,7.5,-3),400,5)
bpy.context.view_layer.update();bpy.ops.wm.save_as_mainfile(filepath=ROOT+'base.blend')
result={'added_hanging_formations':30,'existing_roof_raised':1.12,'side_walls':'straightened and recessed'}
