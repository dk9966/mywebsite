exec(compile(open('/Users/danielku/mywebsite/secret-base/refine_wired_depth.py').read().split('# Remove unsupported')[0],'helpers','exec'))
random.seed(2849)
cam.data.ortho_scale=36
cam.location=C-U*1.5+D*38
# Reveal the deep foreground and whole stone foundation of the nearest tower.
for o in col.objects:
 if o.type=='MESH' and 'grounded foreground rim' in o.name:
  for v in o.data.vertices:v.co-=U*2.5
# Replace stretched triangular strips with medium-size fractured basalt courses.
for o in list(col.objects):
 if any(k in o.name for k in ['buttress attached vertical shard','embedded buttress splinter','grounded fractured rubble']):bpy.data.objects.remove(o,do_unlink=True)
foundations=[]
for o in list(bpy.data.objects):
 if 'bedrock foundation island' not in o.name:continue
 pillar=bpy.data.objects[o.name.split('foundation ')[1]];cx,cy=pillar.matrix_world.translation.xy
 pv=[pillar.matrix_world@v.co for v in pillar.data.vertices];radius=max(math.hypot(v.x-cx,v.y-cy) for v in pv if v.z<.15)
 ns=25;vs=[];fs=[];az=[math.tau*k/ns+random.uniform(-.035,.035) for k in range(ns)];rr=[random.uniform(.89,1.14) for k in range(ns)]
 levels=[0,-.45];z=-.45
 while z>-18:z-=random.uniform(.7,1.2);levels.append(z)
 for j,z in enumerate(levels):
  mult=1.15 if j==0 else (1.17 if z>-.8 else 1.04+(-z)*.024)
  shift=random.uniform(-.045,.045)
  for k,a in enumerate(az):
   n=noise.noise(Vector((math.cos(a)*1.6,math.sin(a)*1.6,z*.38)))
   r=radius*mult*(rr[k]+n*.11+random.uniform(-.028,.028))
   dz=random.uniform(-.17,.17) if j>0 else random.uniform(-.025,0)
   vs.append(Vector((cx+math.cos(a+shift)*r+.16*math.sin(j*.6),cy+math.sin(a+shift)*r+.13*math.cos(j*.6),z+dz)))
 fs.append(tuple(range(ns)))
 for j in range(len(levels)-1):
  for k in range(ns):
   a=j*ns+k;b=j*ns+(k+1)%ns;c=a+ns;d=b+ns
   fs.extend([(a,c,d),(a,d,b)] if (k+j)%2 else [(a,c,b),(b,c,d)])
 me=bpy.data.meshes.new(o.name+' medium fractured basalt');me.from_pydata(vs,[],fs);me.update();o.data=me
 for m in rocks:me.materials.append(m)
 for f in me.polygons:f.material_index=random.choice([2,3,4,4,5]);f.use_smooth=False
 bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free();foundations.append(o)
# Physically embed multi-scale short, broken chunks in the surfaces.
from mathutils.bvhtree import BVHTree
for o in foundations:
 vs=[o.matrix_world@v.co for v in o.data.vertices];bvh=BVHTree.FromPolygons(vs,[list(f.vertices) for f in o.data.polygons]);coords=[v-C for v in vs];xmin=min(v.dot(R) for v in coords);xmax=max(v.dot(R) for v in coords);ymax=max(v.dot(U) for v in coords)
 for i in range(95):
  x=random.uniform(xmin,xmax);y=random.uniform(max(-13,ymax-8),ymax);hit,n,idx,dist=bvh.ray_cast(p(x,y,35),-D,90)
  if not hit:continue
  size=random.uniform(.18,.42) if i%10<7 else random.uniform(.4,.72);q=hit-C
  chunk=crag('Wired | embedded short basalt block',(q.dot(R),q.dot(U),q.dot(D)-size*.2),(size,size*random.uniform(.7,1.6),size*.7),1)
  recv=bpy.data.collections['Wired Foundation light receivers'];recv.objects.link(chunk)
# Visible distant spires rise in the newly exposed negative space.
for x,top,d,w in [(-10,-6.7,-9,.55),(-6.5,-8.5,-10,.6),(-1,-8.6,-12,.65),(3.7,-6.4,-10,.7),(7.8,-7.2,-9,.6),(10.1,-9,-10,.5)]:
 crag('Wired | distant chasm outcrop',(x,top-2.5,d),(w,2.8,w*1.2),2)
# Ledges and rubble in the revealed lower corners.
for x,y,d in [(-11,-11.6,1),(-6,-12.8,1),(3,-12.7,0),(10,-12,0)]:
 crag('Wired | lower broken bedrock ledge',(x,y,d),(2.2,.8,1.9),2)
 for i in range(23):
  r=random.uniform(.12,.4);crag('Wired | lower bedrock rubble',(x+random.uniform(-1.6,1.6),y+random.uniform(.25,.65),d+random.uniform(-1,1)),(r,r*.65,r),1)
# Reconnect fill receivers to rebuilt geometry and newly exposed foreground.
recv=bpy.data.collections['Wired Foundation light receivers']
for o in col.objects:
 if o.type=='MESH' and any(k in o.name for k in ['lower broken','lower bedrock','distant chasm outcrop']):
  if o.name not in recv.objects:recv.objects.link(o)
s.render.resolution_percentage=75;s.eevee.taa_render_samples=64
s.render.filepath='/Users/danielku/mywebsite/secret-base/wired-review/iteration-8.png'
bpy.ops.wm.save_as_mainfile(filepath='/Users/danielku/mywebsite/secret-base/base.blend')
