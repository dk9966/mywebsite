# Additional depth, fractured scale hierarchy, and reference lighting balance.
from mathutils.bvhtree import BVHTree
# Distant cliff layers close the black opening; all are physical rocks.
for i in range(22):
 x=random.uniform(-9,9);y=random.uniform(-7,12)
 crag('Wired | distant cavern interior',(x,y,-29-random.uniform(0,5)),(random.uniform(2,4),random.uniform(3,6),2),2)
area('Wired | distant opening light',(0,6,-24),(0,6,-33),2500,6,(.13,.38,.7))
# Smaller angular sheets of geology sit on the macro-scale cliffs.
def rock_bvh():
 vs=[];fs=[]
 for o in col.objects:
  if o.type!='MESH' or not any(k in o.name for k in ['massive wall','ceiling fractured','foreground cliff','receding wall','service ledge']):continue
  st=len(vs);vs.extend([o.matrix_world@v.co for v in o.data.vertices]);fs.extend([tuple(st+i for i in f.vertices) for f in o.data.polygons])
 return BVHTree.FromPolygons(vs,fs)
bvh=rock_bvh()
for i in range(165):
 x=random.choice([-1,1])*random.uniform(10.7,16) if i<125 else random.uniform(-14,14)
 y=random.uniform(-10,10) if i<125 else random.uniform(7,11)
 hit,n,idx,dist=bvh.ray_cast(p(x,y,35),-D,80)
 if hit:
  v=hit-C;xyz=(v.dot(R),v.dot(U),v.dot(D)-.18)
  crag('Wired | fractured vertical rock blade',xyz,(random.uniform(.35,.9),random.uniform(.7,2.2),random.uniform(.25,.65)),1 if i%3 else 2)
# Make fissures follow actual nearest rock facets instead of floating cable paths.
for o in list(col.objects):
 if 'fissure dark cut' in o.name or 'hairline cyan fissure' in o.name:bpy.data.objects.remove(o,do_unlink=True)
bvh=rock_bvh()
for x,y,length in [(-12.7,10,5), (12.3,10,4.8),(-11.5,-1.7,4.8),(12.2,-3,5.2),(-4.9,10,3.7),(5.6,8.8,3.2),(-13.2,-7,3.8),(10.5,-7,3.6)]:
 route=[];xx=x
 for k in range(7):
  if k in [2,4]:xx+=random.choice([-1,1])*random.uniform(.25,.55)
  route.append((xx,y-k*length/6))
 pts=[]
 for a,b in zip(route,route[1:]):
  for k in range(6):
   t=k/6;hit,n,idx,dist=bvh.ray_cast(p(a[0]*(1-t)+b[0]*t,a[1]*(1-t)+b[1]*t,35),-D,80)
   if hit:pts.append(hit+D*.035)
 if len(pts)>2:
  line('Wired | surface cyan fracture',pts,.012,cyan)
# Restrained wall and foundation illumination; reduce volume scattering from large fills.
for o in col.objects:
 if o.type=='LIGHT':
  o.data.energy*=.34
  if hasattr(o.data,'volume_factor'):o.data.volume_factor=.15
  if hasattr(o.data,'specular_factor'):o.data.specular_factor=.15
for m in rocks:
 bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Specular IOR Level'].default_value=.18
# Preserve soft atmospheric blue at depth without concealing the supports.
for name in ['Cave | deep chasm mist','Cave | drifting mist over foundations']:
 o=bpy.data.objects[name]
 for m in o.data.materials:
  nt=m.node_tree
  for n in nt.nodes:
   if n.type=='PRINCIPLED_VOLUME':
    for socket,factor in [('Density',.6),('Emission Strength',.24)]:
     inp=n.inputs[socket]
     if inp.is_linked:
      source=inp.links[0].from_socket;mul=nt.nodes.new('ShaderNodeMath');mul.operation='MULTIPLY';mul.inputs[1].default_value=factor;nt.links.new(source,mul.inputs[0]);nt.links.new(mul.outputs[0],inp)
for o in bpy.data.objects:
 if o.type=='MESH' and ('floor' in o.name.lower() or 'rune' in o.name.lower()):
  if any(m and 'runeGlow' in m.name for m in o.data.materials):
   for i,m in enumerate(o.data.materials):
    if m and 'runeGlow' in m.name:o.data.materials[i]=mat('Wired subtle deck engraved rings',(.03,.065,.085),.5,.6,.13)
# Dim geometric markings, irrespective of original material name.
result={'floor_details':[(o.name,[m.name for m in o.data.materials]) for o in bpy.data.objects if o.type=='MESH' and 'floor' in o.name.lower()]}
