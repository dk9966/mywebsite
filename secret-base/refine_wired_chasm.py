exec(compile(open('/Users/danielku/mywebsite/secret-base/refine_wired_depth.py').read().split('# Remove unsupported')[0],'helpers','exec'))
random.seed(8294)
# Remove flat isolated boulder shelves from abyss; geology should grow from a continuous bed.
for o in list(col.objects):
 if any(k in o.name for k in ['lower broken bedrock ledge','lower bedrock rubble','chasm rubble ridge','ridge talus fragment','grounded foreground rim','lower cavern rim']):bpy.data.objects.remove(o,do_unlink=True)
# Undulating real horizontal cave bed well beneath all four bases, with broken stones attached.
vs=[];fs=[];nx=66;ny=62
for j in range(ny):
 for i in range(nx):
  x=-2+i*.7+random.uniform(-.2,.2);y=-21+j*.7+random.uniform(-.2,.2);z=-13.9+noise.noise(Vector((x*.26,y*.26,2)))*1.8+random.uniform(-.25,.25)
  vs.append(Vector((x,y,z)))
for j in range(ny-1):
 for i in range(nx-1):
  a=j*nx+i;fs.extend([(a,a+1,a+nx),(a+1,a+nx+1,a+nx)])
o=mesh('Wired | deep fractured cavern bed',vs,fs)
recv=bpy.data.collections['Wired Foundation light receivers'];recv.objects.link(o)
for i in range(600):
 w=random.choice(vs);q=w-C;r=random.uniform(.12,.5)
 o=crag('Wired | cavebed angular rubble',(q.dot(R),q.dot(U)+r*.2,q.dot(D)),(r,r*.6,r),1 if i%4 else 2);recv.objects.link(o)
# Broken foreground sill, with rough irregular silhouettes rather than broad flat disks.
for i in range(16):
 x=-18+i*2.4;y=-14+random.uniform(-1,.3)
 o=crag('Wired | broken near rock sill',(x,y,6),(random.uniform(1.2,2.1),random.uniform(1.3,2),1.8),2);recv.objects.link(o)
# Mist and glacial lights below the bases, illuminating channels through the rubble.
for xyz,target,power in [((-10,-10,-3),(-10,-13,-7),300),((1,-11,-4),(1,-13,-8),400),((9,-10,-4),(9,-13,-8),300)]:
 o=area('Wired | cavern bed blue bounce',xyz,target,power,5,(.08,.42,.76));o.data.volume_factor=.35;o.data.specular_factor=.1
# Restore balanced neutral metal modeling light independently of geological receivers.
for o in col.objects:
 if o.type=='LIGHT' and 'station gray grazing' in o.name:o.data.energy=650
 if o.type=='LIGHT' and 'foundation face grazing' in o.name:o.data.energy=1700
# Medium fractured facets inside the high opening, avoiding giant smooth slabs.
for o in col.objects:
 if o.type!='MESH' or not any(k in o.name for k in ['broken opening ridge','far vertical cavern fold']):continue
 bm=bmesh.new();bm.from_mesh(o.data);original=set(bm.verts);bmesh.ops.subdivide_edges(bm,edges=list(bm.edges),cuts=1,use_grid_fill=True);bm.normal_update()
 for v in bm.verts:
  if v not in original:v.co+=v.normal*random.uniform(-.24,.24)
 bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free()
# One narrow rear opening is less strongly lit than nearby cliff walls.
for o in col.objects:
 if o.type=='LIGHT' and any(k in o.name for k in ['distant opening light','depth layer soft bounce']):o.data.energy*=.65
s.render.filepath='/Users/danielku/mywebsite/secret-base/wired-review/iteration-9.png'
bpy.ops.wm.save_as_mainfile(filepath='/Users/danielku/mywebsite/secret-base/base.blend')
