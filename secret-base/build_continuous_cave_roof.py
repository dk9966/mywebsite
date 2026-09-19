"""World-space continuous cave roof with shared-vertex downward formations."""
import bpy,math,random,os,bmesh
from mathutils import Vector,noise
random.seed(1246)
ROOT='/Users/danielku/mywebsite/secret-base/'
backup=ROOT+'rock-review/before-continuous-roof.blend'
if not os.path.exists(backup):bpy.ops.wm.save_as_mainfile(filepath=backup,copy=True)
s=bpy.context.scene
col=bpy.data.collections.get('Cave_Continuous_Roof')
if col:
 for o in list(col.objects):bpy.data.objects.remove(o,do_unlink=True)
else:
 col=bpy.data.collections.new('Cave_Continuous_Roof');s.collection.children.link(col)
oldcam=bpy.data.objects['Cave_Composition_Camera'];q=oldcam.matrix_world.to_quaternion()
R=q@Vector((1,0,0));R.z=0;R.normalize();F=Vector((-R.y,R.x,0));C=Vector((21,1,0))
def p(x,y,z):return C+R*x+F*y+Vector((0,0,z))
# Roof spans the station footprint, the foreground, and both sides, independent of view.
nx=49;ny=53;vs=[];fs=[]
for j in range(ny):
 y=-23+j*.9
 for i in range(nx):
  x=-21.6+i*.9
  z=13.1+.55*math.sin(x*.25)+.45*math.cos(y*.32)+noise.noise(Vector((x*.33,y*.33,7)))*.45
  vs.append(p(x+random.uniform(-.10,.10),y+random.uniform(-.10,.10),z))
occupied=set();patches=[]
for j in range(3,ny-4,4):
 for i in range(3,nx-4,4):
  if random.random()<.16:continue
  ii=i+random.choice([-1,0,1]);jj=j+random.choice([-1,0,1]);size=2
  cells={(y,x) for y in range(jj,jj+size) for x in range(ii,ii+size)}
  if cells&occupied:continue
  occupied.update(cells)
  boundary=[jj*nx+x for x in range(ii,ii+size)]
  boundary += [y*nx+ii+size for y in range(jj,jj+size)]
  boundary += [(jj+size)*nx+x for x in range(ii+size,ii,-1)]
  boundary += [y*nx+ii for y in range(jj+size,jj,-1)]
  patches.append(boundary)
for j in range(ny-1):
 for i in range(nx-1):
  if (j,i) in occupied:continue
  a=j*nx+i;b=a+1;c=a+nx;d=c+1
  fs.extend([(a,c,b),(b,c,d)])
for boundary in patches:
 center=sum((vs[i] for i in boundary),Vector())/len(boundary)
 length=min(random.uniform(1.0,2.35),center.z-10.55)
 prev=boundary
 for scale,drop in [(.65,.25),(.23,.72)]:
  ring=[]
  for i in boundary:
   ring.append(len(vs));vs.append(center+(vs[i]-center)*scale-Vector((0,0,length*drop)))
  for k in range(len(boundary)):
   a=prev[k];b=prev[(k+1)%len(prev)];c=ring[k];d=ring[(k+1)%len(ring)]
   fs.extend([(a,c,b),(b,c,d)])
  prev=ring
 tip=len(vs);vs.append(center+R*random.uniform(-.14,.14)-Vector((0,0,length)))
 for k in range(len(prev)):fs.append((prev[k],tip,prev[(k+1)%len(prev)]))
# Closed upper shell: sides and a solid top prevent one-sided roof illusion.
boundary=list(range(nx)) + [j*nx+nx-1 for j in range(1,ny)] + [(ny-1)*nx+i for i in range(nx-2,-1,-1)] + [j*nx for j in range(ny-2,0,-1)]
upper=[]
for i in boundary:
 upper.append(len(vs));v=vs[i].copy();v.z=16.0;vs.append(v)
for k in range(len(boundary)):fs.append((boundary[k],boundary[(k+1)%len(boundary)],upper[(k+1)%len(upper)],upper[k]))
fs.append(tuple(upper))
me=bpy.data.meshes.new('Continuous solid cave roof');me.from_pydata(vs,[],fs);me.update()
o=bpy.data.objects.new('Cave | continuous overhead roof with rooted stalactites',me);col.objects.link(o)
for m in bpy.data.objects['Cave | continuous sculpted walls and hanging roof'].data.materials:me.materials.append(m)
for face in me.polygons:face.material_index=2
bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
o['construction']='Single closed mesh; stalactites share root vertices with roof underside; covers entire island footprint and foreground.'
# Prior camera-facing teeth remain in the backup; the actual roof replaces them.
old=bpy.data.objects.get('Cave | thirty raised hanging formations')
if old:old.hide_render=True;old.hide_set(True)
receivers=bpy.data.collections.get('Cave ceiling light receivers')
if receivers:receivers.objects.link(o)
roof_receivers=bpy.data.collections.get('Interior roof lighting receivers') or bpy.data.collections.new('Interior roof lighting receivers')
roof_receivers.objects.link(o)
for i,(x,y) in enumerate([(-8,-7),(0,-5),(8,-6),(-7,5),(2,5),(9,6)]):
 data=bpy.data.lights.new('Roof bounce %d'%i,'AREA');data.energy=240;data.color=(.17,.39,.72);data.shape='DISK';data.size=6
 light=bpy.data.objects.new('Cave | interior roof bounce %d'%i,data);col.objects.link(light);light.location=p(x,y,9);light.rotation_euler=(p(x,y,13)-light.location).to_track_quat('-Z','Y').to_euler();light.light_linking.receiver_collection=roof_receivers
def camera(name,loc,target,lens):
 data=bpy.data.cameras.new(name);data.type='PERSP';data.lens=lens;data.clip_end=250;data.clip_start=.05
 cam=bpy.data.objects.new(name,data);col.objects.link(cam);cam.location=loc;cam.rotation_euler=(target-loc).to_track_quat('-Z','Y').to_euler();return cam
main=camera('Cave_Interior_Main',p(0,-23,10.7),p(0,0,5.0),30)
camera('Cave_Interior_Left',p(-9,-9,9.9),p(2,2,8.3),22)
camera('Cave_Interior_Reverse',p(5,10,10.0),p(-2,-2,8.3),22)
s.camera=main
bpy.context.view_layer.update();bpy.ops.wm.save_as_mainfile(filepath=ROOT+'base.blend')
result={'rooted_formations':len(patches),'camera':main.name,'roof_footprint':[43.2,46.8],'minimum_tip_z':min(v.z for v in vs)}
