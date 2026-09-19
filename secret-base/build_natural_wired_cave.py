"""Continuous world-space cavern: a real vaulted chamber and receding passage."""
import bpy,math,random,bmesh
from mathutils import Vector,noise
from mathutils.bvhtree import BVHTree
random.seed(471)
s=bpy.context.scene
bpy.ops.wm.save_as_mainfile(filepath='/Users/danielku/mywebsite/secret-base/wired-review/before-natural-direction.blend',copy=True)
if bpy.context.object and bpy.context.object.mode!='OBJECT':bpy.ops.object.mode_set(mode='OBJECT')
for o in bpy.data.collections['Wired_Cavern'].objects:o.hide_render=True;o.hide_set(True)
for o in bpy.data.objects:
 if o.name.startswith('Cave |'):o.hide_render=True;o.hide_set(True)
col=bpy.data.collections.get('Natural_Wired_Cavern')
if col:
 for o in list(col.objects):bpy.data.objects.remove(o,do_unlink=True)
else:col=bpy.data.collections.new('Natural_Wired_Cavern');s.collection.children.link(col)
center=Vector((21,0,0));cam=bpy.data.objects['Cave_Composition_Camera'];s.camera=cam
q=cam.matrix_world.to_quaternion();R=q@Vector((1,0,0));H=q@Vector((0,0,1));H.z=0;H.normalize();Z=Vector((0,0,1))
def w(x,d,z):return center+R*x+H*d+Z*z
def material(name,color,metal=0,rough=.85,em=0):
 m=bpy.data.materials.get(name) or bpy.data.materials.new(name);m.use_nodes=True;nt=m.node_tree;nt.nodes.clear();out=nt.nodes.new('ShaderNodeOutputMaterial');bs=nt.nodes.new('ShaderNodeBsdfPrincipled');bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Roughness'].default_value=rough;bs.inputs['Metallic'].default_value=metal;bs.inputs['Emission Color'].default_value=(*color,1);bs.inputs['Emission Strength'].default_value=em;nt.links.new(bs.outputs[0],out.inputs['Surface']);return m
rock=material('Natural cave | weathered slate',(.048,.056,.066))
nt=rock.node_tree;bs=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED');bs.inputs['Specular IOR Level'].default_value=.23
co=nt.nodes.new('ShaderNodeTexCoord');tex=nt.nodes.new('ShaderNodeTexNoise');tex.inputs['Scale'].default_value=1.7;tex.inputs['Detail'].default_value=5;tex.inputs['Roughness'].default_value=.72;nt.links.new(co.outputs['Object'],tex.inputs['Vector'])
ramp=nt.nodes.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].position=.15;ramp.color_ramp.elements[0].color=(.025,.031,.039,1);ramp.color_ramp.elements[1].position=.85;ramp.color_ramp.elements[1].color=(.086,.095,.11,1);nt.links.new(tex.outputs['Fac'],ramp.inputs[0]);nt.links.new(ramp.outputs[0],bs.inputs['Base Color'])
fine=nt.nodes.new('ShaderNodeTexNoise');fine.inputs['Scale'].default_value=12;fine.inputs['Detail'].default_value=3;nt.links.new(co.outputs['Object'],fine.inputs['Vector']);bump=nt.nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.3;bump.inputs['Distance'].default_value=.08;nt.links.new(fine.outputs['Fac'],bump.inputs['Height']);nt.links.new(bump.outputs[0],bs.inputs['Normal'])
metal=material('Natural cave | dark inset alloy',(.018,.026,.035),.7,.43)
trim=material('Natural cave | machined trim',(.047,.064,.079),.65,.5)
cyan=material('Natural cave | cyan wire',(.06,.5,.72),.15,.45,3)
black=material('Natural cave | recess darkness',(.003,.007,.012),.2,.8)
def mesh(name,vs,fs,mat=rock,smooth=True):
 me=bpy.data.meshes.new(name);me.from_pydata(vs,[],fs);me.update();o=bpy.data.objects.new(name,me);col.objects.link(o);me.materials.append(mat)
 for f in me.polygons:f.use_smooth=smooth
 bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free();return o
