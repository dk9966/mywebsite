"""Deterministic V4 block-jointed cavern rebuild. Keeps source scene recoverable.
Run with Blender --background --python rebuild_v4.py -- --pass 1.
"""
import bpy,bmesh,math,random,os,sys,argparse,json
from mathutils import Vector
from mathutils.noise import noise
R=os.path.dirname(os.path.abspath(__file__)); OUT=R+'/v4-review'
p=argparse.ArgumentParser();p.add_argument('--pass',dest='stage',type=int,default=1);p.add_argument('--width',type=int,default=1272);p.add_argument('--samples',type=int,default=40);a=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
bpy.ops.wm.open_mainfile(filepath=OUT+'/before-v4.blend');s=bpy.context.scene
rng=random.Random(416)
# Hide the prior geological treatment, retaining all editable source meshes.
for c in bpy.data.collections:
 if c.name[:2] in ('01','02','03','04','25'):
  for o in c.objects:o.hide_render=True;o.hide_set(True)
for o in s.objects:
 if o.type=='LIGHT':o.hide_render=True
co=bpy.data.collections.new('30 | V4 • jointed basalt walls and roof');s.collection.children.link(co)
li=bpy.data.collections.new('31 | V4 • practical lighting and atmosphere');s.collection.children.link(li)
def mat(n,c,rough=.85,emit=0):
 m=bpy.data.materials.new(n);m.diffuse_color=(*c,1);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*c,1);p.inputs['Roughness'].default_value=rough;p.inputs['Emission Color'].default_value=(*c,1);p.inputs['Emission Strength'].default_value=emit;return m
rock=mat('V4 | fractured matte charcoal basalt',(.048,.058,.07))
nt=rock.node_tree;n=nt.nodes;l=nt.links;bs=n.get('Principled BSDF');tc=n.new('ShaderNodeTexCoord');tex=n.new('ShaderNodeTexNoise');tex.inputs['Scale'].default_value=6;tex.inputs['Detail'].default_value=4;l.new(tc.outputs['Object'],tex.inputs['Vector'])
vor=n.new('ShaderNodeTexVoronoi');vor.feature='DISTANCE_TO_EDGE';vor.inputs['Scale'].default_value=6;l.new(tc.outputs['Object'],vor.inputs['Vector'])
ramp=n.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].position=.014;ramp.color_ramp.elements[0].color=(.028,.035,.043,1);ramp.color_ramp.elements[1].position=.095;ramp.color_ramp.elements[1].color=(.059,.07,.084,1);l.new(vor.outputs['Distance'],ramp.inputs[0]);l.new(ramp.outputs[0],bs.inputs['Base Color'])
b=n.new('ShaderNodeBump');b.inputs['Strength'].default_value=.48;b.inputs['Distance'].default_value=.065;l.new(vor.outputs['Distance'],b.inputs['Height']);b2=n.new('ShaderNodeBump');b2.inputs['Strength'].default_value=.32;b2.inputs['Distance'].default_value=.065;l.new(tex.outputs['Fac'],b2.inputs['Height']);l.new(b.outputs[0],b2.inputs['Normal']);l.new(b2.outputs[0],bs.inputs['Normal'])
# Scanned fracture normal, with triplanar stone color on the block faces.
rock=bpy.data.materials['GEOLOGY | eroded stratified dark limestone'].copy();rock.name='V4 | scanned matte fractured basalt'
nt=rock.node_tree;tc=nt.nodes.new('ShaderNodeTexCoord');mapping=nt.nodes.new('ShaderNodeVectorMath');mapping.operation='SCALE';mapping.inputs[3].default_value=.48;nt.links.new(tc.outputs['Object'],mapping.inputs[0])
for nod in nt.nodes:
 if nod.type=='TEX_IMAGE':nod.projection='BOX';nod.projection_blend=.14;nt.links.new(mapping.outputs[0],nod.inputs['Vector'])
 if nod.type=='NORMAL_MAP':nod.inputs['Strength'].default_value=.65
# Fine-scale geometric fracture shading layered over the scanned face normals.
nt=rock.node_tree;pr=nt.nodes.get('Principled BSDF');old=pr.inputs['Normal'].links[0].from_socket
nn=nt.nodes.new('ShaderNodeTexNoise');nn.inputs['Scale'].default_value=17;nn.inputs['Detail'].default_value=3.5;nt.links.new(tc.outputs['Object'],nn.inputs['Vector'])
bb=nt.nodes.new('ShaderNodeBump');bb.inputs['Strength'].default_value=.35;bb.inputs['Distance'].default_value=.06;nt.links.new(nn.outputs['Fac'],bb.inputs['Height']);nt.links.new(old,bb.inputs['Normal']);nt.links.new(bb.outputs[0],pr.inputs['Normal'])
# Shared chipped orthogonal chunks; broad faces stay planar, corners fracture.
variants=[]
for k in range(24):
 bm=bmesh.new();bmesh.ops.create_cube(bm,size=1)
 for v in bm.verts:v.co+=Vector(tuple(rng.uniform(-.075,.075) for _ in range(3)))
 bmesh.ops.bevel(bm,geom=list(bm.edges),offset=rng.uniform(.055,.105),segments=1,affect='EDGES')
 bmesh.ops.subdivide_edges(bm,edges=list(bm.edges),cuts=6,use_grid_fill=True)
 bm.normal_update()
 for v in bm.verts:v.co+=v.normal*(noise(v.co*17+Vector((k,0,0)))*.025)
 # Embedded angular fracture plates: overlapping mineral-scale chips, not a flat tile shader.
 for axis,sgn in [(0,-1),(0,1),(1,-1),(1,1),(2,1),(2,-1)]:
  axes=[j for j in range(3) if j!=axis]
  for chip in range(13):
   cu=rng.uniform(-.42,.42);cv=rng.uniform(-.42,.42);ru=rng.uniform(.085,.19);rv=rng.uniform(.07,.17);depth=rng.uniform(.012,.035);N=rng.choice([5,6,7]);rings=[]
   for level in [0,1]:
    ring=[]
    for j in range(N):
     ang=2*math.pi*j/N;rad=rng.uniform(.78,1.1);q=[0,0,0];q[axis]=sgn*(.47+level*depth);q[axes[0]]=cu+ru*math.cos(ang)*rad;q[axes[1]]=cv+rv*math.sin(ang)*rad;ring.append(bm.verts.new(q))
    rings.append(ring)
   bm.faces.new(rings[0][::-1]);bm.faces.new(rings[1])
   for j in range(N):bm.faces.new((rings[0][j],rings[0][(j+1)%N],rings[1][(j+1)%N],rings[1][j]))
 bmesh.ops.triangulate(bm,faces=list(bm.faces));bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));me=bpy.data.meshes.new('V4 | chipped joint block %02d'%k);bm.to_mesh(me);bm.free();me.materials.append(rock)
 uv=me.uv_layers.new(name='Fracture face UV')
 for f in me.polygons:
  axis=max(range(3),key=lambda j:abs(f.normal[j]));ax=(0,1) if axis==2 else (0,2) if axis==1 else (1,2)
  for j in f.loop_indices:
   v=me.vertices[me.loops[j].vertex_index].co;uv.data[j].uv=(v[ax[0]]*.7+k*.173,v[ax[1]]*.7+k*.233)
 variants.append(me)
