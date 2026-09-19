"""Scoped revision: geology, illumination, metals, accents, water and depth only.
Always starts from the preserved delivered scene. Architecture/camera/anchors stay fixed.
"""
import bpy,bmesh,math,os,json,sys,argparse,random
from mathutils import Vector
from mathutils.noise import noise_vector,noise
from math import sin,cos,pi
ROOT=os.path.dirname(os.path.abspath(__file__));OUT=os.path.join(ROOT,'atmosphere-review')
ap=argparse.ArgumentParser();ap.add_argument('--pass',dest='stage',type=int,default=1);ap.add_argument('--samples',type=int,default=48);ap.add_argument('--width',type=int,default=1696)
opt=ap.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
bpy.ops.wm.open_mainfile(filepath=os.path.join(OUT,'before-atmosphere.blend'));S=bpy.context.scene
camera_matrix=[list(r) for r in S.camera.matrix_world]
anchors=S['area_anchors_json']
architecture={o.name:[list(r) for r in o.matrix_world] for o in S.objects if o.type in {'MESH','CURVE','FONT'} and not any(m and (m.name.startswith('ROCK') or m.name.startswith('WATER') or m.name.startswith('ATMOSPHERE')) for m in o.data.materials)}
def mat(name,color,metal=0,rough=.7,emission=0):
 m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=rough
 p.inputs['Emission Color'].default_value=(*color,1);p.inputs['Emission Strength'].default_value=emission
 return m
def ramp(nt,socket,colors):
 r=nt.nodes.new('ShaderNodeValToRGB');r.color_ramp.elements.remove(r.color_ramp.elements[1])
 for i,(pos,color) in enumerate(colors):
  e=r.color_ramp.elements[0] if i==0 else r.color_ramp.elements.new(pos);e.position=pos;e.color=color
 nt.links.new(socket,r.inputs['Fac']);return r.outputs['Color']
def mathnode(nt,op,a,b=None):
 n=nt.nodes.new('ShaderNodeMath');n.operation=op
 if isinstance(a,(float,int)):n.inputs[0].default_value=a
 else:nt.links.new(a,n.inputs[0])
 if b is not None:
  if isinstance(b,(float,int)):n.inputs[1].default_value=b
  else:nt.links.new(b,n.inputs[1])
 return n.outputs[0]
def noise_node(nt,coords,scale,detail=2,rough=.6):
 n=nt.nodes.new('ShaderNodeTexNoise');n.inputs['Scale'].default_value=scale;n.inputs['Detail'].default_value=detail;n.inputs['Roughness'].default_value=rough;nt.links.new(coords,n.inputs['Vector']);return n
def vector_scale(nt,coords,value):
 n=nt.nodes.new('ShaderNodeVectorMath');n.operation='MULTIPLY';n.inputs[1].default_value=value;nt.links.new(coords,n.inputs[0]);return n.outputs['Vector']

