"""Reference-led faceted wired cavern, around the existing four pillar station."""
import bpy, math, random, bmesh
from mathutils import Vector, noise
random.seed(7341)
s=bpy.context.scene
if bpy.context.object and bpy.context.object.mode!='OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
col=bpy.data.collections.get('Wired_Cavern')
if col:
 for o in list(col.objects):bpy.data.objects.remove(o,do_unlink=True)
else:
 col=bpy.data.collections.new('Wired_Cavern');s.collection.children.link(col)
cam=bpy.data.objects['Cave_Composition_Camera'];s.camera=cam;cam.data.ortho_scale=32
C=Vector((21,-.3,4));Q=cam.matrix_world.to_quaternion();R=Q@Vector((1,0,0));U=Q@Vector((0,1,0));D=Q@Vector((0,0,1))
def p(x,y,d):return C+R*x+U*y+D*d
# Keep legacy geometry available in the backup, supersede the inconsistent surround.
for o in bpy.data.objects:
 if o.name.startswith('Cave |'):
  if any(k in o.name for k in ['foundation island','deep chasm mist','drifting mist','deep continuous bedrock','retained foundation']):continue
  o.hide_render=True;o.hide_set(True)
for cname in ['Cave_Continuous_Roof','Cave_Ceiling_Teeth','Cave_Surface_Relief','Environment_Stepped_Stone','Cave ceiling light receivers','Interior roof lighting receivers']:
 co=bpy.data.collections.get(cname)
 if co:
  for o in co.objects:o.hide_render=True;o.hide_set(True)
def mat(name,color,metal=0,rough=.87,em=0):
 m=bpy.data.materials.get(name) or bpy.data.materials.new(name);m.use_nodes=True;bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Roughness'].default_value=rough;bs.inputs['Metallic'].default_value=metal
 if em:bs.inputs['Emission Color'].default_value=(*color,1);bs.inputs['Emission Strength'].default_value=em
 return m
rocks=[mat('Wired basalt %02d'%i,(.027*(.75+i*.065),.038*(.75+i*.065),.053*(.75+i*.065))) for i in range(9)]
metal=mat('Wired dark titanium',(.023,.032,.045),.65,.5);edge=mat('Wired titanium bevels',(.046,.065,.083),.6,.47);black=mat('Wired recessed void',(.004,.009,.014),.2,.65)
cyan=mat('Wired cyan luminous core',(.07,.68,1),.1,.34,3.5);dim=mat('Wired cyan dim indicators',(.025,.28,.42),.3,.45,1.8)
def mesh(name,vs,fs,mats=rocks):
 me=bpy.data.meshes.new(name);me.from_pydata(vs,[],fs);me.update();o=bpy.data.objects.new(name,me);col.objects.link(o)
 for m in mats:me.materials.append(m)
 for f in me.polygons:f.material_index=random.randrange(len(mats));f.use_smooth=False
 return o
def crag(name,xyz,scale,detail=2):
 bm=bmesh.new();bmesh.ops.create_icosphere(bm,subdivisions=(3 if any(k in name for k in ['massive wall','ceiling fractured','foreground cliff','receding wall']) else detail),radius=1)
 for v in bm.verts:
  v.co*=random.uniform(.91,1.09)
  q=v.co.copy();v.co=p(xyz[0]+q.x*scale[0],xyz[1]+q.y*scale[1],xyz[2]+q.z*scale[2])
 me=bpy.data.meshes.new(name);bm.to_mesh(me);bm.free();o=bpy.data.objects.new(name,me);col.objects.link(o)
 for m in rocks:me.materials.append(m)
 for f in me.polygons:f.material_index=max(0,min(8,int(4+noise.noise(f.center*.8)*4)));f.use_smooth=False
 return o
def area(name,xyz,target,power,size,color):
 data=bpy.data.lights.new(name,'AREA');data.energy=power;data.color=color;data.shape='DISK';data.size=size;o=bpy.data.objects.new(name,data);col.objects.link(o);o.location=p(*xyz);o.rotation_euler=(p(*target)-o.location).to_track_quat('-Z','Y').to_euler();return o
def line(name,coords,radius,material):
 cu=bpy.data.curves.new(name,'CURVE');cu.dimensions='3D';cu.bevel_depth=radius;cu.bevel_resolution=0;sp=cu.splines.new('POLY');sp.points.add(len(coords)-1)
 for pt,v in zip(sp.points,coords):pt.co=(*v,1)
 o=bpy.data.objects.new(name,cu);col.objects.link(o);cu.materials.append(material);return o