def block(n,loc,scale):
 ob=bpy.data.objects.new(n,rng.choice(variants));co.objects.link(ob);ob.location=loc;ob.scale=scale;ob.rotation_euler.z=rng.uniform(-.016,.016);return ob
def mass(tag,cx,cy,rx,ry,z0,z1,cell=.95):
 # Each column has discrete shoulders and staggered break planes; no taper/cones.
 for ix in range(-math.ceil(rx/cell),math.ceil(rx/cell)+1):
  for iy in range(-math.ceil(ry/cell),math.ceil(ry/cell)+1):
   x=cx+ix*cell;y=cy+iy*cell
   d=(ix*cell/rx)**2+(iy*cell/ry)**2
   if d>1+rng.uniform(-.16,.16):continue
   top=z1-rng.uniform(.0,.6)-max(0,d-.35)*rng.uniform(.7,2.0)
   z=z0+rng.uniform(-.5,.5)
   column_dx=rng.uniform(-.20,.20);column_dy=rng.uniform(-.3,.3)
   while z<top:
    h=min(rng.choice([.85,1.1,1.35,1.65]),top-z)
    if h<.18:break
    tier=math.floor(z/3.4)
    bulge=.80+.28*math.sin(tier*1.71+cx)+.18*math.cos(tier*2.3+cy)
    if d<bulge:
     step_x=.4*math.sin(tier*1.3+cy)+column_dx;step_y=.45*math.sin(tier*2.1+cx)+column_dy
     block('V4 | '+tag,(x+step_x+rng.uniform(-.09,.09),y+step_y+rng.uniform(-.09,.09),z+h/2),(cell*rng.uniform(1.03,1.23),cell*rng.uniform(1.03,1.23),h-.012))
    z+=h
# Deep independent pedestal roots.
for data in [('Projects rear root',0,7,2.7,2.3,-16,7.2),('Contact root',-12.8,11,3.65,3.7,-15,10.6),('Experiences root',-15,-4,5.0,4.3,-16,3.8),('About root',14.3,-.6,4.8,3.9,-16,6.9),('Workshop root',14,14,5.4,4,-12,10.6)]:mass(*data)
# Foreground sidewalls never obscure station fronts.
for data in [('Left edge',-25,3,3.3,9,-15,30),('Right edge',25,6,3.5,11,-15,30),('Left inner cliff',-22,16,2.7,4.5,-14,29),('Right inner cliff',21,19,3.8,4,-14,29),('Rear left buttress',-6.8,25,3.2,4,-14,28),('Rear right buttress',8,29,3.3,4,-14,29)]:mass(*data,cell=1.05)
for x,y,z in [(-16,34,25),(-10,40,27),(-2,40,25),(6,42,27),(15,39,29),(-4,27,9),(5,29,12)]:mass('Receding cliffs',x,y,3.4,3,-17,z,1.6)
for data in [('Projects front shoulder',1,.1,1.5,1.2,-16,6.7),('Projects left shoulder',-3.0,2.6,1.2,1.3,-16,7.0),('About front shoulder',13,-4,2.4,1.8,-16,3.7),('Left foreground ledge',-21,-7,2.2,3,-16,6),('Right foreground ledge',23,-5,2.4,3,-16,8),('Left wall inward step',-21,7,2.3,3,-16,14),('Rear hub buttress',-6.5,22,3,3,-16,15)]:mass(*data,cell=.9)
# Discrete front outcrops give the pedestal a broken geological silhouette.
for data in [('Projects large ledge',2.9,2.8,1.3,1.3,-16,6.7),('Projects broken flank',-2.1,-1.0,1.2,1.2,-16,4.8),('Contact block ledge',-16,7,1.7,1.5,-16,8.3),('Left lower cliff',-21,-8,2.4,2.0,-16,5.0),('Right broken cliff',22,-9,2.6,2,-16,5.8)]:mass(*data,cell=.9)
mass('Projects connected interior',0,3.3,3,2.6,-16,6.8,.95)
# Roof: continuous uneven upper mass with stepped pendent outcrops.
for ix in range(-18,19):
 x=ix*1.45
 for iy in range(7):
  y=8+iy*2.6+2.4*math.sin(ix*.61)
  bottom=21.1+.7*math.sin(ix*.7)+.45*math.cos(iy+ix*.2)
  for iz in range(2):block('V4 | continuous rock roof',(x,y,bottom+iz*1.2),(1.47,2.65,1.23))