# Geological material: continuous sloping bedding, dark fissures, eroded granular relief.
rockmat=mat('GEOLOGY | eroded stratified dark limestone',(.032,.038,.043),0,.88)
nt=rockmat.node_tree;p=nt.nodes.get('Principled BSDF');p.inputs['Specular IOR Level'].default_value=.24
geo=nt.nodes.new('ShaderNodeNewGeometry');coords=geo.outputs['Position']
macro=noise_node(nt,coords,.65,3,.6);micro=noise_node(nt,coords,11,3,.65)
dot=nt.nodes.new('ShaderNodeVectorMath');dot.operation='DOT_PRODUCT';dot.inputs[1].default_value=(.14,.08,1);nt.links.new(coords,dot.inputs[0])
warped=mathnode(nt,'ADD',dot.outputs['Value'],mathnode(nt,'MULTIPLY',macro.outputs['Fac'],.55))
bedding=noise_node(nt,vector_scale(nt,coords,(.8,.7,1.8)),1.1,4,.68).outputs['Fac']
bedding01=bedding
layercolor=ramp(nt,bedding01,[(0,(.015,.020,.023,1)),(.35,(.026,.032,.035,1)),(.65,(.038,.043,.046,1)),(1,(.052,.056,.057,1))])
mix=nt.nodes.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';mix.inputs[0].default_value=.5;nt.links.new(layercolor,mix.inputs[1]);nt.links.new(ramp(nt,macro.outputs['Fac'],[(.1,(.42,.46,.48,1)),(.9,(1,1,1,1))]),mix.inputs[2]);nt.links.new(mix.outputs[0],p.inputs['Base Color'])
nt.links.new(ramp(nt,macro.outputs['Fac'],[(0,(.76,.76,.76,1)),(1,(.98,.98,.98,1))]),p.inputs['Roughness'])
b1=nt.nodes.new('ShaderNodeBump');b1.inputs['Strength'].default_value=.48;b1.inputs['Distance'].default_value=.21;nt.links.new(bedding01,b1.inputs['Height'])
b2=nt.nodes.new('ShaderNodeBump');b2.inputs['Strength'].default_value=.32;b2.inputs['Distance'].default_value=.040;nt.links.new(micro.outputs['Fac'],b2.inputs['Height']);nt.links.new(b1.outputs['Normal'],b2.inputs['Normal']);nt.links.new(b2.outputs['Normal'],p.inputs['Normal'])
# Interrupted mineral fractures and chipped granular relief cross the larger bedding.
vor=nt.nodes.new('ShaderNodeTexVoronoi');vor.feature='DISTANCE_TO_EDGE';vor.inputs['Scale'].default_value=.85;nt.links.new(vector_scale(nt,coords,(1,1,1.6)),vor.inputs['Vector'])
crack=mathnode(nt,'MULTIPLY',mathnode(nt,'LESS_THAN',vor.outputs['Distance'],.026),mathnode(nt,'GREATER_THAN',macro.outputs['Fac'],.40))
cm=nt.nodes.new('ShaderNodeMixRGB');nt.links.new(mathnode(nt,'MULTIPLY',crack,.48),cm.inputs[0]);nt.links.new(mix.outputs[0],cm.inputs[1]);cm.inputs[2].default_value=(.009,.012,.014,1);nt.links.new(cm.outputs[0],p.inputs['Base Color'])
b3=nt.nodes.new('ShaderNodeBump');b3.invert=True;b3.inputs['Strength'].default_value=.20;b3.inputs['Distance'].default_value=.060;nt.links.new(crack,b3.inputs['Height']);nt.links.new(b2.outputs['Normal'],b3.inputs['Normal']);nt.links.new(b3.outputs['Normal'],p.inputs['Normal'])
# Thin, discontinuous bedding seams, warped by broad geological erosion.
strata=mathnode(nt,'SINE',mathnode(nt,'ADD',mathnode(nt,'MULTIPLY',dot.outputs['Value'],17),mathnode(nt,'MULTIPLY',macro.outputs['Fac'],7)))
seams=mathnode(nt,'MULTIPLY',mathnode(nt,'LESS_THAN',strata,-.85),mathnode(nt,'GREATER_THAN',micro.outputs['Fac'],.40))
sm=nt.nodes.new('ShaderNodeMixRGB');nt.links.new(mathnode(nt,'MULTIPLY',seams,.30),sm.inputs[0]);nt.links.new(cm.outputs[0],sm.inputs[1]);sm.inputs[2].default_value=(.008,.011,.013,1);nt.links.new(sm.outputs[0],p.inputs['Base Color'])
b4=nt.nodes.new('ShaderNodeBump');b4.invert=True;b4.inputs['Strength'].default_value=.26;b4.inputs['Distance'].default_value=.048;nt.links.new(seams,b4.inputs['Height']);nt.links.new(b3.outputs['Normal'],b4.inputs['Normal']);nt.links.new(b4.outputs['Normal'],p.inputs['Normal'])
farrock=rockmat.copy();farrock.name='GEOLOGY | distant eroded stone'

