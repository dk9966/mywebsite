exec(compile(open('/Users/danielku/mywebsite/secret-base/refine_wired_depth.py').read().split('# Remove unsupported')[0],'helpers','exec'))
random.seed(7319)
# Replace cylindrical root meshes with coherent jagged buttresses with widening talus feet.
for o in list(bpy.data.objects):
 if 'bedrock foundation island' not in o.name:continue
 pillar=bpy.data.objects[o.name.split('foundation ')[1]];cx,cy=pillar.matrix_world.translation.xy
 pv=[pillar.matrix_world@v.co for v in pillar.data.vertices];radius=max(math.hypot(v.x-cx,v.y-cy) for v in pv if v.z<.15)
 ns=19;vs=[];fs=[]
 az=[math.tau*k/ns+random.uniform(-.035,.035) for k in range(ns)];rr=[random.uniform(.84,1.2) for k in range(ns)]
 for j,(z,mult) in enumerate([(0,1.16),(-.5,1.25),(-1.7,1.11),(-3.4,1.1),(-5.6,1.22),(-8.5,1.52),(-12,1.8),(-17,2.0)]):
  for k,a in enumerate(az):
   r=radius*mult*rr[k]*(random.uniform(.94,1.07) if j>0 else 1);dz=random.uniform(-.45,.25) if j else random.uniform(-.04,.0)
   vs.append(Vector((cx+math.cos(a)*r+.22*math.sin(j),cy+math.sin(a)*r+.24*math.cos(j*.8),z+dz)))
 fs.append(tuple(reversed(range(ns))))
 for j in range(7):
  for k in range(ns):
   a=j*ns+k;b=j*ns+(k+1)%ns;c=a+ns;d=b+ns
   fs.extend([(a,b,c),(b,d,c)])
 me=bpy.data.meshes.new(o.name+' fractured buttress');me.from_pydata(vs,[],fs);me.update();o.data=me
 for m in rocks:me.materials.append(m)
 for f in me.polygons:f.material_index=random.choice([2,3,4,4,5]);f.use_smooth=False
 # Embedded long fractures and broken shoulders, rooted within the same supporting massif.
 for k in range(11):
  a=math.tau*k/11+random.uniform(-.13,.13);r=radius*random.uniform(1.0,1.14);z=random.uniform(-3.7,-1.3)
  w=Vector((cx+math.cos(a)*r,cy+math.sin(a)*r,z));v=w-C
  crag('Wired | buttress attached vertical shard',(v.dot(R),v.dot(U),v.dot(D)),(random.uniform(.45,.85),random.uniform(1.1,2),random.uniform(.5,.9)),1)
 # Rough broken cap rocks just outside metal foundation rings.
 for k in range(24):
  a=math.tau*k/24;r=radius*random.uniform(1.04,1.22);w=Vector((cx+math.cos(a)*r,cy+math.sin(a)*r,random.uniform(-.4,-.1)));v=w-C;sz=random.uniform(.16,.38)
  crag('Wired | footing cap rubble',(v.dot(R),v.dot(U),v.dot(D)),(sz,sz*.65,sz),1)
# Conceal obsolete floating surface relief that belonged to the old pedestals.
o=bpy.data.objects.get('Cave | retained foundation relief')
if o:o.hide_render=True;o.hide_set(True)
# New far vertical cliff folds are divided into meaningful medium-scale fractures.
for o in list(col.objects):
 if 'distant cavern interior' in o.name:bpy.data.objects.remove(o,do_unlink=True)
for layer,depth in enumerate([-36,-29,-23]):
 for i in range(9):
  x=-10+i*2.4+random.uniform(-.8,.8);y=random.uniform(3.8,7)
  if layer==2 and -2<x<2:continue
  crag('Wired | far vertical cavern fold',(x,y,depth),(random.uniform(1.5,2.5),random.uniform(4,7),random.uniform(1.4,2.8)),3)
# Sparse foreground needles rise out of deep interconnected rock beds.
for i,(x,top,d) in enumerate([(-10,-7.1,0),(-7.4,-8.4,-1),(-3.2,-9,-3),(.4,-8,-2),(3.8,-7.8,-1),(7,-6.9,-2),(10,-8.9,1),(-1.9,-6.9,-8),(5.1,-6,-9)]):
 crag('Wired | visible abyss pinnacle',(x,top-3,d),(random.uniform(.4,.8),3.4,random.uniform(.5,.9)),2)
# Scattered grounded broken boulders over dim ridges at abyss bottom.
for x,y,d in [(-8,-10,-1),(1,-10.5,-2),(6,-9.5,-2),(-2,-12,1)]:
 crag('Wired | chasm rubble ridge',(x,y,d),(2.2,1.1,1.6),2)
 for j in range(18):
  xx=x+random.uniform(-1.4,1.4);yy=y+random.uniform(-.1,.75);dd=d+random.uniform(-.7,.7);r=random.uniform(.12,.38)
  crag('Wired | ridge talus fragment',(xx,yy,dd),(r,r*.7,r),1)
# Additional light picks out silhouettes in gaps without bluewashing near rock.
for xyz,target,power in [((1,-7,2),(2,-9,-3),210),((7,-5,1),(7,-9,-3),170),((-9,-5,2),(-9,-8,-3),140)]:
 o=area('Wired | lower chasm grazing',xyz,target,power,3.5,(.14,.45,.68));o.data.volume_factor=.2;o.data.specular_factor=.1
# Right door remains, left door becomes a smaller, different narrow armored service terminal.
for o in col.objects:
 if o.type!='MESH' or not any(k in o.name for k in ['service recess','inset door','recessed jamb','segmented conduit','ventilation slot','status aperture','central door seam','door edge','threshold']):continue
 v=o.location-C;x=v.dot(R)
 if -13.1<x<-10.7 and -2<v.dot(U)<3.5:
  anchor=p(-11.8,1.15,-.8);delta=o.location-anchor;o.location=anchor+R*(delta.dot(R)*.62)+U*(delta.dot(U)*.74+.8)+D*delta.dot(D);o.scale.x*=.62;o.scale.y*=.74
# Small practical warm lamps are more prominent in the reference.
for o in bpy.data.objects:
 if o.type=='MESH' and any(k in o.name.lower() for k in ['lantern']) and any(k in o.name.lower() for k in ['glass','glow','bulb','flame','core']):o.scale*=1.35
 if o.type=='LIGHT' and 'lantern' in o.name.lower():o.data.energy*=1.8
# Match local cyan light spill to actual attached crack positions.
for o in list(col.objects):
 if o.type=='CURVE' and 'surface cyan fracture' in o.name:
  pts=o.data.splines[0].points
  for k in [len(pts)//3,2*len(pts)//3]:
   pt=Vector(pts[k].co[:3])+D*.3;data=bpy.data.lights.new('Wired | recessed fissure bounce','POINT');data.energy=7;data.color=(.08,.55,1);data.shadow_soft_size=.5;data.specular_factor=0;data.volume_factor=.1;light=bpy.data.objects.new(data.name,data);col.objects.link(light);light.location=pt
s.render.filepath='/Users/danielku/mywebsite/secret-base/wired-review/iteration-4.png'
bpy.ops.wm.save_as_mainfile(filepath='/Users/danielku/mywebsite/secret-base/base.blend')