for x,y,low in [(-23,11,15),(-18,23,15),(-7,25,15),(5,30,17),(20,23,15),(24,12,15)]:mass('Roof hanging step',x,y,2.1,2,low,22,.95)
# Remove rounded architectural rock awnings from the old style.
for ob in s.objects:
 if ob.type=='MESH' and any(m and m.name.startswith(('GEOLOGY','ROCK |')) for m in ob.data.materials):
  if not ob.name.startswith('V4 |'):ob.hide_render=True
# Chunky horizontal shoulders project into the top framing, with thick roofs.
for data in [('Roof left foreground',-17,6,3.1,2.7,20.4,25),('Roof central shelf',-5,10,3.0,3.6,20.5,25),('Roof right shelf',7,12,3.1,3.6,19.8,25)]:mass(*data,cell=1.3)
for i,(x,y,z,sx,sy,sz) in enumerate([(-20,1,22,4,9,2.2),(-13,6,22.3,3,8,1.5),(-8,7,22.7,5,9,2.0),(2,9,22.0,4.5,9,1.6),(10,6,23.2,5,9,2.0),(18,7,22,4,8,2.4)]):
 for j in range(4):
  for k in range(6):block('V4 | overhanging roof shelf',(x+j*sx/4,y-sy/2+k*sy/6,z+rng.uniform(-.25,.25)),(sx/4+.1,sy/6+.03,sz*rng.uniform(.6,1.1)))
# Sloping ceiling beds expose their underside to the comparison camera.
for ob in co.objects:
 if any(t in ob.name for t in ['continuous rock roof','overhanging roof shelf']):
  ob.location.z-=.22*min(6,(ob.location.y-12));ob.rotation_euler.x=math.radians(-13)
# Asymmetric central geological buttress with lateral terraces and a broken root.
for ob in co.objects:
 if 'Projects' in ob.name:
  z=ob.location.z;ob.location.x+=1.0*math.sin((z-6.8)*.36);ob.location.y+=.55*math.sin((z-6.8)*.48)
mass('Central outlying terrace',4.0,2.5,1.25,1.3,-16,3.5,.85)
mass('Central low terrace',-4.0,1.5,1.35,1.5,-16,.5,.9)
# Integrate manufactured alcove roofs into fractured rock shoulders.
mass('Experiences cavern brow',-16,2.6,5.4,1.8,9.1,10.7,.9)
mass('About cavern brow',15,5.0,5.4,1.9,10.2,11.3,.9)
# Separate hanging cuboid clusters interrupt the ceiling at several depths.
for data in [('Ceiling pendant left',-6.2,16,1.65,1.8,12.0,24),('Ceiling pendant right',7.5,20,1.9,2,14.5,24),('Ceiling foreground left',-20,8,1.9,2,17,24),('Ceiling foreground right',21,10,1.8,2,16,24)]:mass(*data,cell=.85)
for data in [('Projects mid foreground crown',-.3,-1.2,1.8,1.3,-16,5.3),('Projects wide lower shoulder',-4.3,.4,1.6,1.4,-16,-.3),('Projects stepped right spur',4,1.3,1.3,1.4,-16,2.0)]:mass(*data,cell=.8)
# The reference root is narrow at the deck and opens into staggered lower buttresses.
for ob in co.objects:
 if any(t in ob.name for t in ['Projects','Central outlying','Central low']):
  z=ob.location.z;w=.66+.34*max(0,min(1,(6.8-z)/12));ob.location.x=.8+ob.location.x*w;ob.scale.x*=w
 if any(t in ob.name for t in ['Left edge','Right edge','Left inner cliff','Right inner cliff']):
  tier=math.floor(ob.location.z/3.5);ob.location.x+=.75*math.sin(tier*1.7);ob.location.y+=.8*math.cos(tier*1.9)
# Lift the central ceiling pocket while keeping the side rooms enclosed.
for ob in co.objects:
 if any(t in ob.name for t in ['continuous rock roof','overhanging roof shelf']):
  w=max(0,1-abs(ob.location.x)/8);ob.location.z+=2.3*w
# Move distant layers behind the illuminated air column, avoiding a flat lit back wall.
for ob in co.objects:
 if 'Receding cliffs' in ob.name:ob.location.y+=16
# Slightly wider matching 1.832:1 camera gate.
s.render.resolution_x=a.width;s.render.resolution_y=round(a.width*927/1696);s.render.resolution_percentage=100;s.render.pixel_aspect_x=1;s.render.pixel_aspect_y=1
s.camera.data.ortho_scale=49.2;s.camera.location.z=34.8;s.camera.rotation_euler.x=math.radians(69.5)
# Dim neutral world, with visible localized illumination.
s.world.node_tree.nodes.get('Background').inputs[0].default_value=(.12,.16,.21,1);s.world.node_tree.nodes.get('Background').inputs[1].default_value=.11
s.view_settings.exposure=.1
white=mat('V4 | ceiling luminous strip',(.70,.82,1),.3,7)
label=mat('V4 | icy blue illuminated typography',(.25,.42,1),.45,2.4)
for ob in s.objects:
 if ob.type=='FONT' and 'lettering' in ob.name:ob.data.materials.clear();ob.data.materials.append(label)
 # Make the central pool visibly blue instead of hollow black.
 if ob.type=='MESH' and any(m and 'Secondary table' in m.name for m in ob.data.materials):
  for m in ob.data.materials:
   if m and m.use_nodes:
    p=m.node_tree.nodes.get('Principled BSDF')
    if p:p.inputs['Emission Color'].default_value=(.018,.29,.62,1);p.inputs['Emission Strength'].default_value=1.8

def light(n,pos,target,power,size=1,kind='AREA',color=(.72,.82,1),angle=.65):
 d=bpy.data.lights.new('V4 | '+n,kind);d.energy=power;d.color=color
 if kind=='AREA':d.shape='DISK';d.size=size
 if kind=='SPOT':d.spot_size=angle;d.spot_blend=.85;d.shadow_soft_size=.18
 ob=bpy.data.objects.new(d.name,d);li.objects.link(ob);ob.location=pos;ob.rotation_euler=(Vector(target)-ob.location).to_track_quat('-Z','Y').to_euler();return ob