def box(name,xyz,scale,material,bevel=0):
 bpy.ops.mesh.primitive_cube_add(size=1,location=p(*xyz));o=bpy.context.object;o.name=name
 for c in list(o.users_collection):c.objects.unlink(o)
 col.objects.link(o);o.rotation_euler=cam.rotation_euler;o.scale=scale;o.data.materials.append(material)
 if bevel:
  bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);mod=o.modifiers.new('Machined chamfer','BEVEL');mod.width=bevel;mod.segments=1;o.modifiers.new('Weighted corner normals','WEIGHTED_NORMAL')
 return o
# Three depth bands; openings offset between layers to create a winding cavern.
for band,depth in enumerate([-21,-15,-9]):
 for side in [-1,1]:
  for j in range(6):
   x=side*(10.4+band*.85+random.uniform(-.7,.6));y=-10+j*4.0+random.uniform(-1,1)
   crag('Wired | massive wall band%d %d %d'%(band,side,j),(x,y,depth),(random.uniform(2.7,4.0),random.uniform(3,5),random.uniform(2.5,4)),2)
 # Rear wall leaves narrow high central slot and lower chasm.
 if band<2:
  for x,y,w,h in [(-6,7,4,5),(5.8,6.7,3.7,5),(-3,-2,3,5),(4,-4,3,4),(-8,-7,3,4),(8,-8,3,4)]:
   crag('Wired | receding wall', (x+band*.7,y,depth-2),(w,h,3),2)
# Substantial irregular overhead boulders, connected behind the top edge.
for x,y,w,h,d in [(-13,9,5,4,3),(-8,10.5,4.2,3.7,-1),(-4.8,11,3.5,3.5,-5),(0,12,4,3,-10),(4.8,10,3.2,4,-7),(8.5,11,3.8,3.8,0),(13,9.6,4.2,4.5,4)]:
 crag('Wired | ceiling fractured overhang',(x,y,d),(w,h,3),2)
# Near side walls frame the image without covering the platforms.
for side in [-1,1]:
 for j in range(5):
  crag('Wired | foreground cliff',(side*(15.4+random.uniform(-.5,.5)),-9+j*4.3,6+random.uniform(-1,2)),(3.2,3.5,3),2)
# Rock shelves at service doors, broken and uneven underneath.
for x,y,d in [(-11.8,-1,-3),(11.6,-1.9,-2),(-11.2,-6.1,2),(11.6,-7,2),(-8.1,2.4,-9),(7.8,3,-10)]:
 crag('Wired | service ledge',(x,y,d),(2.1,.6,1.8),2)
 for i in range(15):
  crag('Wired | loose ledge rubble',(x+random.uniform(-1.6,1.6),y+random.uniform(.1,.45),d+random.uniform(-1,1)),(random.uniform(.12,.42),random.uniform(.12,.35),random.uniform(.1,.4)),1)
# Sharp spires, with small broken talus, disappearing down the blue abyss.
for i in range(58):
 x=random.uniform(-13,13);y=random.uniform(-15,-4.5);d=random.uniform(-18,-7)
 crag('Wired | abyss rock tooth',(x,y,d),(random.uniform(.45,1.5),random.uniform(1.3,3.4),random.uniform(.6,1.6)),1 if i%3 else 2)
for i in range(145):
 x=random.uniform(-14,14);y=random.uniform(-13,-7.5);d=random.uniform(-9,4)
 crag('Wired | talus field',(x,y,d),(random.uniform(.15,.75),random.uniform(.16,.65),random.uniform(.2,.7)),1)
# Lower foreground broken rim.
for i in range(12):
 x=-16+i*2.8
 crag('Wired | bottom cavern rim',(x,-11.4+random.uniform(-1,.6),9),(random.uniform(1.6,2.8),random.uniform(1.2,2.4),2.2),1 if i%2 else 2)
# Faceted foundations match the walls in material and catch grazing blue light.
for o in bpy.data.objects:
 if o.type=='MESH' and 'bedrock foundation island' in o.name:
  o.data.materials.clear()
  for m in rocks:o.data.materials.append(m)
  o.hide_render=False;o.hide_set(False)
  for f in o.data.polygons:f.use_smooth=False;f.material_index=random.randrange(len(rocks))