def area(name,loc,target,power,size,color):
 data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size;data.color=color;data.specular_factor=.35;data.volume_factor=.45;o=bpy.data.objects.new(name,data);col.objects.link(o);o.location=loc;o.rotation_euler=(Vector(target)-loc).to_track_quat('-Z','Y').to_euler();return o
def tube(name,points,radius,mat):
 cu=bpy.data.curves.new(name,'CURVE');cu.dimensions='3D';cu.bevel_depth=radius;cu.bevel_resolution=2;sp=cu.splines.new('POLY');sp.points.add(len(points)-1)
 for p,v in zip(sp.points,points):p.co=(*v,1)
 o=bpy.data.objects.new(name,cu);col.objects.link(o);cu.materials.append(mat);return o
# One continuous wall and roof grid. Foreground aperture is an actual cavern entrance.
na=128;nz=65;vs=[];fs=[]
profiles=[(-11,20),(-8,20.5),(-3,20),(3,19),(8,18.5),(12,17),(16,14),(19,10.5),(21,7),(22.5,3.5),(23,.2)]
def radius(z):
 for (a,r),(b,t) in zip(profiles,profiles[1:]):
  if a<=z<=b:return r+(t-r)*(z-a)/(b-a)
 return .2
folds=[(random.uniform(-13,13),random.uniform(-12,9),random.uniform(1.1,2.6),random.uniform(1.1,3.9)) for i in range(22)]
for j in range(nz):
 zz=-11+j*34/(nz-1)
 for i in range(na):
  a=i*math.tau/na;r=radius(zz);x=math.sin(a)*r;d=math.cos(a)*r
  n=noise.fractal(Vector((x*.22,d*.22,zz*.23)),1.0,2.0,3);r+=n*1.5+.32*math.sin(a*9+zz*.8)
  x=math.sin(a)*r;d=math.cos(a)*r;z=zz+noise.noise(Vector((x*.45,d*.45,zz*.25)))*.5
  if zz>14:
   for fx,fd,rad,drop in folds:z-=drop*math.exp(-((x-fx)**2+(d-fd)**2)/(rad*rad))
  vs.append(w(x,d,z))
for j in range(nz-1):
 for i in range(na):
  a=(i+.5)*math.tau/na;zz=-11+(j+.5)*34/(nz-1);r=radius(zz);x=math.sin(a)*r;d=math.cos(a)*r
  # Broad irregular entrance toward camera, with true rock above and at both sides.
  angle=min(a,math.tau-a)
  if angle<.84 and zz<18.5+.8*math.sin(a*7):continue
  # A real passage through the far wall, above and behind the platforms.
  if d<-12 and (x/4.3)**2+((zz-10)/4.0)**2<1:continue
  aa=j*na+i;bb=j*na+(i+1)%na;cc=aa+na;dd=bb+na
  fs.extend([(aa,bb,cc),(bb,dd,cc)] if (i+j)%2 else [(aa,bb,dd),(aa,dd,cc)])
shell=mesh('Natural cave | continuous enclosing wall and vaulted roof',vs,fs)
# A winding passage recedes into actual depth beyond the rear aperture.
vs=[];fs=[];nn=48;nr=26
for j in range(nr):
 d=-16-j*.72;rad=4.3-j*.055
 for k in range(nn):
  a=k*math.tau/nn;r=rad+noise.noise(Vector((math.cos(a)*2,math.sin(a)*2,j*.22)))*.6
  vs.append(w(math.cos(a)*r+math.sin(j*.15)*.65,d,10+math.sin(a)*r))
for j in range(nr-1):
 for k in range(nn):
  a=j*nn+k;b=j*nn+(k+1)%nn;c=a+nn;dd=b+nn;fs.extend([(a,b,c),(b,dd,c)])
mesh('Natural cave | winding rear passage',vs,fs)
# Continuous undulating chamber floor, with natural sloping supports for the station.
def floorz(x,d):return -10.2+noise.fractal(Vector((x*.23,d*.23,4)),1,2,3)*1.1
vs=[];fs=[];nx=86;ny=90
for j in range(ny):
 for i in range(nx):
  x=-23+i*.54;d=-24+j*.54;vs.append(w(x,d,floorz(x,d)))
for j in range(ny-1):
 for i in range(nx-1):
  a=j*nx+i;fs.extend([(a,a+1,a+nx),(a+1,a+nx+1,a+nx)])