def fixture(n,pos,target,power,angle=.65):
 ob=block('Lamp housing '+n,pos,(1.05,.6,.14));ob.data=ob.data.copy();ob.data.materials.clear();ob.data.materials.append(bpy.data.materials['STRUCTURE | graphite powdercoat'])
 for dy in [-.18,.18]:
  ob=block('White lamp strip '+n,(pos[0],pos[1]+dy,pos[2]-.08),(.86,.06,.035));ob.data=ob.data.copy();ob.data.materials.clear();ob.data.materials.append(white)
 light(n,(pos[0],pos[1],pos[2]-.25),target,power,kind='SPOT',angle=angle)
fixture('Contact overhead',(-13.5,9,18.4),(-12.8,10,10),3800,.78)
fixture('Central overhead',(-.6,13,21.0),(0,14,-5),6500,1.35)
fixture('Workshop overhead',(14,10,17.0),(14,13,10),2900,.85)
fixture('Education ceiling',(-16.6,-1,9.1),(-15,-4,5),950,1.1)
fixture('About ceiling',(14.3,1.5,11.8),(14,-1,7),1500,1.05)
light('Soft camera bounce',(0,-18,20),(0,8,9),2200,18)
light('Rear depth',(0,34,22),(0,22,10),1700,8)
light('Left rock grazing',(-17,-4,19),(-24,8,12),350,8)
light('Right rock grazing',(17,-4,20),(24,8,12),350,8)
light('Projects screen',(0,7,10),(0,4,7.5),120,3,color=(.08,.4,1))
light('About blue pool',(14,-1,9),(14,-1,7),70,2,color=(.04,.38,1))
for ob in s.objects:
 if ob.type=='LIGHT' and ('Workshop | warm task' in ob.name or 'Practical | workshop' in ob.name):ob.hide_render=False;ob.data.energy*=1.0
 if ob.type=='LIGHT' and 'Bollard | pool' in ob.name:ob.hide_render=False;ob.data.energy=5;ob.data.color=(1,.72,.43)
# Filled luminous holographic surface at the real table top.
light('Experience work floor',(-14,-6,9),(-14,-6,4.8),500,4,color=(.8,.86,1))
for ob in s.objects:
 if ob.type=='MESH' and any(m and 'luminous blue surface' in m.name for m in ob.data.materials):
  for m in ob.data.materials:
   if m and m.use_nodes:
    pp=m.node_tree.nodes.get('Principled BSDF')
    if pp:pp.inputs['Emission Color'].default_value=(.022,.25,.65,1);pp.inputs['Emission Strength'].default_value=2.0
# Luminous inset explicitly replaces legacy connected emission graph.
inset=bpy.data.objects['Holo table | luminous inset'];inset.data=inset.data.copy();inset.data.materials.clear();inset.data.materials.append(mat('V4 | filled blue table',(.003,.065,.22),.55,.32))
for ob in s.objects:
 if ob.name.startswith('Holo table | blue vent'):
  ob.data=ob.data.copy();ob.data.materials.clear();ob.data.materials.append(white)
# Broad station pools complement the ceiling shafts.
light('Projects ceiling bounce',(0,3,14),(0,5,7),1800,5,color=(.72,.8,1))
light('Contact soft white',(-12,7,17),(-12,11,11),350,4,color=(.85,.88,1))
light('About soft white',(13,-1,12),(14,-1,7.6),700,4,color=(.8,.87,1))
# Bottom haze is illuminated behind the rock roots, not from the camera.
light('Deep abyss mist',(0,18,-1),(0,3,-7),450,9,color=(.36,.46,.60))
light('Left abyss mist',(-7,14,0),(-7,0,-8),260,7,color=(.36,.46,.60))
# Reduce the tower's height to the reference silhouette, anchored on its deck.
for ob in bpy.data.collections['20 | CONTACT • antenna & operations'].objects:
 if 'mast' in ob.name.lower() or 'antenna' in ob.name.lower():
  ob.location.z=11.35+(ob.location.z-11.35)*.82;ob.scale.z*=.82
# Separate lower-right laboratory from the upper workshop in screen space.
for prefix,dz in [('13',-1.1),('22',-1.1),('14',-.65),('24',-.65)]:
 for coll in bpy.data.collections:
  if coll.name.startswith(prefix):
   for ob in coll.objects:ob.location.z+=dz
# Preserve circulation endpoints with a smooth localized descent.
for ob in bpy.data.collections['15 | CIRCULATION • bridges & stairs'].objects:
 if ob.type in {'MESH','CURVE'}:
  pts=[ob.matrix_world@Vector(v) for v in ob.bound_box];center=sum(pts,Vector())/8
  if center.x>5 and center.y<6:ob.location.z-=1.1*min(1,(center.x-5)/5)
# Light positions follow the laboratory move.
for ob in list(li.objects)+list(co.objects):
 if any(t in ob.name for t in ['About ceiling','About soft white','About blue pool']):ob.location.z-=1.1
# Fine rock-edge readability and frontal pedestal strata.
light('Projects rock side relief',(-6,-5,9),(0,3,0),500,6,color=(.57,.65,.76))
light('Left cliff relief',(-16,-7,11),(-21,3,3),400,7,color=(.57,.65,.76))
light('Right cliff relief',(18,-8,9),(23,3,2),300,6,color=(.57,.65,.76))
# The ring emits saturated blue; the center remains a restrained blue surface.
bluevent=mat('V4 | saturated table apertures',(.015,.24,1),.35,4)
for ob in s.objects:
 if ob.name.startswith('Holo table | blue vent'):
  ob.data.materials.clear();ob.data.materials.append(bluevent)
# Workstation display faces emit soft blue instead of outlines alone.
screenmat=mat('V4 | blue workstation glass',(.003,.017,.05),.4,.4)
for ob in s.objects:
 if ob.type=='MESH' and ('| screen' in ob.name or '| display glass' in ob.name) and 'perimeter' not in ob.name:
  ob.data=ob.data.copy();ob.data.materials.clear();ob.data.materials.append(screenmat)