# Reconstruct only geological meshes. Retain their spine, taper and scene transforms.
# Seven to eleven persistent planes replace independent ring-vertex jitter.
geology=[]
for ob in list(S.objects):
 if ob.type!='MESH' or len(ob.data.vertices)<100:continue
 if not ob.data.materials or not all(m and m.name.startswith('ROCK') for m in ob.data.materials):continue
 me=ob.data;N=len(me.polygons[-1].vertices)
 if N<8 or len(me.vertices)%N:continue
 levels=len(me.vertices)//N-1
 if levels<3:continue
 old=[v.co.copy() for v in me.vertices]
 centers=[];radii=[]
 for j in range(levels+1):
  ring=old[j*N:(j+1)*N];c=sum(ring,Vector())/N;centers.append(c)
  radii.append((sum(abs(v.x-c.x) for v in ring)/N*pi/2,sum(abs(v.y-c.y) for v in ring)/N*pi/2))
 def avg(seq,j,window):return sum(seq[max(0,j-window):min(len(seq),j+window+1)],seq[0]*0)/len(seq[max(0,j-window):min(len(seq),j+window+1)])
 rx=[r[0] for r in radii];ry=[r[1] for r in radii];phase=(sum(ord(c) for c in ob.name)%93)*.11
 angular=11;new=[]
 rng=random.Random(sum(ord(c) for c in ob.name));planes=[(k*2*pi/angular+rng.uniform(-.18,.18),rng.uniform(.75,1.10),rng.uniform(-.025,.025)) for k in range(angular)]
 h=centers[-1].z-centers[0].z
 # Denser vertical samples resolve eroded ledges without adding random facet jitter.
 oldlevels=levels;levels=max(levels,round(abs(h)/.19))
 def resample(seq):
  out=[]
  for k in range(levels+1):
   fj=k/levels*oldlevels;ij=min(oldlevels-1,int(fj));u=fj-ij
   out.append(seq[ij]*(1-u)+seq[ij+1]*u)
  return out
 centers=resample(centers);rx=resample(rx);ry=resample(ry)
 for j,c0 in enumerate(centers):
  t=j/levels;c=avg(centers,j,2);c.z=c0.z
  ax=avg(rx,j,2) if 1<j<levels-1 else rx[j];ay=avg(ry,j,2) if 1<j<levels-1 else ry[j]
  for i in range(N):
   a=2*pi*i/N
   approx=Vector((c.x+cos(a)*ax,c.y+sin(a)*ay,c.z))
   bedding_z=approx.z+.27*approx.x+.17*approx.y
   level_z=bedding_z*.61+.36*sin(bedding_z*.5+phase);li=math.floor(level_z);lf=level_z-li
   u=min(1,lf/.28);u=u*u*(3-2*u)
   offsets=[]
   for normal,offset,tilt in planes:
    if cos(a-normal-phase)<=.08:continue
    prev=(sin((li-1)*127.1+normal*311.7+phase)*43758.5453)%1*2-1;now=(sin(li*127.1+normal*311.7+phase)*43758.5453)%1*2-1
    layered=.16*(prev*(1-u)+now*u)
    offsets.append((offset+layered+tilt*(c.z-centers[0].z))/cos(a-normal-phase))
   plane=max(.38,min(offsets))
   q=Vector((c.x+cos(a)*ax*plane,c.y+sin(a)*ay*plane,c.z))
   nv=noise_vector(q*.43+Vector((phase,phase*.31,0)))
   bed=q.z+.28*q.x+.16*q.y+.20*sin(q.x*.45+phase)
   bz=bed*.79+.42*sin(bed*.41+phase);bi=math.floor(bz);bf=bz-bi
   prev=sin((bi-1)*17.19+phase*3.4);current=sin(bi*17.19+phase*3.4)
   u=min(1,bf/.12);u=u*u*(3-2*u)
   shelf=.16*(prev*(1-u)+current*u)*(.55+.45*noise(q*.31))
   erosion=.22*noise_vector(Vector((q.x*.28+phase,q.y*.28,q.z*.7))).x+.04*noise(q*2.2)
   amount=(shelf+erosion)*min(1,abs(h)/3)*min(1,ax/.9)
   q.x+=cos(a)*amount;q.y+=sin(a)*amount;q.z+=.12*nv.y
   new.append(q)
 faces=[]
 for j in range(levels):
  for i in range(N):a=j*N+i;b=j*N+(i+1)%N;faces.append((a,b,b+N,a+N))
 faces += [tuple(reversed(range(N))),tuple(range(levels*N,(levels+1)*N))]
 if h<0:faces=[tuple(reversed(f)) for f in faces]
 fresh=bpy.data.meshes.new(ob.name+' | continuous eroded strata');fresh.from_pydata(new,[],faces);fresh.update();ob.data=fresh
 distant=ob.name.startswith('Distant') or ob.name.startswith('Depth')
 fresh.materials.append(farrock if distant else rockmat)
 for f in fresh.polygons:f.use_smooth=True
 fresh.set_sharp_from_angle(angle=math.radians(45))
 ob['geology_revision']='Persistent fracture planes, continuous sloping bedding and coherent erosion; no random triangle colors.'
 geology.append(ob.name)
print('Resculpted geological masses',len(geology),flush=True)
ledge_count=0

