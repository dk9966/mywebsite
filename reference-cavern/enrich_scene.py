# Executed in the builder's namespace, before station transforms.
# Atmosphere is a bounded 3D volume, independent of the comparison camera.
collection('04 | ATMOSPHERE • blue cavern depth')
fog=bpy.data.materials.new('ATMOSPHERE | blue suspended haze');fog.use_nodes=True
nt=fog.node_tree;nt.nodes.clear();out=nt.nodes.new('ShaderNodeOutputMaterial');vol=nt.nodes.new('ShaderNodeVolumePrincipled')
vol.inputs['Density'].default_value=.052;vol.inputs['Color'].default_value=(.30,.49,.7,1);vol.inputs['Anisotropy'].default_value=.18
vol.inputs['Emission Color'].default_value=(.025,.11,.25,1);vol.inputs['Emission Strength'].default_value=.025
nt.links.new(vol.outputs['Volume'],out.inputs['Volume']);box('Atmosphere | rear blue haze',(0,44,12),(72,45,48),fog,0)
area('Cavern depth | blue shaft',(0,35,19),(0,15,7),4500,(.17,.4,.8),16)
# Move far rock masses behind the blue volume; preserve a distinct middle spire.
co=bpy.data.collections['02 | CAVERN • distant depth layers']
for ob in co.objects:
 if ob.name.startswith('Distant cavern ridge'):
  ob.location.y+=5
  for mat in ob.data.materials:
   p=mat.node_tree.nodes.get('Principled BSDF');p.inputs['Emission Color'].default_value=(.035,.10,.20,1);p.inputs['Emission Strength'].default_value=.35
 if ob.name.startswith('Chasm | solitary spire 02'):ob.location.x-=4
 if ob.name.startswith('Chasm | solitary spire 01'):ob.location.x+=5
# Basalt portal overhangs: broken rock covers the broad manufactured roof edges.
COL=bpy.data.collections['14 | WORKSHOP • carved cave hangar']
for i in range(14):
 x=8.7+i*.8
 rock('Workshop | carved roof crown %02d'%i,(x,14.5,18.1),.80,2.0,-random.uniform(.45,1.1),2200+i,.52,5,10)
COL=bpy.data.collections['13 | ABOUT ME • holographic laboratory']
for i in range(12):
 x=8.4+i*.9
 rock('About | broken lintel crown %02d'%i,(x,2.7,12.0),.85,2.1,-random.uniform(.45,.85),2250+i,.8,5,10)
# Chipped ledges and diagonal ribs interrupt the repetitive vertical wall rhythm.
COL=bpy.data.collections['01 | CAVERN • structural geology']
for side in [-1,1]:
 for i in range(22):
  x=side*random.uniform(19.5,22.5);y=random.uniform(8,24);z=random.uniform(3,22)
  rock('Cavern | embedded angular outcrop',(x,y,z),random.uniform(.5,1.0),random.uniform(.7,1.5),random.uniform(1,2.7),2300+i+(50 if side>0 else 0),.45,6,11)

# Layered architecture is confined to the appropriate station collections.
COL=bpy.data.collections['10 | PROJECTS • circular hub']
for i in range(32):
 a=i*2*pi/32;rr=5.38;x=rr*cos(a);y=rr*sin(a)
 o=box('Projects | skirt armor panel',(x,y,6.74),(.88,.11,.54),deck,.025);o.rotation_euler.z=a-pi/2
 for off in [-.32,.32]:
  xx=x+off*cos(a-pi/2);yy=y+off*sin(a-pi/2)
  ob=cyl('Projects | armor bolt',(xx,yy,6.91),.041,.045,silver,6);ob.rotation_euler=(pi/2,0,a-pi/2)