# More breathing room around the central island.
pivot=Vector((0,5.3,7.65))
for coll in bpy.data.collections:
 if coll.name[:2] in ('10','21'):
  for ob in coll.objects:
   ob.location=pivot+(ob.location-pivot)*.89;ob.scale*=.89
# The blue table is secondary to its laboratory floor.
pivot=Vector((13.52245,-1.87912,6.85))
for ob in bpy.data.collections['22 | ABOUT ME • circular holographic table'].objects:
 ob.location=pivot+(ob.location-pivot)*.9;ob.scale*=.9
for ob in s.objects:
 if 'Railing | tubular' in ob.name or 'Railing | stanchion' in ob.name:ob.scale.x*=.72;ob.scale.y*=.72
# Suppress the obsolete exposed diagonal background route; restore a recessed crossing.
for ob in bpy.data.collections['15 | CIRCULATION • bridges & stairs'].objects:
 if ob.type in {'MESH','CURVE'}:
  pts=[ob.matrix_world@Vector(v) for v in ob.bound_box];c=sum(pts,Vector())/8
  if c.y>15 and c.x<11:ob.hide_render=True
# Manufactured bridge modules are separate from geological blocks.
def steelbox(name,pos,dim,material=None):
 me=bpy.data.meshes.new('V4 | '+name);bm=bmesh.new();bmesh.ops.create_cube(bm,size=1);bm.to_mesh(me);bm.free();ob=bpy.data.objects.new('V4 | '+name,me);co.objects.link(ob);ob.location=pos;ob.scale=dim;me.materials.append(material or bpy.data.materials['STRUCTURE | graphite powdercoat']);return ob
def beam(name,start,end,width=.045):
 start,end=Vector(start),Vector(end);ob=steelbox(name,(start+end)/2,(width,width,(end-start).length));ob.rotation_euler=(end-start).to_track_quat('Z','Y').to_euler();return ob
def walkway(start,end,width=1.1,steps=25):
 start,end=Vector(start),Vector(end);delta=end-start;side=Vector((-delta.y,delta.x,0)).normalized()*width/2
 for i in range(steps):
  p=start.lerp(end,(i+.5)/steps);ob=steelbox('rear bridge deck',p,(width,delta.xy.length/steps+.02,.12));ob.rotation_euler.z=math.atan2(-delta.x,delta.y)
 for sg in [-1,1]:
  for h in [.45,.95]:beam('rear bridge rail',start+side*sg+Vector((0,0,h)),end+side*sg+Vector((0,0,h)),.035)
  for i in range(10):
   p=start.lerp(end,i/9)+side*sg;beam('rear bridge stanchion',p,p+Vector((0,0,1)),.045)
walkway((0,18,8),(10.5,14,10.4))
# Stop the front-directed bounce lights from lighting the entire air volume.
surface_receivers=bpy.data.collections.new('V4 light receivers | surfaces');
for c in list(s.collection.children):
 if c.name[:2] in ('10','11','12','13','14','15','20','21','22','23','24','26','30'):surface_receivers.children.link(c)
for ob in li.objects:
 if ob.type=='LIGHT' and ob.data.type=='AREA' and 'mist' not in ob.name and 'Rear depth' not in ob.name:
  ob.light_linking.receiver_collection=surface_receivers
# The About center is a dim blue emitter without a white specular hotspot.
mm=bpy.data.materials['V4 | filled blue table'];nt=mm.node_tree;nt.nodes.clear();em=nt.nodes.new('ShaderNodeEmission');em.inputs[0].default_value=(.012,.15,.43,1);em.inputs[1].default_value=.75;oo=nt.nodes.new('ShaderNodeOutputMaterial');nt.links.new(em.outputs[0],oo.inputs['Surface'])
# Neutral-warm workshop task lighting and an independent cool ceiling shaft.
for ob in s.objects:
 if ob.type=='LIGHT' and 'workshop' in ob.name.lower() and 'warm' in ob.name.lower():ob.data.color=(1,.70,.47);ob.data.energy*=.7
fixture('Workshop visible white',(14,9.5,16.4),(14,12,10.7),2200,1.05)
# Lower the two-tier gallery into the foreground, preserving its internal structure.
for coll in bpy.data.collections:
 if coll.name[:2] in ('11','23'):
  for ob in coll.objects:ob.location.z-=.7
# Widen the laboratory enclosure; the smaller table retains its position.
pp=Vector((13.8,-.5,6.6))
for ob in bpy.data.collections['13 | ABOUT ME • holographic laboratory'].objects:
 ob.location.x=pp.x+(ob.location.x-pp.x)*1.12;ob.scale.x*=1.12
# A long diagonal exit runs from the laboratory down into the foreground abyss.
for ob in bpy.data.collections['15 | CIRCULATION • bridges & stairs'].objects:
 if ob.type in {'MESH','CURVE'}:
  vv=[ob.matrix_world@Vector(v) for v in ob.bound_box];cc=sum(vv,Vector())/8
  if cc.x>14 and cc.y<-5:ob.hide_render=True
start=Vector((18.9,-5.5,6.6));end=Vector((2,-22,-2.5));delta=end-start;side=Vector((-delta.y,delta.x,0)).normalized()*.9
for j in range(48):
 t=(j+.5)/48;pnt=start.lerp(end,t);ob=steelbox('long exit stair tread',pnt,(1.8,delta.xy.length/48+.035,.13));ob.rotation_euler.z=math.atan2(-delta.x,delta.y)
for sign in [-1,1]:
 for h in [.45,.98]:beam('long exit handrail',start+side*sign+Vector((0,0,h)),end+side*sign+Vector((0,0,h)),.038)
 beam('long exit stringer',start+side*sign-Vector((0,0,.16)),end+side*sign-Vector((0,0,.16)),.15)
 for j in range(16):
  pnt=start.lerp(end,j/15)+side*sign;beam('long exit post',pnt,pnt+Vector((0,0,1.03)),.042)