# Metal response: subdued alloys, correlated roughness, thin directional abrasion.
for m in list(bpy.data.materials):
 if not m.use_nodes or m.name.startswith(('GEOLOGY','ROCK','LIGHT','DISPLAY','ATMOSPHERE')):continue
 p=m.node_tree.nodes.get('Principled BSDF')
 if not p:continue
 if not any(k in m.name for k in ['STRUCTURE','FRAME','DECK','HARDWARE','PROJECTS | neutral','RECESSES','ANTENNA']):continue
 nt=m.node_tree
 old=list(p.inputs['Normal'].links)
 for link in old:nt.links.remove(link)
 c=p.inputs['Base Color'].default_value[:3]
 if 'HARDWARE' in m.name:c=(.24,.27,.29);metal=.82
 elif 'ANTENNA' in m.name:c=(.43,.46,.44);metal=.22
 else:c=tuple(v*.73 for v in c);metal=.68
 p.inputs['Base Color'].default_value=(*c,1);p.inputs['Metallic'].default_value=metal;p.inputs['Coat Weight'].default_value=0;p.inputs['Specular IOR Level'].default_value=.35
 geo=nt.nodes.new('ShaderNodeNewGeometry');coord=geo.outputs['Position'];broad=noise_node(nt,coord,1.25,3,.7)
 nt.links.new(ramp(nt,broad.outputs['Fac'],[(.28,(.49,.49,.49,1)),(.50,(.61,.61,.61,1)),(.70,(.74,.74,.74,1))]),p.inputs['Roughness'])
 tint=ramp(nt,broad.outputs['Fac'],[(.25,(*[v*.90 for v in c],1)),(.72,(*[v*1.06 for v in c],1))]);nt.links.new(tint,p.inputs['Base Color'])
 brush=noise_node(nt,vector_scale(nt,coord,(16,1.2,3)),1.8,3,.65)
 bump=nt.nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.20;bump.inputs['Distance'].default_value=.009;nt.links.new(brush.outputs['Fac'],bump.inputs['Height']);nt.links.new(bump.outputs['Normal'],p.inputs['Normal'])
 # Thin, sparse directional scuffs and worn convex edges remain low contrast.
 scratches=mathnode(nt,'GREATER_THAN',brush.outputs['Fac'],.64)
 worn=nt.nodes.new('ShaderNodeMixRGB');worn.blend_type='MIX';nt.links.new(mathnode(nt,'MULTIPLY',scratches,.12),worn.inputs[0]);nt.links.new(tint,worn.inputs[1]);worn.inputs[2].default_value=(*[min(.45,v*1.75) for v in c],1);nt.links.new(worn.outputs[0],p.inputs['Base Color'])
 tc=nt.nodes.new('ShaderNodeTexCoord');sep=nt.nodes.new('ShaderNodeSeparateXYZ');nt.links.new(tc.outputs['Generated'],sep.inputs[0])
 nearx=mathnode(nt,'MINIMUM',sep.outputs['X'],mathnode(nt,'SUBTRACT',1,sep.outputs['X']));neary=mathnode(nt,'MINIMUM',sep.outputs['Y'],mathnode(nt,'SUBTRACT',1,sep.outputs['Y']))
 edgemask=mathnode(nt,'LESS_THAN',mathnode(nt,'MINIMUM',nearx,neary),.055)
 edgewear=nt.nodes.new('ShaderNodeMixRGB');nt.links.new(mathnode(nt,'MULTIPLY',edgemask,mathnode(nt,'MULTIPLY',broad.outputs['Fac'],.28)),edgewear.inputs[0]);nt.links.new(worn.outputs[0],edgewear.inputs[1]);edgewear.inputs[2].default_value=(*[min(.4,v*1.65) for v in c],1);nt.links.new(edgewear.outputs[0],p.inputs['Base Color'])



exec(compile(open(os.path.join(ROOT,'apply_scanned_materials.py')).read(),'apply_scanned_materials.py','exec'))

exec(compile(open(os.path.join(ROOT,'add_scanned_rock_faces.py')).read(),'add_scanned_rock_faces.py','exec'))
exec(compile(open(os.path.join(ROOT,'connect_geological_forms.py')).read(),'connect_geological_forms.py','exec'))
exec(compile(open(os.path.join(ROOT,'weather_deck_surfaces.py')).read(),'weather_deck_surfaces.py','exec'))

# Emission is graded by area and function instead of an equally bright global palette.
material_variants={};mesh_variants={}
def graded(source,strength,color=None,tag=''):
 key=(source.name,strength,tuple(color) if color else None,tag)
 if key in material_variants:return material_variants[key]
 m=source.copy();m.name='ACCENT | '+tag+' | '+source.name
 p=m.node_tree.nodes.get('Principled BSDF')
 if p:
  p.inputs['Emission Strength'].default_value=strength
  if source.name.startswith('LIGHT'):
   base=p.inputs['Base Color'].default_value[:3];factor=.30 if tag=='Projects' else .12
   p.inputs['Base Color'].default_value=(*[v*factor for v in base],1);p.inputs['Roughness'].default_value=.45
  if color:
   for link in list(p.inputs['Emission Color'].links):m.node_tree.links.remove(link)
   p.inputs['Emission Color'].default_value=(*color,1)
 material_variants[key]=m;return m