# Tall inset service strips, framed with segmented titanium and cyan apertures.
def panel(x,y,d,w,h,door=False):
 box('Wired | excavated service recess',(x,y,d),(w+ .3,h+.3,.28),black,.09)
 box('Wired | armored inset door' if door else 'Wired | wall service cassette',(x,y,d+.17),(w,h,.26),metal,.09)
 for side in [-1,1]:
  box('Wired | recessed jamb',(x+side*(w*.5-.055),y,d+.34),(.11,h-.12,.15),edge,.025)
  for k in range(5):box('Wired | segmented conduit armor',(x+side*(w*.5+.13),y-h*.44+k*h*.22,d+.02),(.18,h*.17,.22),metal,.02)
 for k in range(4):
  box('Wired | cyan ventilation slot',(x+(k-1.5)*w*.135,y+h*.28,d+.322),(.022,h*.15,.012),cyan)
 for k in range(5):
  yy=y-h*.35+k*h*.11
  box('Wired | status aperture',(x-w*.2,yy,d+.315),(.055,.045 if k%2 else .12,.018),dim)
 box('Wired | central door seam',(x+.05,y-h*.13,d+.315),(.018,h*.52,.013),black)
 if door:
  for side in [-1,1]:box('Wired | door edge running light',(x+side*w*.35,y-h*.24,d+.34),(.021,h*.35,.018),dim)
  for k in range(4):box('Wired | threshold tread',(x,y-h*.5-.05-k*.12,d+.3+k*.18),(w,.10,.25),edge,.012)
  line('Wired | luminous threshold',[p(x-w*.4,y-h*.5-.38,d+.85),p(x+w*.4,y-h*.5-.38,d+.85)],.018,cyan)
 area('Wired | local cassette spill',(x,y,d+1),(x,y,d-1),22,1,(.06,.55,1))
panel(-11.8,1.15,-.8,1.35,3.8,True)
panel(11.6,.5,-.3,1.35,3.8,True)
panel(-8.2,5.2,-6.8,.7,3.2)
panel(7.6,5.8,-6.3,.72,3.7)
panel(-13.6,6.5,2,.65,3.7)
panel(13.6,5.5,2.2,.7,3.3)
# Sparse angular wall fissures; black split beneath thin emissive inner wire.
for x,y,d,length in [(-12.3,9,3,5.2),(11.4,9.8,2,4.5),(-10.6,-1.9,1,4.2),(12,-3,2,5.3),(-3.2,9,-17,4),(5,7.8,-7,3.5),(-13,-7,5,4),(8.9,-7,3,4)]:
 coords=[];xx=x
 for k in range(7):
  if k in [2,4]:xx+=random.choice([-1,1])*random.uniform(.3,.65)
  coords.append(p(xx,y-k*length/6,d+random.uniform(-.08,.08)))
 line('Wired | fissure dark cut',coords,.065,black);line('Wired | hairline cyan fissure',[v+D*.018 for v in coords],.015,cyan)
 area('Wired | fissure blue rock spill',(x,y-length*.5,d+.7),(x,y-length*.5,d-1),80,2,(.04,.48,1))
# Blue depth comes from dim distant stone and localized haze, not a bright flat sky.
area('Wired | broad cool key',(-3,7,14),(0,1,-4),2100,14,(.48,.62,.8))
area('Wired | left facets',(-7,-1,5),(-13,-1,-5),1600,8,(.17,.42,.68))
area('Wired | right facets',(7,1,6),(13,-2,-5),1750,8,(.18,.43,.7))
area('Wired | upper cavern bounce',(0,5,-3),(0,11,-12),1400,7,(.13,.38,.65))
area('Wired | distant glacial light',(0,5,-17),(0,6,-24),2200,6,(.12,.45,1))
area('Wired | abyss light west',(-6,-7,-3),(-6,-10,-12),1600,7,(.08,.48,.9))
area('Wired | abyss light east',(7,-7,-3),(7,-10,-12),1850,7,(.07,.46,.9))
area('Wired | foundation face grazing',(0,-2,12),(0,-5,0),1900,12,(.28,.48,.68))
# Tone down graphic glowing rings on platforms, as in the reference.
for m in bpy.data.materials:
 if any(k in m.name.lower() for k in ['floor']) and m.use_nodes:
  for n in m.node_tree.nodes:
   if n.type=='EMISSION':n.inputs['Strength'].default_value*=.35
exec(compile(open('/Users/danielku/mywebsite/secret-base/refine_wired_cavern.py').read(),'refine_wired_cavern.py','exec'))
s.render.resolution_x=1540;s.render.resolution_y=1020;s.render.resolution_percentage=65;s.eevee.taa_render_samples=48
s['wired_cavern_reference']='User supplied two Wired Cavern images; four existing station pillars with faceted enclosing geology, service panels, sparse cyan fissures and abyss.'
for screen in bpy.data.screens:
 for a in screen.areas:
  if a.type=='VIEW_3D':a.spaces.active.region_3d.view_perspective='CAMERA'
bpy.ops.wm.save_as_mainfile(filepath='/Users/danielku/mywebsite/secret-base/base.blend')