for i in range(12):
 a=i*2*pi/12;rr=4.62
 ob=box('Projects | inset service hatch',(rr*cos(a),rr*sin(a),7.365),(.47,.32,.025),edge,.025);ob.rotation_euler.z=a
 for off in [-.10,0,.10]:
  ob=box('Projects | hatch vent',(rr*cos(a)+off*cos(a),rr*sin(a)+off*sin(a),7.382),(.035,.21,.015),dark,.003);ob.rotation_euler.z=a

COL=bpy.data.collections['23 | EXPERIENCES • gallery & cabinets']
for x in [-17.7,-14.8,-11.8,-8.6]:
 for y,z in [(-9.38,4.47),(-4.72,5.96)]:
  box('Experiences | fascia splice',(x,y,z),(.21,.16,.67),edge)
  for zz in [z-.22,z+.22]:bolt((x,y-.095,zz))
for x in [-16.5,-14.7,-12.9,-11.1]:
 box('Education | inlaid yellow deck stripe',(x,-3.8,6.45),(1.1,.028,.012),yellow,.001)
 box('Work | inlaid yellow deck stripe',(x,-7.9,4.94),(1.1,.028,.012),yellow,.001)
for x in [-17,-15.5,-14]:
 box('Education | overhead warm strip',(x,1.05,9.2),(.85,.12,.05),orange,.01)
 area('Education | ceiling warm pool',(x,.8,9.0),(x,-.2,6.4),95,(1,.4,.15),1.5)
for i in range(5):
 x=-16+i*1.65;text('Work | date tag',str(2018+i*2),(x,-6.46,5.7),.11,white)

COL=bpy.data.collections['13 | ABOUT ME • holographic laboratory']
# Wall-mounted consoles and a seated operations station fill the side alcoves.
for x in [9.6,16.5]:
 console((x,2.7,7.0),1.4);monitor('About | diagnostic monitor',(x,2.9,8.52),1.2,.75,0,2)
for x in [10.9,15.0]:
 cabinet('About | drawer rack',(x,3.3,7.0),.8,1.25)
 for h in [7.22,7.52,7.82]:box('About | drawer handle',(x,2.96,h),(.37,.035,.025),silver,.003)
for i in range(6):
 x=9.5+i*1.45
 box('About | rear wall inner rib',(x,4.2,9.1),(.075,.15,3.7),edge)
for x in [9.8,13.2,16.5]:
 box('About | overhead strip luminaire',(x,3.4,11.02),(.9,.15,.065),white,.01)
for x in [11.4,15.8]:
 box('About | floor access hatch',(x,-3.6,7.01),(.65,.72,.028),steel)
 for dx in [-.22,.22]:box('About | hatch latch',(x+dx,-3.6,7.035),(.07,.22,.018),silver,.008)
# Shade glossy holographic glass so the large blue surface retains color.
for ob in bpy.data.collections['22 | ABOUT ME • circular holographic table'].objects:
 if ob.name.startswith('Hologram | cyan spill'):ob.data.energy=90

COL=bpy.data.collections['24 | WORKSHOP • workbench machinery & tools']
area('Workshop | warm broad room fill',(14,13,16.7),(14,15.4,13.8),180,(1,.49,.22),4)
for x in [11.4,12.8,14.2,15.6,17.0]:
 box('Workshop | upper wall storage',(x,16.1,16.65),(1.2,.5,.42),edge)
 box('Workshop | upper cabinet handle',(x,15.83,16.65),(.23,.045,.04),silver)
for i in range(9):
 x=11.2+i*.64
 cyl('Workshop | oil bottle',(x,15.62,13.99),.073,.38,wood if i%2 else steel,10)
 cyl('Workshop | bottle cap',(x,15.62,14.2),.052,.055,silver,10)
for x in [11.7,16.3]:
 box('Workshop | open equipment tray',(x,14.9,13.85),(.55,.38,.10),dark)
 for i in range(4):beam('Workshop | loose hand tool',(x-.18+i*.09,14.8,13.94),(x-.18+i*.09,15.03,13.94),.025,silver)
