# Detailed reusable equipment, executed before station transforms.
COL=bpy.data.collections['24 | WORKSHOP • workbench machinery & tools']
for x in [11.1,17.6]:
 beam('Workshop | overhead service rail',(x,12.8,17.28),(x,16.2,17.28),.065,steel,True)
for y in [13.3,14.8,16.0]:
 beam('Workshop | roof cross-member',(10,y,17.5),(18.7,y,17.5),.10,edge,True)
for x,y in [(12,13.7),(14.3,14.9),(16.4,13.7)]:
 box('Workshop | suspended light housing',(x,y,17.19),(1.15,.45,.13),steel)
 box('Workshop | suspended light diffuser',(x,y,17.115),(.97,.32,.027),white)
 for dx in [-.4,.4]:beam('Workshop | fixture suspension',(x+dx,y,17.2),(x+dx,y,17.55),.018,steel)
for j in range(5):
 for i in range(31):
  o=cyl('Workshop | pegboard perforation',(11.85+i*.175,16.073,14.5+j*.23),.013,.015,dark,6);o.rotation_euler.x=pi/2
for i in range(8):
 x=12.25+i*.45
 if i%3==0:
  # Pliers with divergent handles and jaws.
  for side in [-1,1]:
   beam('Workshop | pliers grip',(x,15.96,15.35),(x+side*.075,15.96,15.02),.029,orange if False else wood)
   beam('Workshop | pliers jaws',(x,15.96,15.35),(x+side*.035,15.96,15.49),.022,silver)
 elif i%3==1:
  for side in [-1,1]:beam('Workshop | open-ended spanner jaw',(x+side*.055,15.96,15.59),(x+side*.055,15.96,15.49),.022,silver)
 else:
  box('Workshop | hammer head',(x,15.95,15.58),(.21,.1,.08),silver,.013)
for i in range(6):
 x=15.1+i*.16
 o=cyl('Workshop | socket set',(x,15.96,14.45),.058,.14,silver,10);o.rotation_euler.x=pi/2
box('Workshop | socket rail',(15.5,16.01,14.44),(1.03,.055,.06),steel)
# Bench drill press with column, motor, chuck and handles.
x=11.65;y=15.05;z=13.8
box('Workshop | drill base',(x,y,z+.08),(.63,.51,.14),steel)
cyl('Workshop | drill column',(x,y+.11,z+.61),.064,1.03,silver,16)
box('Workshop | drill motor',(x,y,z+1.09),(.48,.44,.33),edge)
box('Workshop | drill table',(x,y-.15,z+.47),(.49,.46,.07),steel)
cyl('Workshop | drill chuck',(x,y-.14,z+.81),.085,.20,dark,16)
beam('Workshop | drill bit',(x,y-.14,z+.56),(x,y-.14,z+.75),.014,silver)
for a in [0,2*pi/3,4*pi/3]:
 beam('Workshop | drill feed handle',(x+.30,y,z+.93),(x+.30,y+.24*cos(a),z+.93+.24*sin(a)),.019,silver)
# Bench vise, metal toolbox and small loose parts.
box('Workshop | bench vise body',(15.85,14.92,13.97),(.46,.32,.25),steel)
for x in [15.65,16.07]:box('Workshop | bench vise jaw',(x,14.92,14.12),(.09,.41,.13),silver)
beam('Workshop | vise screw',(15.6,14.7,13.98),(16.1,14.7,13.98),.027,silver)
box('Workshop | portable toolbox',(13.35,15.07,13.99),(.56,.38,.36),steel)
path('Workshop | toolbox handle',[(13.20,15.07,14.18),(13.20,15.07,14.29),(13.48,15.07,14.29),(13.48,15.07,14.18)],.022,silver)
for x in [13.2,13.5]:box('Workshop | toolbox latch',(x,14.868,13.98),(.05,.027,.09),silver,.003)
for x in [16.55,17.12]:
 cyl('Workshop | compressed gas bottle',(x,16,13.07),.17,1.16,steel,16,r2=.15)
 cyl('Workshop | gas bottle shoulder',(x,16,13.71),.15,.16,steel,16,r2=.065)
 beam('Workshop | valve stem',(x,16,13.79),(x,16,13.97),.023,silver)
 path('Workshop | air hose',[(x,15.93,13.9),(x-.16,15.7,13.6),(x-.22,15.5,12.8),(x-.55,15.3,12.51),(x-.9,15.1,12.52)],.022,dark)