mesh('Natural cave | continuous uneven cavern floor',vs,fs)
for key in ['about','contact','experience','project']:
 pillar=bpy.data.objects['island_pillar_'+key];ctr=pillar.matrix_world.translation.copy();pts=[pillar.matrix_world@v.co for v in pillar.data.vertices];r=max(math.hypot(v.x-ctr.x,v.y-ctr.y) for v in pts if v.z<.2)
 vs=[];fs=[];N=52;M=24
 for j in range(M):
  t=j/(M-1);z=-10.9*(1-t);rad=r*(1.04+.8*(1-t)**2)
  for k in range(N):
   a=k*math.tau/N;nv=noise.fractal(Vector((math.cos(a)*1.8,math.sin(a)*1.8,z*.32)),1,2,3);rr=rad*(1+nv*.14)+.12*math.sin(a*7+z)
   zz=z+(.19*math.sin(a*5+z*.7) if j<M-1 else -.02)
   vs.append(Vector((ctr.x+math.cos(a)*rr,ctr.y+math.sin(a)*rr,zz)))
 for j in range(M-1):
  for k in range(N):
   a=j*N+k;b=j*N+(k+1)%N;c=a+N;dd=b+N;fs.extend([(a,b,c),(b,dd,c)])
 fs.append(tuple((M-1)*N+k for k in range(N)))
 mesh('Natural cave | bedrock buttress '+key,vs,fs)
# Scattered modest stalagmites and fallen stone are physically rooted on the floor.
for i in range(65):
 x=random.uniform(-18,18);d=random.uniform(-17,14)
 if any((w(x,d,0)-Vector((bpy.data.objects['island_pillar_'+key].location.x,bpy.data.objects['island_pillar_'+key].location.y,0))).length<4 for key in ['about','contact','experience','project']):continue
 z=floorz(x,d);height=random.uniform(.6,2.8);rad=random.uniform(.2,.7);vs=[];fs=[];N=10
 for j,(t,rr) in enumerate([(0,1.45),(.25,1),(.6,.62),(.85,.28),(1,.12)]):
  for k in range(N):
   a=k*math.tau/N;r=rad*rr*(1+.13*math.sin(k*2+i));vs.append(w(x+math.cos(a)*r+t*.22,d+math.sin(a)*r,z+height*t))
 for j in range(4):
  for k in range(N):
   a=j*N+k;b=j*N+(k+1)%N;c=a+N;dd=b+N;fs.extend([(a,b,c),(b,dd,c)])
 fs.append(tuple(4*N+k for k in range(N)));mesh('Natural cave | rooted mineral formation',vs,fs)
for i in range(340):
 x=random.uniform(-20,20);d=random.uniform(-20,18);z=floorz(x,d);r=random.uniform(.1,.48)
 bm=bmesh.new();bmesh.ops.create_icosphere(bm,subdivisions=1,radius=1)
 for v in bm.verts:v.co=w(x+v.co.x*r,d+v.co.y*r,z+v.co.z*r*.6+r*.2)
 me=bpy.data.meshes.new('fallen stone');bm.to_mesh(me);bm.free();o=bpy.data.objects.new('Natural cave | fallen stone',me);col.objects.link(o);me.materials.append(rock)
# Embedded wall machinery uses the actual curved wall surface and world vertical.
bvh=BVHTree.FromPolygons([v.co for v in shell.data.vertices],[list(f.vertices) for f in shell.data.polygons])
def wallhit(angle,z):
 direction=R*math.sin(angle)+H*math.cos(angle);hit,n,idx,dist=bvh.ray_cast(w(0,0,z),direction,40)
 if hit:
  normal=-direction;return hit,normal
 return None,None
def cuboid(name,c,X,Y,N,sc,mat):
 vs=[c+X*(a*sc[0])+Y*(b*sc[1])+N*(d*sc[2]) for a,b,d in [(-.5,-.5,-.5),(.5,-.5,-.5),(.5,.5,-.5),(-.5,.5,-.5),(-.5,-.5,.5),(.5,-.5,.5),(.5,.5,.5),(-.5,.5,.5)]]
 return mesh(name,vs,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],mat,False)