for idx,ob in enumerate(list(S.objects)):
 if ob.type not in {'MESH','CURVE','FONT'}:continue
 names=' '.join(c.name for c in ob.users_collection);primary='21 |' in names;about='22 |' in names
 repl=[];changed=False
 for source in ob.data.materials:
  if not source:repl.append(source);continue
  m=source
  if source.name.startswith('LIGHT | cyan'):
   power=1.25 if primary else .18
   if 'grille' in ob.name or 'keypad' in ob.name or 'data row' in ob.name:power*=.65
   if about:power=.12
   m=graded(source,power,tag='Projects' if primary else 'Secondary cyan')
  elif source.name.startswith('LIGHT | white'):
   power=.65 if primary else .20
   if about:power=.11
   if 'lettering' in ob.name:power=.38 if 'PROJECTS' in ob.name else .19
   if any(t in ob.name for t in ['diffuser','luminaire','overhead strip','horizontal wall strip']):power=1.7
   m=graded(source,power,tag='Practical white' if power>1 else 'Quiet white')
  elif source.name.startswith('LIGHT | amber'):
   power=.65
   if 'Bollard | amber lens' in ob.name:power=.55 if idx%7==0 else .012
   if 'Edge lamp' in ob.name:power=.45 if idx%5==0 else .025
   if 'luminous timeline' in ob.name:power=.20
   if 'flame' in ob.name:power=1.4
   m=graded(source,power,(1,.19,.025),tag='Sparse amber')
  elif source.name.startswith('DISPLAY | luminous blue surface'):
   m=graded(source,.16,(.018,.13,.22),tag='Secondary table')
   m.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(.001,.003,.005,1)
  if m!=source:changed=True
  repl.append(m)
 if changed:
  key=(ob.data.as_pointer(),tuple(m.name if m else '' for m in repl))
  if key not in mesh_variants:
   data=ob.data.copy();data.materials.clear()
   for m in repl:data.materials.append(m)
   mesh_variants[key]=data
  ob.data=mesh_variants[key]

# Restrained hologram: dark glass center with a narrow cyan perimeter glow.
# A portable emission texture and explicit cap UVs keep the runtime material practical.
ob=S.objects['Holo table | luminous inset'];m=ob.data.materials[0];p=m.node_tree.nodes.get('Principled BSDF');nt=m.node_tree
sz=512;yy,xx=np.mgrid[0:sz,0:sz].astype(np.float32);rr=np.sqrt(((xx+.5)/sz-.5)**2+((yy+.5)/sz-.5)**2)
weight=np.clip((rr-.36)/.115,0,1);weight=weight*weight*(3-2*weight)
rgb=np.array([.006,.014,.023])[None,None,:]*(1-weight[:,:,None])+np.array([.020,.16,.23])[None,None,:]*weight[:,:,None]
a=np.ones((sz,sz,4),np.float32);a[:,:,:3]=np.where(rgb<=.0031308,rgb*12.92,1.055*rgb**(1/2.4)-.055)
im=bpy.data.images.new('Hologram | subtle cyan perimeter',width=sz,height=sz,alpha=True);im.pixels.foreach_set(a.ravel());im.filepath_raw=os.path.join(TEX,'hologram_perimeter.png');im.file_format='PNG';im.save();im.pack()
n=nt.nodes.new('ShaderNodeTexImage');n.image=im;nt.links.new(n.outputs['Color'],p.inputs['Emission Color']);p.inputs['Emission Strength'].default_value=.30
p.inputs['Base Color'].default_value=(.001,.003,.005,1)
uv=ob.data.uv_layers.new(name='Hologram cap UV');radius=max(abs(v.co.x) for v in ob.data.vertices)
for f in ob.data.polygons:
 for li in f.loop_indices:
  q=ob.data.vertices[ob.data.loops[li].vertex_index].co;uv.data[li].uv=(.5+q.x/(radius*2),.5+q.y/(radius*2))

# A dark basin with finite short waves and fine directional normals.
waterob=next(o for o in S.objects if o.name.startswith('Water | rippled'))
for v in waterob.data.vertices:
 x,y=v.co.x,v.co.y;amp=.35+.75*noise(Vector((x*.12,y*.12,1)));warp=1.8*noise(Vector((x*.17,y*.17,0)));v.co.z=.9+amp*(.035*sin(x*1.8+y*3.6+warp)+.018*sin(x*4.6-y*1.5+warp))
water=mat('WATER | dark moving basin',(.0015,.004,.007),0,.20)
nt=water.node_tree;p=nt.nodes.get('Principled BSDF');p.inputs['IOR'].default_value=1.333;p.inputs['Specular IOR Level'].default_value=.12;p.inputs['Coat Weight'].default_value=0
geo=nt.nodes.new('ShaderNodeNewGeometry');tex=noise_node(nt,vector_scale(nt,geo.outputs['Position'],(1,2.8,1)),5.0,3,.58)
sep=nt.nodes.new('ShaderNodeSeparateXYZ');nt.links.new(geo.outputs['Position'],sep.inputs[0]);warp=noise_node(nt,geo.outputs['Position'],.22,2,.6);phase=mathnode(nt,'ADD',mathnode(nt,'MULTIPLY',sep.outputs['X'],6),mathnode(nt,'ADD',mathnode(nt,'MULTIPLY',sep.outputs['Y'],13),mathnode(nt,'MULTIPLY',warp.outputs['Fac'],12)));wave=mathnode(nt,'SINE',phase)
b=nt.nodes.new('ShaderNodeBump');b.inputs['Strength'].default_value=.28;b.inputs['Distance'].default_value=.047;nt.links.new(mathnode(nt,'ADD',tex.outputs['Fac'],mathnode(nt,'MULTIPLY',wave,.012)),b.inputs['Height']);nt.links.new(b.outputs['Normal'],p.inputs['Normal']);waterob.data.materials.clear();waterob.data.materials.append(water)