COL=bpy.data.collections['20 | CONTACT • antenna & operations']
for x,y,w,h in [(-15.6,12.2,.66,1.1),(-10.6,12.25,.68,1.6),(-9.7,12.25,.68,1.6),(-14.1,12.65,.58,.8)]:cabinet('Contact | communications rack',(x,y,10.77),w,h)
for x in [-10.6,-9.7]:
 for h in [11.2,11.5,11.8,12.1]:
  box('Contact | rack slot',(x,11.9,h),(.51,.032,.17),dark)
  for dx in [-.18,-.11]:box('Contact | rack activity LED',(x+dx,11.876,h),(.027,.008,.015),cyan,.001)
path('Contact | buried power loom',[(-13,11.5,10.8),(-13.3,12.2,10.8),(-11.8,12.5,10.8),(-10,12.3,10.8)],.045,dark)
for i in range(4):
 z=12.4+i*.43
 o=cyl('Antenna | microwave can',(-12.15,11.2,z),.115,.19,ivory,16);o.rotation_euler.y=pi/2
 o=cyl('Antenna | microwave cap',(-12.045,11.2,z),.092,.015,edge,16);o.rotation_euler.y=pi/2

COL=bpy.data.collections['13 | ABOUT ME • holographic laboratory']
for x in [9.15,17.2]:
 box('About | padded equipment crate',(x,1.92,7.3),(.66,.54,.66),wood)
 for dx in [-.23,.23]:box('About | crate corner armour',(x+dx,1.63,7.3),(.055,.04,.62),edge)
# Operator stool tucked beside the wall console.
x=15.7;y=2.0;z=7.03
cyl('About | stool column',(x,y,z+.42),.055,.65,silver,12)
cyl('About | padded seat',(x,y,z+.83),.30,.14,dark,24)
box('About | seat back',(x,y+.22,z+1.16),(.53,.09,.49),steel,.065)
beam('About | back support',(x,y+.20,z+.71),(x,y+.24,z+1.15),.027,silver)
for i in range(5):
 a=i*2*pi/5;beam('About | stool foot',(x,y,z+.12),(x+.32*cos(a),y+.32*sin(a),z+.06),.023,steel)
for x in [9.8,13.2,16.6]:
 box('About | horizontal wall strip',(x,4.10,10.22),(1.0,.045,.045),white,.005)
for y in [2.4,3.2]:
 path('About | rear overhead conduit',[(8.7,y,10.85),(10.3,y,11.05),(16.8,y,11.05),(18.1,y,10.4)],.045,steel)

COL=bpy.data.collections['21 | PROJECTS • panoramic workstation']
for x,y in [(-2.1,2.3),(0,2.65),(2.15,2.3)]:
 for dx in [-.34,0,.34]:
  box('Projects | console touchscreen',(x+dx,y-.20,8.232),(.27,.22,.023),screen,.01)
  box('Projects | console screen line',(x+dx,y-.20,8.248),(.20,.024,.007),cyan,.001)
for x in [-1.35,1.35]:
 box('Projects | console grille',(x,2.26,7.8),(.24,.04,.34),dark)
 for i in range(5):box('Projects | grille slit',(x,2.23,7.68+i*.055),(.21,.018,.014),edge,.002)