# Gentle roof underside definition.
light('Roof relief',(0,0,17),(0,14,23),650,12,color=(.45,.54,.68))
# Match lateral anchors measured from the reference while preserving center.
for c in bpy.data.collections:
 dx=-1.1 if c.name[:2] in ('12','20') else -1.15 if c.name[:2] in ('11','23') else 1.15 if c.name[:2] in ('13','22') else 0
 if dx:
  for ob in c.objects:ob.location.x+=dx
for ob in co.objects:
 if any(t in ob.name for t in ['Contact root','Contact block ledge']):ob.location.x-=1.1
 if any(t in ob.name for t in ['Experiences root','Experiences cavern brow']):ob.location.x-=1.15
 if any(t in ob.name for t in ['About root','About front shoulder','About cavern brow','long exit']):ob.location.x+=1.15
for ob in li.objects:
 if 'Contact' in ob.name:ob.location.x-=1.1
 if 'About' in ob.name:ob.location.x+=1.15
# Scale bridge positions continuously to the wider station anchors.
for ob in bpy.data.collections['15 | CIRCULATION • bridges & stairs'].objects:
 if ob.type in {'MESH','CURVE'}:
  vv=[ob.matrix_world@Vector(v) for v in ob.bound_box];cc=sum(vv,Vector())/8
  if cc.x<-4:ob.location.x-=min(1.1,(-cc.x-4)/8*1.1)
  elif cc.x>4 and cc.y<6:ob.location.x+=min(1.15,(cc.x-4)/8*1.15)
# A soft radial blue gradient gives the pool depth without white clipping.
mm=bpy.data.materials['V4 | filled blue table'];nt=mm.node_tree;em=next(n for n in nt.nodes if n.type=='EMISSION');tc2=nt.nodes.new('ShaderNodeTexCoord');dist=nt.nodes.new('ShaderNodeVectorMath');dist.operation='DISTANCE';dist.inputs[1].default_value=(.5,.5,1);nt.links.new(tc2.outputs['Generated'],dist.inputs[0]);rr=nt.nodes.new('ShaderNodeValToRGB');rr.color_ramp.elements[0].color=(.035,.28,.59,1);rr.color_ramp.elements[1].position=.53;rr.color_ramp.elements[1].color=(.007,.07,.23,1);nt.links.new(dist.outputs['Value'],rr.inputs[0]);nt.links.new(rr.outputs[0],em.inputs[0]);em.inputs[1].default_value=1
# Physically scattering fog in a continuous abyss, no visible water plane.
vol=bpy.data.materials.new('V4 | fine cool suspended cavern haze');vol.use_nodes=True;nt=vol.node_tree;nt.nodes.clear();out=nt.nodes.new('ShaderNodeOutputMaterial');pv=nt.nodes.new('ShaderNodeVolumePrincipled');pv.inputs['Density'].default_value=.0115;pv.inputs['Color'].default_value=(.40,.47,.56,1);pv.inputs['Anisotropy'].default_value=.28;nt.links.new(pv.outputs['Volume'],out.inputs['Volume'])
bpy.ops.mesh.primitive_cube_add(size=1,location=(0,25,5));fog=bpy.context.object;fog.name='V4 | atmospheric chasm volume';fog.scale=(62,40,66);fog.data.materials.append(vol)
for tag,pos,scale in [('About',(15,-.2,9),(12,8,8)),('Experience',(-17,-2,7),(12,8,7))]:
 vv=vol.copy();vv.name='V4 | local '+tag+' haze';vv.node_tree.nodes.get('Principled Volume').inputs['Density'].default_value=.010
 bpy.ops.mesh.primitive_cube_add(size=1,location=pos);ob=bpy.context.object;ob.name='V4 | local '+tag+' air';ob.scale=scale;ob.data.materials.append(vv)
# Moderate perspective retains the reference's compression and real ceiling depth.
from bpy_extras.object_utils import world_to_camera_view
s.camera.location=(0,-42.06,22.43);s.camera.rotation_euler.x=math.radians(74.0);s.camera.data.type='PERSP';s.camera.data.lens=33.0;s.camera.data.sensor_width=36;s.camera.data.sensor_fit='HORIZONTAL'
bpy.context.view_layer.update()
up=s.camera.rotation_euler.to_matrix()@Vector((0,1,0));right=Vector((1,0,0));forward=s.camera.rotation_euler.to_matrix()@Vector((0,0,-1))
station_specs=[('PROJECTS',('10','21'),(.494,.609),.225),('CONTACT',('12','20'),(.233,.387),.158),('EXPERIENCES',('11','23'),(.249,.856),.278),('ABOUT ME',('13','22'),(.790,.733),.250),('WORKSHOP',('14','24'),(.801,.378),.205)]
station_transforms=[]
for tag,prefixes,target,width in station_specs:
 group=list({ob for c in bpy.data.collections if c.name[:2] in prefixes for ob in c.objects})
 labelob=bpy.data.objects[tag+' | lettering'];pivot=labelob.matrix_world.translation.copy()
 base=next(c for c in bpy.data.collections if c.name.startswith(prefixes[0]+' |'))
 points=[world_to_camera_view(s,s.camera,ob.matrix_world@Vector(v)).x for ob in base.objects if ob.type=='MESH' and not ob.hide_render for v in ob.bound_box]
 fac=max(.50,min(1.50,width/(max(points)-min(points))))
 for ob in group:ob.location=pivot+(ob.location-pivot)*fac;ob.scale*=fac
 bpy.context.view_layer.update();uv=world_to_camera_view(s,s.camera,labelob.matrix_world.translation);depth=(pivot-s.camera.location).dot(forward);fw=depth*36/s.camera.data.lens;fh=fw*s.render.resolution_y/s.render.resolution_x
 delta=right*((target[0]-uv.x)*fw)+up*((1-target[1]-uv.y)*fh)
 for ob in group:ob.location+=delta
 station_transforms.append((tag,pivot,fac,delta))
 print('Station fit',tag,fac,tuple(delta),flush=True)
 # Attach station foundations and practical lights to the same transform.
 for ob in list(co.objects)+list(li.objects):
  name=ob.name.lower();hit=(tag=='PROJECTS' and any(t in name for t in ['projects','central outlying','central low'])) or (tag=='CONTACT' and 'contact' in name) or (tag=='EXPERIENCES' and any(t in name for t in ['experiences','experience','education'])) or (tag=='ABOUT ME' and 'about' in name) or (tag=='WORKSHOP' and 'workshop' in name)
  if hit:ob.location=pivot+(ob.location-pivot)*fac+delta;ob.scale*=fac