# Existing practical fixtures remain. Broad fill and redundant light pools are disabled.
for ob in S.objects:
 if ob.type!='LIGHT':continue
 ob.data.energy=0
 if 'Workshop | warm task wash' in ob.name:ob.data.energy=140;ob.data.color=(1,.49,.24)
 if 'Workshop' in ob.name and 'overhead pool' in ob.name:ob.data.energy=250;ob.data.color=(.78,.75,.70)
 if 'About' in ob.name and 'overhead pool' in ob.name:ob.data.energy=250;ob.data.color=(.60,.75,.84)
 if 'Minecraft | warm torch' in ob.name:ob.data.energy=22
S.world.node_tree.nodes.get('Background').inputs['Color'].default_value=(.06,.08,.11,1);S.world.node_tree.nodes.get('Background').inputs['Strength'].default_value=.17
lights=bpy.data.collections.new('05 | LIGHTING • localized pools');S.collection.children.link(lights)
def light(name,pos,target,energy,color,angle=40,blend=.5,radius=.35,kind='SPOT',size=5):
 d=bpy.data.lights.new(name,kind);d.energy=energy;d.color=color
 if name.startswith(('Depth','Shaft','Grazing','Fill')):d.specular_factor=0;d.diffuse_factor=1
 if name.startswith('Depth'):d.volume_factor=.65
 if name.startswith('Shaft'):d.volume_factor=.4
 if kind=='SPOT':d.spot_size=math.radians(angle);d.spot_blend=blend;d.shadow_soft_size=radius
 if kind=='AREA':d.shape='DISK';d.size=size
 o=bpy.data.objects.new(name,d);lights.objects.link(o);o.location=pos;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();return o
light('Pool | Projects primary',(-1.5,5,19),(-.4,5.9,7.65),12500,(.67,.78,.88),52,.92,radius=1.25)
light('Pool | Education',(-15,-1,14),(-14,-3,6.4),4600,(.60,.74,.84),60,.92,radius=1.0)
light('Pool | Contact',(-14,9,23),(-12.4,11,12.5),3900,(.59,.74,.84),48,.9,radius=1.1)
light('Pool | About', (14,-2,16),(12.4,-3,7.8),2300,(.53,.70,.82),56,.9,radius=1.1)
light('Bounce | Projects screens',(0,7.2,9.5),(0,5.3,7.6),90,(.06,.40,.70),kind='AREA',size=3)
light('Bounce | About display',(13.7,-1.8,9.8),(13.7,-1.8,7.7),65,(.05,.35,.60),kind='AREA',size=4)
light('Practical | Work amber',(-17,-6.5,7.8),(-16,-6.5,4.9),90,(1,.38,.12),55,.8)
light('Shaft | mid cavern',(-4,18,23),(-2,17,7),550,(.38,.56,.76),42,.95)
light('Shaft | distant stone',(4,29,16),(-1,24,8),1400,(.34,.51,.70),56,.95)
light('Depth | distant blue scatter',(0,37,18),(0,20,11),4300,(.25,.43,.61),kind='AREA',size=11)

light('Grazing | left limestone',(-13,-7,18),(-21,2,14),4800,(.40,.53,.64),35,.8)
light('Grazing | right limestone',(14,-5,18),(21,3,14),3400,(.34,.47,.59),32,.8)
light('Fill | low diffuse camera bounce',(0,-15,15),(0,7,9),900,(.40,.49,.57),kind='AREA',size=20)

light('Depth | mid stone rim',(-5,15,15),(-1,19,9),1600,(.40,.54,.64),kind='AREA',size=6)
light('Depth | rear limestone reveal',(3,43,21),(-5,50,5),7000,(.32,.48,.62),kind='AREA',size=10)

light('Depth | inner right rock recess',(8,9,16),(9,19,10),1200,(.40,.53,.64),48,.7)

light('Reflection | hub brushed steel',(-4,12.5,12.5),(-1,4.5,7.7),120,(.53,.65,.76),kind='AREA',size=3.5)

light('Depth | left intermediate rim',(-7,10,13),(-10,19,12),650,(.30,.43,.54),35,.8)