# Additional fascia plates, gussets and mechanical joints along the stations.
for coname,cx,cy,z,w in [('12 | CONTACT • elevated communications',-12.5,8.47,10.25,7.6),('14 | WORKSHOP • carved cave hangar',14.3,10.76,11.98,10.2)]:
 COL=bpy.data.collections[coname]
 for i in range(int(w)):
  x=cx-w/2+.5+i
  box('Structure | segmented fascia plate',(x,cy+.07,z),(.86,.055,.45),edge)
  for dx in [-.33,.33]:
   for zz in [-.14,.14]:bolt((x+dx,cy+.032,z+zz))
 for x in [cx-w*.35,cx+w*.35]:
  box('Structure | deep vertical bracket',(x,cy+.12,z-.2),(.27,.3,1.1),steel)

# Continuous curved Projects workstation with integrated low cabinets.
COL=bpy.data.collections['21 | PROJECTS • panoramic workstation']
pts=[];verts=[];N=32
for i in range(N+1):
 a=-pi/2+pi*i/N;x=3.23*sin(a);y=1.58+.58*cos(a);pts.append((x,y))
for dz in [7.94,8.13]:
 for dy in [0,.76]:
  verts.extend([(x,y+dy,dz) for x,y in pts])
faces=[]
for i in range(N):
 k=N+1
 faces.extend([(i,i+1,k+i+1,k+i),(2*k+i,3*k+i,3*k+i+1,2*k+i+1),(i,2*k+i,2*k+i+1,i+1),(k+i,k+i+1,3*k+i+1,3*k+i)])
faces.extend([(0,N+1,3*(N+1),2*(N+1)),(N,2*N+1,4*N+3,3*N+2)])
meshob('Projects | curved continuous worktop',verts,faces,edge)
path('Projects | continuous cyan worktop lip',[(x,y-.018,8.105) for x,y in pts],.024,cyan)
path('Projects | lower cabinet cyan trim',[(x,y+.03,7.47) for x,y in pts],.013,cyan)
for i in range(0,N,4):
 a=Vector((*pts[i],7.76));b=Vector((*pts[min(i+4,N)],7.76));v=b-a
 o=box('Projects | curved cabinet fascia',(a+b)/2,(v.length-.027,.13,.48),steel,.025);o.rotation_euler.z=math.atan2(v.y,v.x)
 for t in [.18,.82]:
  p=a.lerp(b,t);bolt((p.x,p.y-.08,p.z+.15))
for x in [-2.7,-1.4,1.4,2.7]:
 cyl('Projects | workstation foot',(x,2.3,7.63),.08,.47,steel,12)
# Replace right screen assembly with a two-tier wing.
for ob in list(COL.objects):
 if ob.name.startswith('Projects | holographic monitor') and ob.location.x>1.6:
  bpy.data.objects.remove(ob,do_unlink=True)
monitor('Projects | upper right wing',(2.48,2.30,9.62),1.5,.88,.38,3)
monitor('Projects | lower right wing',(2.48,2.30,8.68),1.5,.84,.38,4)

# Final material variation and localized atmosphere.
neutraldeck=material('PROJECTS | neutral slate steel',(.075,.081,.091),.42,.56)
for ob in bpy.data.collections['10 | PROJECTS • circular hub'].objects:
 if ob.name=='PROJECTS | floor':
  ob.data=ob.data.copy();ob.data.materials.clear();ob.data.materials.append(neutraldeck)
tilemats=[]
for i in range(4):
 m=deck.copy();m.name='DECK | maintenance panel finish %02d'%i
 p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Roughness'].default_value=[.46,.55,.65,.73][i]
 p.inputs['Base Color'].default_value=(.075+i*.005,.084+i*.005,.099+i*.005,1);tilemats.append(m)
tilecache={}
for ob in list(bpy.data.objects):
 if 'floor tile' in ob.name:
  idx=(int(abs(ob.location.x*3))+int(abs(ob.location.y*2)))%4;key=(ob.data.name,idx)
  if key not in tilecache:
   me=ob.data.copy();me.materials.clear();me.materials.append(tilemats[idx]);tilecache[key]=me
  ob.data=tilecache[key]