# Continuous deformation keeps the many shared bridge components connected.
def bridge_delta(q):
 weights=[1/max(2,(q-p).length)**5 for _,p,_,_ in station_transforms];total=sum(weights)
 return sum((((q-p)*(fac-1)+d)*(w/total) for w,(_,p,fac,d) in zip(weights,station_transforms)),Vector())
bridge_objects=list(bpy.data.collections['15 | CIRCULATION • bridges & stairs'].objects)+[ob for ob in co.objects if 'rear bridge' in ob.name or 'long exit' in ob.name]
for ob in bridge_objects:
 if ob.hide_render:continue
 M=ob.matrix_world.copy();inv=M.inverted()
 if ob.type=='MESH':
  ob.data=ob.data.copy()
  for v in ob.data.vertices:
   q=M@v.co;v.co=inv@(q+bridge_delta(q))
 elif ob.type=='CURVE':
  ob.data=ob.data.copy()
  for sp in ob.data.splines:
   for pt in sp.points:
    q=M@Vector(pt.co[:3]);v=inv@(q+bridge_delta(q));pt.co=(*v,1)
# A slimmer blue label treatment.
for ob in s.objects:
 if ob.type=='FONT' and 'lettering' in ob.name:ob.scale.x*=.9;ob.scale.z*=1.12
label.node_tree.nodes.get('Principled BSDF').inputs['Emission Strength'].default_value=1.4
# A finite overhead emitter makes a soft shaft without a sharp spotlight apex.
central=next(ob for ob in li.objects if ob.name=='V4 | Central overhead');central.data.type='AREA';central.data.shape='DISK';central.data.size=2.8;central.data.spread=math.radians(65);central.data.energy=650
for ob in li.objects:
 if ob.type=='LIGHT' and 'Contact' in ob.name:ob.data.energy*=.62
 if ob.type=='LIGHT' and ('Experience work floor' in ob.name or 'Projects ceiling bounce' in ob.name):ob.data.energy*=.72
# Bright glass center, subdued metal surround.
mm=bpy.data.materials['V4 | filled blue table'];nt=mm.node_tree;em=next(n for n in nt.nodes if n.type=='EMISSION');r=next(n for n in nt.nodes if n.type=='VALTORGB');r.color_ramp.elements[0].color=(.055,.39,.72,1);r.color_ramp.elements[1].color=(.008,.10,.27,1);em.inputs[1].default_value=1.1
# Quiet metal framing and safety lines keep the practical lights dominant.
for name in ['FRAME | worn gunmetal']:
 mm=bpy.data.materials[name];pp=mm.node_tree.nodes.get('Principled BSDF');pp.inputs['Base Color'].default_value=(.075,.09,.105,1);pp.inputs['Roughness'].default_value=.52
mm=bpy.data.materials['SAFETY | ochre yellow'];pp=mm.node_tree.nodes.get('Principled BSDF');pp.inputs['Base Color'].default_value=(.19,.12,.045,1)
toolmat=mat('V4 | dark steel tools',(.12,.135,.15),.52)
for ob in s.objects:
 if ob.type=='MESH' and any(t in ob.name for t in ['Workshop | hanging tool shaft','Workshop | wrench head','Workshop | open-ended spanner','Workshop | hammer head','Workshop | pliers jaws']):
  ob.data=ob.data.copy();ob.data.materials.clear();ob.data.materials.append(toolmat)
# Warm room bounce is localized behind the workshop front.
for ob in s.objects:
 if ob.type=='LIGHT' and 'workshop' in ob.name.lower() and 'warm' in ob.name.lower():ob.data.energy*=1.65
# Replace stair-like horizontal bridge panels with coplanar sloped metal decks.
def deck_bridge(a,b,width=1.3,tag='catwalk'):
 a,b=Vector(a),Vector(b);vec=b-a;u=vec.normalized();side=Vector((-u.y,u.x,0)).normalized();normal=u.cross(side).normalized();count=max(4,round(vec.length/.72))
 for j in range(count):
  center=a.lerp(b,(j+.5)/count);hh=vec.length/count/2-.008;ww=width/2;th=.055
  vs=[center+u*xx+side*yy+normal*zz for zz in [-th,th] for yy in [-ww,ww] for xx in [-hh,hh]]
  me=bpy.data.meshes.new('V4 | '+tag+' sloped plate');me.from_pydata(vs,[],[(0,2,3,1),(4,5,7,6),(0,1,5,4),(2,6,7,3),(0,4,6,2),(1,3,7,5)]);me.materials.append(bpy.data.materials['DECK | titanium panels']);ob=bpy.data.objects.new(me.name,me);co.objects.link(ob)
 for sg in [-1,1]:
  for h in [.45,.98]:beam(tag+' rail',a+side*sg*width/2+Vector((0,0,h)),b+side*sg*width/2+Vector((0,0,h)),.028)
  beam(tag+' edge girder',a+side*sg*width/2-Vector((0,0,.14)),b+side*sg*width/2-Vector((0,0,.14)),.12)
  for j in range(max(2,round(vec.length/1.3))+1):
   pnt=a.lerp(b,j/max(2,round(vec.length/1.3)))+side*sg*width/2;beam(tag+' post',pnt,pnt+Vector((0,0,1)),.038)