light('Depth | lower left reflected fill',(-7,1,5),(-8,10,7),360,(.28,.40,.49),kind='AREA',size=5)
light('Depth | lower right reflected fill',(5,1,5),(10,9,7),230,(.26,.38,.48),kind='AREA',size=5)

light('Grazing | soft left rock bounce',(-14,-8,19),(-21,3,17),650,(.32,.45,.56),kind='AREA',size=12)
light('Grazing | soft right rock bounce',(15,-7,18),(22,4,16),450,(.30,.43,.54),kind='AREA',size=12)

# Low, local reflected light recovers circulation and fascia without exposing recesses.
light('Reflected | left circulation',(-7,-3,8),(-6,3,7),650,(.31,.46,.58),kind='AREA',size=7)
light('Reflected | contact landing',(-6,12,9),(-9,10,10),500,(.34,.47,.57),kind='AREA',size=6)
light('Reflected | right circulation',(7,-4,8),(9,2,7.8),500,(.30,.44,.55),kind='AREA',size=6)
light('Reflected | rear bridge',(0,14,11),(1,18,10),600,(.30,.44,.55),kind='AREA',size=7)
light('Reflected | hub fascia',(0,-3,5),(0,3,7),300,(.30,.43,.52),kind='AREA',size=6)
light('Reflected | experiences front',(-12,-9,6),(-13,-5,6),320,(.31,.43,.53),kind='AREA',size=7)
light('Practical | workshop warm bench',(14,14,14.7),(15,17,12.5),210,(1,.49,.22),kind='AREA',size=3)
light('Practical | workshop warm floor',(13,13,13.8),(14,13,11.5),70,(1,.51,.26),kind='AREA',size=3)

light('Depth | left water reflected scatter',(-8,-6,6),(-5,4,1),650,(.27,.39,.49),kind='AREA',size=8)
light('Depth | right water reflected scatter',(10,-1,7),(7,5,1.5),330,(.25,.37,.47),kind='AREA',size=9)
light('Depth | right lower contours',(5,8,7),(11,1,3),240,(.30,.43,.53),kind='AREA',size=7)

# Broad reflection sources sit at grazing angles to the visible water channels.
light('Reflection | water left channel',(-6,18,7),(-6,3,1),1600,(.28,.43,.57),kind='AREA',size=9)
light('Reflection | water right channel',(7,11,4.5),(7,3,1),700,(.25,.40,.55),kind='AREA',size=6)

# Neutral suspended mist takes color from illumination rather than emitting a blue wall.
atm=bpy.data.collections.get('04 | ATMOSPHERE • blue cavern depth')
for o in list(atm.objects):
 if o.type!='LIGHT':bpy.data.objects.remove(o,do_unlink=True)
def volume_box(name,center,size,density,emission=0):
 m=bpy.data.materials.new(name);nt=m.node_tree;nt.nodes.clear();out=nt.nodes.new('ShaderNodeOutputMaterial');v=nt.nodes.new('ShaderNodeVolumePrincipled');v.inputs['Density'].default_value=density;v.inputs['Color'].default_value=(.55,.64,.72,1);v.inputs['Anisotropy'].default_value=.28;v.inputs['Emission Strength'].default_value=emission;v.inputs['Emission Color'].default_value=(.028,.043,.060,1);nt.links.new(v.outputs['Volume'],out.inputs['Volume'])
 tc=nt.nodes.new('ShaderNodeTexCoord');cloud=noise_node(nt,tc.outputs['Object'],.13,3,.6);vary=mathnode(nt,'ADD',.6,mathnode(nt,'MULTIPLY',cloud.outputs['Fac'],.8));nt.links.new(mathnode(nt,'MULTIPLY',vary,density),v.inputs['Density'])
 x,y,z=[a/2 for a in size];verts=[(-x,-y,-z),(-x,-y,z),(-x,y,-z),(-x,y,z),(x,-y,-z),(x,-y,z),(x,y,-z),(x,y,z)];faces=[(0,4,6,2),(1,3,7,5),(0,1,5,4),(2,6,7,3),(0,2,3,1),(4,5,7,6)]
 me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.materials.append(m);o=bpy.data.objects.new(name,me);atm.objects.link(o);o.location=center
volume_box('ATMOSPHERE | rear density',(0,45,13),(70,44,44),.021,.0024)
volume_box('ATMOSPHERE | fine midground haze',(0,10,14),(44,32,32),.006)
volume_box('ATMOSPHERE | intermediate depth veil',(0,21,12),(37,5,31),.010,.0032)
# A rounded mist pocket has a naturally gradual optical thickness at its perimeter.
volume_box('ATMOSPHERE | central light mist',(-1,5.5,14.5),(8,6,14),.0025)
old=bpy.data.objects['ATMOSPHERE | central light mist'];material=old.data.materials[0]
bpy.data.objects.remove(old,do_unlink=True)
bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=12,location=(-1,5.5,14.5));mist=bpy.context.object;mist.name='ATMOSPHERE | rounded focal mist';mist.scale=(5,6,8)
for co in list(mist.users_collection):co.objects.unlink(mist)
atm.objects.link(mist);mist.data.materials.append(material)