for mat in stonebg:
 p=mat.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(.062,.11,.18,1)
 p.inputs['Emission Color'].default_value=(.045,.092,.17,1);p.inputs['Emission Strength'].default_value=.38
for ob in bpy.data.collections['02 | CAVERN • distant depth layers'].objects:
 if ob.name.startswith('Distant') or ob.name.startswith('Depth'):
  for poly in ob.data.polygons:poly.use_smooth=True
COL=bpy.data.collections['00 | CAMERA & lighting']
area('Bounce | cool reflected water',(0,-4,3),(0,14,7),1600,(.20,.39,.65),18)
COL=bpy.data.collections['24 | WORKSHOP • workbench machinery & tools']
for i in range(4):
 x=12.3+i*.83
 path('Workshop | hanging coiled power line',[(x,15.78,17.25),(x,15.78,16.65),(x+.04,15.73,16.15),(x+.16,15.71,15.95),(x+.37,15.72,15.96),(x+.51,15.78,16.2),(x+.51,15.78,17.25)],.031,dark)
COL=bpy.data.collections['13 | ABOUT ME • holographic laboratory']
for x,y,z,w,h in [(8.9,3.05,7.04,.6,.65),(9.2,3.15,7.69,.48,.40),(17.5,2.65,7.04,.7,.8)]:
 cabinet('About | stacked service module',(x,y,z),w,h)
for x in [10.4,15.9]:
 box('About | ceiling light housing',(x,2.2,11.1),(1.0,.5,.13),steel)
 box('About | ceiling light diffuser',(x,2.2,11.023),(.81,.32,.035),white)

# Real alcove floors extend the terraces beneath rear equipment and wall corners.
COL=bpy.data.collections['23 | EXPERIENCES • gallery & cabinets']
box('Education | rear alcove subframe',(-13.7,.25,6.22),(9.6,2.9,.30),steel)
for i in range(8):
 for j in range(3):
  box('Education | rear alcove floor tile',(-17.9+i*1.2,-.72+j*.96,6.395),(1.175,.935,.1),deck,.015)
COL=bpy.data.collections['13 | ABOUT ME • holographic laboratory']
box('About | rear chamber subframe',(13.5,3.0,6.82),(10.4,3.0,.32),steel)
for i in range(8):
 for j in range(3):
  box('About | rear chamber floor tile',(8.95+i*1.3,2.0+j,7.005),(1.275,.975,.05),deck,.015)

# The circular display emits a bright center fading to a deeper cyan perimeter.
nt=blueglass.node_tree;p=nt.nodes.get('Principled BSDF');tc=nt.nodes.new('ShaderNodeTexCoord')
flatten=nt.nodes.new('ShaderNodeVectorMath');flatten.operation='MULTIPLY';flatten.inputs[1].default_value=(1,1,0);nt.links.new(tc.outputs['Generated'],flatten.inputs[0])
dist=nt.nodes.new('ShaderNodeVectorMath');dist.operation='DISTANCE';dist.inputs[1].default_value=(.5,.5,0);nt.links.new(flatten.outputs['Vector'],dist.inputs[0])
ramp=nt.nodes.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].position=0;ramp.color_ramp.elements[0].color=(.10,.70,1,1)
ramp.color_ramp.elements[1].position=.54;ramp.color_ramp.elements[1].color=(.003,.20,.48,1)
nt.links.new(dist.outputs['Value'],ramp.inputs['Fac']);nt.links.new(ramp.outputs['Color'],p.inputs['Emission Color']);p.inputs['Emission Strength'].default_value=1.35
for ob in bpy.data.collections['22 | ABOUT ME • circular holographic table'].objects:
 if ob.name.startswith('Hologram | cyan spill'):ob.data.energy=160
