exec(compile(open('/Users/danielku/mywebsite/secret-base/refine_wired_depth.py').read().split('# Remove unsupported')[0],'helpers','exec'))
random.seed(8914)
# The rock pedestals terminate in an actual lower cavern bed instead of infinitely long shafts.
for o in bpy.data.objects:
 if o.type=='MESH' and 'bedrock foundation island' in o.name:
  for v in o.data.vertices:v.co.z*=.5
  o.data.update()
for o in col.objects:
 if o.type=='MESH' and any(k in o.name for k in ['embedded short basalt block','footing cap rubble']):
  for v in o.data.vertices:
   if v.co.z<0:v.co.z*=.5
  o.data.update()
for o in list(col.objects):
 if any(k in o.name for k in ['rooted chasm crag','visible abyss pinnacle','distant chasm outcrop']):bpy.data.objects.remove(o,do_unlink=True)
# Raise the deep irregular bed enough to reveal broken surfaces across the lower frame.
for o in col.objects:
 if o.type=='MESH' and any(k in o.name for k in ['deep fractured cavern bed','cavebed angular rubble']):
  for v in o.data.vertices:v.co.z+=4.8
  o.data.update()
# Natural, staggered short rock needles rooted in that bed.
recv=bpy.data.collections['Wired Foundation light receivers']
for i in range(32):
 x=random.uniform(-13,13);y=random.uniform(-7,-10);d=random.uniform(-12,-2);top=p(x,y,d);height=random.uniform(1.2,3.2);cz=-9+height*.5
 vs=[];fs=[];N=random.choice([7,8,9]);radius=random.uniform(.25,.7)
 for j,(zz,mult) in enumerate([(-9.4,1.3),(cz,1),(-9+height,.14)]):
  for k in range(N):
   a=k*math.tau/N;r=radius*mult*random.uniform(.8,1.2);vs.append((top.x+math.cos(a)*r+j*.07,top.y+math.sin(a)*r,zz+random.uniform(-.12,.12)))
 for j in range(2):
  for k in range(N):
   a=j*N+k;b=j*N+(k+1)%N;c=a+N;dd=b+N;fs.extend([(a,b,c),(b,dd,c)])
 fs.append(tuple(2*N+k for k in range(N)));o=mesh('Wired | grounded broken stalagmite',vs,fs);recv.objects.link(o)
# Blue mist lingers close to the rocky bed, revealing its silhouette through channels.
old=bpy.data.objects['Wired | low curling chasm mist'];o=bpy.data.objects.new('Wired | blue mist along cave bed',old.data.copy());col.objects.link(o);o.location=(21,0,-8.5);o.rotation_euler=(0,0,0);o.scale=(38,32,3.4)
# Existing material has soft 3D-noise density and emission falloff.
for pos in [(13,2,-7),(23,2,-7),(31,0,-7),(18,-7,-7)]:
 data=bpy.data.lights.new('Wired | cold chasm floor bounce','POINT');data.energy=45;data.color=(.08,.38,.7);data.shadow_soft_size=2;data.specular_factor=0;data.volume_factor=.6;light=bpy.data.objects.new(data.name,data);col.objects.link(light);light.location=pos
s.render.filepath='/Users/danielku/mywebsite/secret-base/wired-review/iteration-10.png'
bpy.ops.wm.save_as_mainfile(filepath='/Users/danielku/mywebsite/secret-base/base.blend')