for prefix in ['Projects → Experiences','Projects → About']:
 panels=[ob for ob in bpy.data.collections['15 | CIRCULATION • bridges & stairs'].objects if ob.name.startswith(prefix+' | deck panel') and not ob.hide_render]
 centers=[sum((ob.matrix_world@Vector(v) for v in ob.bound_box),Vector())/8 for ob in panels];centers.sort(key=lambda q:q.x)
 if len(centers)<2:continue
 a0,b0=centers[0],centers[-1];u=(b0-a0).normalized();a0-=u*.35;b0+=u*.35
 # Snap the route to the actual transformed deck boundaries.
 hub=bpy.data.objects['PROJECTS | floor'];hp=[hub.matrix_world@v.co for v in hub.data.vertices];hc=sum(hp,Vector())/len(hp);hz=max(q.z for q in hp)
 if 'Experiences' in prefix:
  ep=[ob.matrix_world@v.co for ob in bpy.data.collections['11 | EXPERIENCES • two-tier gallery'].objects if ob.type=='MESH' and 'upper Education' in ob.name and 'floor' in ob.name for v in ob.data.vertices]
 else:
  ab=bpy.data.objects['ABOUT ME | floor'];ep=[ab.matrix_world@v.co for v in ab.data.vertices]
 if ep:
  ec=sum(ep,Vector())/len(ep);ez=max(q.z for q in ep);direction=Vector((ec.x-hc.x,ec.y-hc.y,0)).normalized();hboundary=max(hp,key=lambda q:(q-hc).dot(direction));eboundary=min(ep,key=lambda q:(Vector((q.x,q.y,0))-Vector((hc.x,hc.y,0))).length_squared)
  a0=Vector((hboundary.x,hboundary.y,hz))-direction*.18;b0=Vector((eboundary.x,eboundary.y,ez))+direction*.12
 vec=b0-a0
 for ob in bpy.data.collections['15 | CIRCULATION • bridges & stairs'].objects:
  if ob.type not in {'MESH','CURVE'}:continue
  c=sum((ob.matrix_world@Vector(v) for v in ob.bound_box),Vector())/8;t=max(0,min(1,(c-a0).dot(vec)/vec.length_squared));nearest=a0+vec*t
  if ob.name.startswith(prefix) or ((c-nearest).xy.length<2.6 and -2<c.z-nearest.z<2.5 and ('Railing' in ob.name or 'Bollard' in ob.name)):ob.hide_render=True
 deck_bridge(a0,b0,1.3,prefix)
# Clear geological overlaps across station signs and the workshop opening.
bpy.context.view_layer.update()
protected=[]
for tag,_,target,_ in station_specs:
 lab=bpy.data.objects[tag+' | lettering'];d=(lab.matrix_world.translation-s.camera.location).dot(forward);protected.append((target[0]-.044,target[0]+.044,1-target[1]-.013,1-target[1]+.018,d))
wl=bpy.data.objects['WORKSHOP | lettering'];wd=(wl.matrix_world.translation-s.camera.location).dot(forward);protected.append((.72,.879,.64,.80,wd+1))
for ob in co.objects:
 if ob.type!='MESH' or not ob.data.materials or ob.data.materials[0]!=rock:continue
 c=ob.matrix_world.translation;uv=world_to_camera_view(s,s.camera,c);d=(c-s.camera.location).dot(forward)
 if any(x0<uv.x<x1 and y0<uv.y<y1 and d<dd for x0,x1,y0,y1,dd in protected):ob.hide_render=True
# The distant exit reads as a narrow catwalk instead of an oversized stair flight.
treads=[ob for ob in co.objects if 'long exit stair tread' in ob.name];pts=[sum((ob.matrix_world@Vector(v) for v in ob.bound_box),Vector())/8 for ob in treads];pts.sort(key=lambda q:q.y,reverse=True)
if pts:
 for ob in list(co.objects):
  if 'long exit' in ob.name:ob.hide_render=True
 deck_bridge(pts[0],pts[-1],1.12,'Abyss exit')
# Sign faces sit just ahead of the metal fascia.
for ob in s.objects:
 if ob.type=='FONT' and 'lettering' in ob.name:ob.location+=(s.camera.location-ob.location).normalized()*.09
# Depth increases gradually down into the foreground abyss.
lv=vol.copy();lv.name='V4 | graded lower abyss mist';nt=lv.node_tree;pv=nt.nodes.get('Principled Volume');tex=nt.nodes.new('ShaderNodeTexCoord');sep=nt.nodes.new('ShaderNodeSeparateXYZ');nt.links.new(tex.outputs['Generated'],sep.inputs[0]);r=nt.nodes.new('ShaderNodeMapRange');r.inputs['From Min'].default_value=0;r.inputs['From Max'].default_value=1;r.inputs['To Min'].default_value=.032;r.inputs['To Max'].default_value=.002;nt.links.new(sep.outputs['Z'],r.inputs[0]);nt.links.new(r.outputs[0],pv.inputs['Density'])
bpy.ops.mesh.primitive_cube_add(size=1,location=(0,0,-5));ob=bpy.context.object;ob.name='V4 | graded foreground abyss';ob.scale=(52,40,20);ob.data.materials.append(lv)
# Persist full camera aspect and rendering settings in the artifact.
s.render.engine='CYCLES';s.cycles.samples=a.samples;s.cycles.use_denoising=True
try:
 prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='METAL';prefs.get_devices()
 for dev in prefs.devices:dev.use=True
 s.cycles.device='GPU'
except Exception:s.cycles.device='CPU'
s.render.filepath=OUT+'/pass-%02d.png'%a.stage
s['v4_reference']='design-references/misty-abyss/blockwork-cavern-central-light-v4.png';s['v4_generator']='rebuild_v4.py';s['v4_seed']=416
bpy.ops.wm.save_as_mainfile(filepath=OUT+'/pass-%02d.blend'%a.stage)
bpy.ops.render.render(write_still=True)