for i in range(10):
 x=10.3+(i%2)*.53;z=13.6+(i//2)*.50
 box('Workshop | labeled parts drawer',(x,14.0,z),(.44,.08,.26),steel)
 box('Workshop | parts label',(x,13.95,z),(.14,.012,.07),ivory,.002)
for x in [10.4,17.8]:
 path('Workshop | dangling power cable',[(x,15.95,16.2),(x,15.95,15.55),(x+.15,15.9,15.12),(x+.55,15.95,15.0),(x+.7,15.95,15.2),(x+.7,15.95,16.2)],.023,dark)

COL=bpy.data.collections['25 | MINECRAFT • hidden block shrine']
# Broken stepped stone sides help the shrine read as a miniature ruin in the cave.
for side in [-1,1]:
 for j in range(6):
  for k in range(3-j//2):
   box('Minecraft | stepped ruin blocks',(6.45+side*(2.15+k*.56),20.25,9.83+j*.56),(.55,.62,.54),stone[(j+k*2)%len(stone)],.025)

COL=bpy.data.collections['02 | CAVERN • distant depth layers']
for i,(x,y,z,rx,hh) in enumerate([(-7,31,-9,3.6,17),(-3.4,33,-12,3.5,20),(3.4,34,-12,3.8,23),(7,31,-10,2.9,17)]):
 rock('Depth | jagged middle ridge',(x,y,z),rx,2.5,hh,3000+i,.025,22,20,stonebg)
# Hero mast has additional ceramic segmentation, feed lines and bolted equipment.
COL=bpy.data.collections['20 | CONTACT • antenna & operations']
for x in [-12.95,-12.35]:
 for z in [11.7,12.3,12.9,13.5]:
  box('Antenna | equipment module',(x,10.83,z),(.22,.15,.31),ivory,.015)
  box('Antenna | module inset',(x,10.745,z),(.11,.015,.2),edge,.006)
for x in [-13.18,-12.17]:
 path('Antenna | external feed cable',[(x,11.4,11.1),(x,11.4,13.0),(x+.08,11.4,13.4),(x+.08,11.4,15.1)],.025,dark)
area('Contact | dish rim light',(-15,8,16),(-15,11,13.7),250,(.65,.78,1),2)
# Floor lamps cast localized amber pools.
COL=bpy.data.collections['26 | SECONDARY • service details']
for x,y,z in [(-16,-8,5.5),(-9,-4,6.9),(9,-5,7.6),(17,-4,7.6),(-10,9,11.3)]:
 point('Deck | localized amber pool',(x,y,z),60,(1,.30,.07),.35)

# Saturated self-lit holographic surface; black substrate prevents broad white reflections.
p=blueglass.node_tree.nodes.get('Principled BSDF')
p.inputs['Base Color'].default_value=(.001,.003,.006,1)
p.inputs['Roughness'].default_value=1;p.inputs['Metallic'].default_value=0
p.inputs['Specular IOR Level'].default_value=0
p.inputs['Emission Color'].default_value=(.004,.28,.70,1);p.inputs['Emission Strength'].default_value=.8
# The workshop tool board is dark stained perforated steel rather than a bright panel.
boardmat=material('WORKSHOP | dark bronze pegboard',(.075,.040,.017),.30,.63)
for ob in bpy.data.collections['24 | WORKSHOP • workbench machinery & tools'].objects:
 if ob.name.startswith('Workshop | rear tool board'):ob.data.materials.clear();ob.data.materials.append(boardmat)
 if ob.name.startswith('Workshop | warm task wash'):ob.data.energy=100
 if ob.name.startswith('Workshop | solid worktop'):ob.data=ob.data.copy();ob.data.materials.clear();ob.data.materials.append(edge)

exec(compile(open(os.path.join(ROOT,'detail_pass.py')).read(),'detail_pass.py','exec'))