# Sparse low mist links rock bases and water; the foreground remains clear.
for tag,pos,scale in [('left',(-5,5,1.8),(5.5,7,1.8)),('right',(6,7,1.6),(6,8,1.7))]:
 volume_box('ATMOSPHERE | low water '+tag,pos,(4,4,4),.010)
 old=bpy.data.objects['ATMOSPHERE | low water '+tag];material=old.data.materials[0];bpy.data.objects.remove(old,do_unlink=True)
 bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=12,location=pos);o=bpy.context.object;o.name='ATMOSPHERE | low drifting mist '+tag;o.scale=scale
 for co in list(o.users_collection):co.objects.unlink(o)
 atm.objects.link(o);o.data.materials.append(material)

# Geological grazing lights illuminate rock and suspended particles only.
# The islands retain their individually motivated pools and clear falloff.
receivers=bpy.data.collections.new('LIGHT LINK | geology and suspended particles')
for ob in list(S.objects):
 if ob.type=='MESH' and any(m and m.name.startswith(('GEOLOGY','ROCK','ATMOSPHERE','WATER')) for m in ob.data.materials):receivers.objects.link(ob)
for ob in lights.objects:
 if ob.type=='LIGHT' and ob.name.startswith(('Depth','Shaft','Grazing')):ob.light_linking.receiver_collection=receivers
metal_receivers=bpy.data.collections.new('LIGHT LINK | focal metal surfaces')
for ob in list(S.objects):
 if ob.type=='MESH' and any(c.name.startswith(('10 |','21 |')) for c in ob.users_collection):metal_receivers.objects.link(ob)
ob=S.objects['Reflection | hub brushed steel'];ob.light_linking.receiver_collection=metal_receivers;ob.data.diffuse_factor=.15


# Island practicals and reflected light illuminate solid surfaces. Suspended mist
# is illuminated by the separate dim, broad cavern sources, avoiding a theatrical beam.
solid_receivers=bpy.data.collections.new('LIGHT LINK | solid surface practicals')
for ob in list(S.objects):
 if ob.type=='MESH' and not any(m and m.name.startswith('ATMOSPHERE') for m in ob.data.materials):solid_receivers.objects.link(ob)
for ob in list(S.objects):
 if ob.type=='LIGHT' and ob.data.energy>0 and (ob.name.startswith(('Pool','Bounce','Reflected','Practical')) or 'Workshop' in ob.name or 'About' in ob.name):ob.light_linking.receiver_collection=solid_receivers

water_receivers=bpy.data.collections.new('LIGHT LINK | water reflections and low mist')
for ob in list(S.objects):
 if ob.type=='MESH' and any(m and m.name.startswith(('WATER','ATMOSPHERE')) for m in ob.data.materials):water_receivers.objects.link(ob)
for ob in lights.objects:
 if ob.name.startswith('Reflection | water'):ob.light_linking.receiver_collection=water_receivers

# Verification: all non-geology object transforms, section anchors and camera are unchanged.
bpy.context.view_layer.update()
assert camera_matrix==[list(r) for r in S.camera.matrix_world]
assert anchors==S['area_anchors_json']
assert all(name in S.objects and matrix==[list(r) for r in S.objects[name].matrix_world] for name,matrix in architecture.items())
S['atmosphere_revision']=opt.stage;S['atmosphere_scope']='Only geology, lighting, material response, accent hierarchy, water and atmospheric depth.'
S.render.resolution_x=opt.width;S.render.resolution_y=round(opt.width*927/1696);S.cycles.samples=opt.samples;S.cycles.use_denoising=True;S.view_settings.exposure=.6
S.render.filepath=os.path.join(OUT,'pass-%02d.png'%opt.stage)
ref=bpy.data.images.load(os.path.join(OUT,'target-atmosphere.png'),check_existing=True);ref.use_fake_user=True;ref.pack()
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT,'cavern-portfolio.blend'))
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT,'pass-%02d.blend'%opt.stage),copy=True)
report={'pass':opt.stage,'remodeled_geological_masses':len(geology),'fractured_shelves':ledge_count,'camera_unchanged':True,'architecture_transforms_unchanged':True,'anchors_unchanged':True,'active_lights':sum(o.type=='LIGHT' and o.data.energy>0 for o in S.objects),'objects':len(S.objects)}
json.dump(report,open(os.path.join(OUT,'pass-%02d.json'%opt.stage),'w'),indent=2)
print('SCOPED_QA',json.dumps(report),flush=True)
bpy.ops.render.render(write_still=True)