for a,z,width,height in [(1.16,6,1.0,4.2),(2.2,9,.75,3.5),(4.5,6,1.1,4.5),(5.05,1,1.6,4.6)]:
 hit,N=wallhit(a,z)
 if hit is None:continue
 X=Z.cross(N).normalized();hit+=N*.12
 cuboid('Natural cave | inset service panel',hit,X,Z,N,(width,height,.18),metal)
 for sign in [-1,1]:cuboid('Natural cave | panel armored jamb',hit+X*(sign*width*.49)+N*.13,X,Z,N,(.12,height+.12,.25),trim)
 for k in range(4):cuboid('Natural cave | cyan ventilation aperture',hit+X*((k-1.5)*width*.13)+Z*(height*.28)+N*.105,X,Z,N,(.02,height*.13,.02),cyan)
 for k in range(5):cuboid('Natural cave | small status indicator',hit-X*width*.2+Z*(-height*.35+k*height*.12)+N*.11,X,Z,N,(.04,.06,.02),cyan)
 area('Natural cave | panel cyan spill',hit+N*.8,hit,20,1,(.06,.45,.7))
for a,top,length in [(1.0,14,6),(1.8,17,5),(2.8,16,6),(4.1,15,5),(5.1,11,7)]:
 pts=[]
 for k in range(48):
  t=k/47;aa=a+(.025 if .27<t<.54 else (-.018 if t>.7 else 0));hit,N=wallhit(aa,top-length*t)
  if hit is not None:pts.append(hit+N*.035)
 if len(pts)>2:tube('Natural cave | wall following cyan cable',pts,.014,cyan)
# Low, soft mist unifies depth without a painted background.
m=bpy.data.materials.new('Natural cave | atmospheric mist');m.use_nodes=True;nt=m.node_tree;nt.nodes.clear();out=nt.nodes.new('ShaderNodeOutputMaterial');vol=nt.nodes.new('ShaderNodeVolumePrincipled');vol.inputs['Color'].default_value=(.2,.34,.5,1);vol.inputs['Anisotropy'].default_value=.18;vol.inputs['Emission Color'].default_value=(.015,.065,.12,1);vol.inputs['Emission Strength'].default_value=.008
co=nt.nodes.new('ShaderNodeTexCoord');tex=nt.nodes.new('ShaderNodeTexNoise');tex.inputs['Scale'].default_value=3;tex.inputs['Detail'].default_value=3;nt.links.new(co.outputs['Generated'],tex.inputs['Vector']);mul=nt.nodes.new('ShaderNodeMath');mul.operation='MULTIPLY';mul.inputs[1].default_value=.07;nt.links.new(tex.outputs['Fac'],mul.inputs[0]);nt.links.new(mul.outputs[0],vol.inputs['Density']);nt.links.new(vol.outputs[0],out.inputs['Volume'])
cuboid('Natural cave | low chamber mist',w(0,-1,-7),R,H,Z,(40,42,6),m)
area('Natural cave | soft entrance daylight',w(-5,19,15),w(0,0,5),2400,14,(.5,.61,.76))
area('Natural cave | overhead reflected blue',w(0,0,9),w(0,-2,22),2600,12,(.2,.39,.62))
area('Natural cave | left reflected light',w(-8,1,4),w(-19,-3,5),1400,9,(.25,.39,.56))
area('Natural cave | right reflected light',w(9,1,5),w(19,-3,5),1500,9,(.23,.39,.6))
area('Natural cave | distant passage light',w(0,-23,11),w(0,-17,10),1800,4,(.09,.39,.8))
for x,d in [(-10,-4),(4,-5),(11,1),(-3,8)]:
 area('Natural cave | blue chasm bounce',w(x,d,-6),w(x,d,-10),300,5,(.08,.35,.63))
area('Natural cave | foundation ambient',w(0,13,-1),w(0,0,-5),1200,12,(.35,.45,.59))
s.render.engine='BLENDER_EEVEE';s.render.resolution_percentage=75;s.eevee.taa_render_samples=64
s.render.filepath='/Users/danielku/mywebsite/secret-base/wired-review/natural-cave-1.png'
s['cavern_direction']='Continuous physically connected chamber and passage. Natural geology takes precedence over matching the image silhouette.'
bpy.ops.wm.save_as_mainfile(filepath='/Users/danielku/mywebsite/secret-base/base.blend')
