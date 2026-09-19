"""Continuous eroded hanging masses and bent cliff ridges; architecture stays fixed.
Remesh only intersecting geological surfaces, with finite mesh budgets and metric UVs.
"""
from mathutils import Matrix

def mapped_stone(ob):
 me=ob.data;me.materials.clear();me.materials.append(rockmat)
 for old_uv in list(me.uv_layers):me.uv_layers.remove(old_uv)
 me.polygons.foreach_set('material_index',np.zeros(len(me.polygons),dtype=np.int32))
 me.update()
 uv=me.uv_layers.new(name='Geology UV • metric')
 for f in me.polygons:
  axis=max(range(3),key=lambda k:abs(f.normal[k]));ax=(0,1) if axis==2 else (0,2) if axis==1 else (1,2)
  for li in f.loop_indices:
   v=me.vertices[me.loops[li].vertex_index].co;uv.data[li].uv=(v[ax[0]]/3.5,(v[ax[1]]+.16*v.x)/3.5)
  f.use_smooth=True
 me.set_sharp_from_angle(angle=math.radians(50))

for tooth_index in [2,3,4,5]:
 stem=S.objects['Ceiling | hanging tooth %02d'%tooth_index];me=stem.data;N=len(me.polygons[-1].vertices)
 source=[stem.matrix_world@v.co for v in me.vertices]
 sections=[]
 for j in range(len(source)//N):
  vs=source[j*N:(j+1)*N];c=sum(vs,Vector())/N
  sections.append((c.z,c,max(abs(v.x-c.x) for v in vs),max(abs(v.y-c.y) for v in vs)))
 sections.sort(key=lambda a:a[0]);heights=np.array([r[0] for r in sections])
 def section(z):
  j=max(0,min(len(sections)-2,int(np.searchsorted(heights,z))-1));a,b=sections[j:j+2];t=max(0,min(1,(z-a[0])/max(.001,b[0]-a[0])))
  return a[1].lerp(b[1],t),a[2]*(1-t)+b[2]*t,a[3]*(1-t)+b[3]*t
 # Conform scanned fractures to the taper of their parent, embedding all boundaries.
 chunks=[o for o in S.objects if o.name.startswith('Geology | hanging fractured bed %02d.'%tooth_index)]
 for ob in chunks:
  old=ob.data;ob.data=old.copy();M=ob.matrix_world.copy();width=max(abs(v.co.x) for v in old.vertices);height=max(v.co.z for v in old.vertices)
  for v in ob.data.vertices:
   q=M@v.co;center,rx,ry=section(q.z);u=v.co.x/width;edge=sin(pi*max(0,min(1,v.co.z/height)))
   q.x=center.x+u*rx*1.02
   q.y=center.y-ry*math.sqrt(max(.05,1-(u*.96)**2))+v.co.y*.30-.30*edge+.20*(1-edge)
   v.co=q
  ob.matrix_world=Matrix.Identity(4)
 # Join and voxel-union overlapping pieces into a single geological volume.
 bpy.ops.object.select_all(action='DESELECT');stem.select_set(True)
 for ob in chunks:ob.select_set(True)
 bpy.context.view_layer.objects.active=stem;bpy.ops.object.join()
 M=stem.matrix_world.copy();stem.data.transform(M);stem.matrix_world=Matrix.Identity(4)
 z0=min(v.co.z for v in stem.data.vertices);z1=max(v.co.z for v in stem.data.vertices)
 for v in stem.data.vertices:
  t=(v.co.z-z0)/(z1-z0);w=sin(pi*t)
  v.co.x+=w*(.72*sin(t*5.0+tooth_index*1.6)+.23*sin(t*11.0+tooth_index))
  v.co.y+=w*.58*sin(t*4.8+tooth_index*2.1)
 stem.data.remesh_voxel_size=.11;stem.data.remesh_voxel_adaptivity=0
 bpy.ops.object.voxel_remesh()
 smooth=stem.modifiers.new('Erosion across connected fracture boundaries','SMOOTH');smooth.factor=.45;smooth.iterations=3;bpy.ops.object.modifier_apply(modifier=smooth.name)
 dec=stem.modifiers.new('Finite rock surface budget','DECIMATE');dec.ratio=.44;bpy.ops.object.modifier_apply(modifier=dec.name)
 mapped_stone(stem);stem['geology_revision']='Continuous voxel-unioned bedrock with bent spine, embedded fractures, and eroded junctions.'
 print('Connected hanging mass',stem.name,len(stem.data.polygons),'faces',flush=True)

# Break vertical alignment without displacing the architectural attachment elevations.
for ob in list(S.objects):
 if ob.type!='MESH' or not (ob.name.startswith('Cavern | massive fluted wall') or ob.name.startswith('Chasm | solitary spire')):continue
 phase=(sum(ord(c) for c in ob.name)%53)*.17;M=ob.matrix_world;inv=M.inverted();coords=[M@v.co for v in ob.data.vertices];zmin=min(q.z for q in coords);zmax=max(q.z for q in coords)
 for v,q in zip(ob.data.vertices,coords):
  t=(q.z-zmin)/max(1,zmax-zmin);envelope=sin(pi*t)
  amplitude=.85 if 'wall' in ob.name else .55
  dx=amplitude*envelope*(sin(t*7+phase)+.28*sin(t*13+phase));dy=.7*envelope*sin(t*5.5+phase)
  # Keep the wall attachments near occupied terraces stable.
  if 'wall' in ob.name:
   safe=1-.70*math.exp(-((q.z-10)/4)**2);dx*=safe;dy*=safe
  v.co=inv@(q+Vector((dx,dy,0)))
 ob.data.update();ob['geology_macro_shape']='Bent and uneven ridge with stable attachment zone.'
print('Connected geological forms complete',flush=True)

# Connected bedrock shoulders join the individual support outcrops below each island.
# Platform stanchions, fascia and walking surfaces remain untouched.
def foundation_name(i):return 'Foundation | basalt buttress'+('' if i==0 else '.%03d'%i)
for tag,indices,center,size in [
 ('Projects',[0,1,2,3],(0,5.3,.6),(7.0,7.7,6.8)),
 ('About',[16,17,18,19],(14.8,-.4,.65),(11.8,8.1,6.9)),
 ('Contact',[12,13,14,15],(-12.8,11.0,2.55),(8.1,7.2,10.5)),
]:
 group=[S.objects[foundation_name(i)] for i in indices];template=group[0]
 verts=[template.matrix_world@v.co for v in template.data.vertices];lo=Vector(tuple(min(v[k] for v in verts) for k in range(3)));hi=Vector(tuple(max(v[k] for v in verts) for k in range(3)));mid=(lo+hi)/2
 me=template.data.copy();core=bpy.data.objects.new('Geology | '+tag+' connected bedrock shoulder',me);co=bpy.data.collections['01 | CAVERN • structural geology'];co.objects.link(core)
 for v,q in zip(me.vertices,verts):
  p=Vector(tuple((q[k]-mid[k])/(hi[k]-lo[k])*size[k] for k in range(3)))
  t=(p.z+size[2]/2)/size[2];p.x*=1+.85*t;p.y*=1+.65*t;p.x+=.8*sin(t*5+.8);p.y+=.6*sin(t*7+1.3);v.co=p+Vector(center)
 bpy.ops.object.select_all(action='DESELECT');core.select_set(True)
 for o in group:o.select_set(True)
 bpy.context.view_layer.objects.active=core;bpy.ops.object.join();core.data.remesh_voxel_size=.14;core.data.remesh_voxel_adaptivity=0;bpy.ops.object.voxel_remesh()
 sm=core.modifiers.new('Eroded connected shoulder junctions','SMOOTH');sm.factor=.36;sm.iterations=3;bpy.ops.object.modifier_apply(modifier=sm.name)
 dec=core.modifiers.new('Finite connected bedrock budget','DECIMATE');dec.ratio=.38;bpy.ops.object.modifier_apply(modifier=dec.name);mapped_stone(core)
 core['component']='Connected irregular bedrock under unchanged island supports.'
 print('Connected island foundation',tag,len(core.data.polygons),'faces',flush=True)

# A continuous branching ceiling shoulder makes the roots of the pendants readable.
# The arch stays above the routes and within the existing cave enclosure.
arch_sections=[(-10,24.2,15,3,2.8),(-7,24.7,13.5,3,2),(-4.8,25,12.6,2.5,1.5),(-1.8,24.2,14.2,3.2,1.7),(1.4,24,13.2,3,1.7),(3.5,25.1,13.3,2.5,1.3),(6.2,25.3,16.4,2.5,2.5)]
verts=[];faces=[];N=14
for j,(x,y,z,ry,rz) in enumerate(arch_sections):
 for i in range(N):
  a=i*2*pi/N;shape=1+.10*sin(a*3+j*.7)+.07*sin(a*5+1.2)
  verts.append((x+.18*sin(a*2+j),y+ry*cos(a)*shape,z+rz*sin(a)*shape))
for j in range(len(arch_sections)-1):
 for i in range(N):a=j*N+i;b=j*N+(i+1)%N;faces.append((a,b,b+N,a+N))
faces.extend([tuple(reversed(range(N))),tuple(range((len(arch_sections)-1)*N,len(arch_sections)*N))])
me=bpy.data.meshes.new('Geology | branching crown union');me.from_pydata(verts,[],faces);o=bpy.data.objects.new('Geology | connected cavern crown',me);bpy.data.collections['01 | CAVERN • structural geology'].objects.link(o)
bpy.ops.object.select_all(action='DESELECT');o.select_set(True)
for i in [2,3,4,5]:S.objects['Ceiling | hanging tooth %02d'%i].select_set(True)
bpy.context.view_layer.objects.active=o;bpy.ops.object.join();o.data.remesh_voxel_size=.15;o.data.remesh_voxel_adaptivity=0;bpy.ops.object.voxel_remesh()
sm=o.modifiers.new('Erosion through arch roots','SMOOTH');sm.factor=.42;sm.iterations=3;bpy.ops.object.modifier_apply(modifier=sm.name)
dec=o.modifiers.new('Crown surface budget','DECIMATE');dec.ratio=.48;bpy.ops.object.modifier_apply(modifier=dec.name);mapped_stone(o)
# Erosion cuts across the broad crown planes at geological scales.
o.data.update();crown_normals=[v.normal.copy() for v in o.data.vertices]
for v,normal in zip(o.data.vertices,crown_normals):
 q=v.co.copy();bed=q.z+.22*q.x+.11*q.y
 relief=.38*noise_vector(Vector((q.x*.55,q.y*.55,q.z*1.05))).x+.035*sin(bed*7+noise(q*.5)*3)+.26*noise_vector(q*.26).z
 v.co+=normal*relief
o.data.update();mapped_stone(o)
print('Connected branching cavern crown',len(o.data.polygons),'faces',flush=True)

# Large sedimentary faces break the remaining cylindrical support silhouettes.
# Each closed volume overlaps the connected core and stays below the fixed decks.
shared=bpy.data.meshes.get('Geology | scanned sediment face • shared 20K')
for tag,pos,scale,rz in [('Projects',(0,.8,-1.7),(1.8,1.25,2.1),.06),('About',(14.5,-4.1,-1.6),(2.2,1.15,2.1),-.24),('Contact',(-12.7,7.1,-1.3),(1.65,1.15,2.4),.09)]:
 o=bpy.data.objects.new('Geology | stratified island face '+tag,shared);bpy.data.collections['01 | CAVERN • structural geology'].objects.link(o);o.location=pos;o.scale=scale;o.rotation_euler.z=rz;o['component']='Instanced closed sedimentary rock volume embedded in connected island bedrock.'
# The roots converge obliquely into the larger bedrock shoulders.
for o in list(S.objects):
 if o.type!='MESH' or 'connected bedrock shoulder' not in o.name:continue
 vs=[v.co.copy() for v in o.data.vertices];lo=min(v.z for v in vs);hi=max(v.z for v in vs);cx=sum(v.x for v in vs)/len(vs);cy=sum(v.y for v in vs)/len(vs)
 for v,q in zip(o.data.vertices,vs):
  t=max(0,min(1,(hi-q.z)/(hi-lo)));w=.22*sin(t*pi*.78)
  v.co.x+=(cx-q.x)*w;v.co.y+=(cy-q.y)*w*.8
 o.data.update()

# Ensure newly placed scanned faces have evaluated transforms before world-space erosion.
bpy.context.view_layer.update()

# Offset shoulders and undercuts break the planar outline while keeping upper anchors covered.
for ob in list(S.objects):
 if not ob.name.startswith('Geology | stratified island face'):continue
 ob.data=ob.data.copy();M=ob.matrix_world.copy();center=ob.location.x
 for v in ob.data.vertices:
  q=M@v.co;z=q.z
  taper=1-.13*math.exp(-((z-2.0)/1.3)**2)
  q.x=center+(q.x-center)*taper+.30*sin(z*1.2+.7)
  q.y+=.32*sin(z*1.4+.8)+.10*sin(q.x*.65+z)
  v.co=q
 ob.matrix_world=Matrix.Identity(4);ob.data.update()

# Oblique bedrock transitions connect the islands' roots behind existing routes.
# Their upper surfaces remain below the bridges and do not create new walkways.
for tag,sections in [
 ('left root',[(-3.6,7.5,2.4,2.0,1.3),(-5.4,9.2,1.8,2.2,1.15),(-7.2,11.2,2.8,2.5,1.4),(-10.0,12.8,3.6,2.7,1.6)]),
 ('right root',[(3.5,7.7,2.0,2.1,1.25),(5.5,8.0,1.3,1.9,1.05),(7.7,6.6,1.7,2.1,1.2),(10.1,4.5,2.6,2.4,1.5)])
]:
 verts=[];faces=[];N=16
 for j,(x,y,z,ry,rz) in enumerate(sections):
  for i in range(N):
   a=i*2*pi/N;profile=1+.14*sin(a*3+.5)+.075*sin(a*5+j*.5)
   verts.append((x+.18*sin(a*2+j),y+ry*cos(a)*profile,z+rz*sin(a)*profile))
 for j in range(len(sections)-1):
  for i in range(N):a=j*N+i;b=j*N+(i+1)%N;faces.append((a,b,b+N,a+N))
 faces.extend([tuple(reversed(range(N))),tuple(range((len(sections)-1)*N,len(sections)*N))])
 me=bpy.data.meshes.new('Geology | oblique '+tag);me.from_pydata(verts,[],faces);bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free();o=bpy.data.objects.new('Geology | connected oblique '+tag,me);bpy.data.collections['01 | CAVERN • structural geology'].objects.link(o)
 bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o;o.data.remesh_voxel_size=.15;bpy.ops.object.voxel_remesh()
 normals=[v.normal.copy() for v in o.data.vertices]
 for v,n in zip(o.data.vertices,normals):
  q=v.co;v.co+=n*(.22*noise_vector(Vector((q.x*.6,q.y*.6,q.z*1.8))).x+.06*sin((q.z+.18*q.x)*10))
 dec=o.modifiers.new('Oblique ridge surface budget','DECIMATE');dec.ratio=.42;bpy.ops.object.modifier_apply(modifier=dec.name);mapped_stone(o)
 o['component']='Closed oblique bedrock transition overlapping neighboring island roots below the bridges.'

# Unite adjoining bedrock into continuous geological volumes. Architecture is excluded.
# Existing terraces still occupy the same air pockets; only intersecting rock is fused.
bpy.context.view_layer.update()
groups=[
 ('left cavern wall',[o for o in S.objects if o.name in ['Cavern | massive fluted wall %02d'%i for i in range(4)]+['Ceiling | hanging tooth 00','Ceiling | hanging tooth 01'] or o.name.startswith(('Geology | scanned fractured Left','Geology | scanned fractured Inner left'))]),
 ('right cavern wall',[o for o in S.objects if o.name in ['Cavern | massive fluted wall %02d'%i for i in range(4,8)]+['Ceiling | hanging tooth 06','Ceiling | hanging tooth 07','Ceiling | hanging tooth 08'] or o.name.startswith('Geology | scanned fractured Right')]),
 ('island bedrock network',[o for o in S.objects if 'connected bedrock shoulder' in o.name or o.name.startswith(('Geology | stratified island face','Geology | connected oblique'))]),
]
for tag,group in groups:
 bpy.ops.object.select_all(action='DESELECT')
 for ob in group:ob.select_set(True)
 ob=group[0];bpy.context.view_layer.objects.active=ob;bpy.ops.object.join()
 ob.data.transform(ob.matrix_world);ob.matrix_world=Matrix.Identity(4);ob.name='Geology | unified '+tag
 bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(ob.data);bm.free()
 ob.data.remesh_voxel_size=.18 if 'wall' in tag else .14;ob.data.remesh_voxel_adaptivity=0;bpy.ops.object.voxel_remesh()
 sm=ob.modifiers.new('Eroded geological junctions','SMOOTH');sm.factor=.48;sm.iterations=5;bpy.ops.object.modifier_apply(modifier=sm.name)
 normals=[v.normal.copy() for v in ob.data.vertices]
 for v,n in zip(ob.data.vertices,normals):
  q=v.co.copy();coarse=noise_vector(Vector((q.x*.27,q.y*.25,q.z*.31))).x
  bed=.38*q.x+.23*q.y+.73*q.z+1.1*noise(q*.13)
  fracture=abs(sin(bed))**8
  v.co+=n*(.48*coarse-.20*fracture)
 dec=ob.modifiers.new('Unified geology finite mesh budget','DECIMATE');dec.ratio=.43;bpy.ops.object.modifier_apply(modifier=dec.name)
 mapped_stone(ob)
 # A shared oblique bedding direction crosses object junctions and avoids ring-like bands.
 uv=ob.data.uv_layers.active
 for f in ob.data.polygons:
  axis=max(range(3),key=lambda k:abs(f.normal[k]));ax=(0,1) if axis==2 else (0,2) if axis==1 else (1,2)
  for li in f.loop_indices:
   q=ob.data.vertices[ob.data.loops[li].vertex_index].co;u=q[ax[0]];vv=q[ax[1]]
   uv.data[li].uv=((.92*u+.39*vv)/4.6,(-.39*u+.92*vv)/4.6)
 ob['component']='Continuous geological volume with oblique fracture planes and eroded intersections.'
 print('Unified connected bedrock',tag,len(ob.data.polygons),'faces',flush=True)

# Broad fracture planes are fitted to coherent surface patches, not individual triangles.
# This preserves connected volumes while breaking the melted/rounded appearance.
from mathutils.kdtree import KDTree
for ob in list(S.objects):
 if not (ob.name.startswith('Geology | unified') or ob.name=='Geology | connected cavern crown'):continue
 me=ob.data;vs=[v.co.copy() for v in me.vertices];ns=[v.normal.copy() for v in me.vertices];cells={};spacing=2.2
 for q,n in zip(vs,ns):
  key=tuple(math.floor((q[k]+[.7,1.1,.3][k])/spacing) for k in range(3))
  # Opposing surfaces in a narrow formation must not share a fracture plane.
  key=key+(max(range(3),key=lambda k:abs(n[k])),1 if sum(n)>0 else -1)
  if key not in cells:cells[key]=[Vector(),Vector(),0]
  cells[key][0]+=q;cells[key][1]+=n;cells[key][2]+=1
 planes=[(q/count,n.normalized()) for q,n,count in cells.values() if n.length>.1 and count>3]
 tree=KDTree(len(planes))
 for i,(q,n) in enumerate(planes):tree.insert(q,i)
 tree.balance()
 for v,q,n in zip(me.vertices,vs,ns):
  candidates=tree.find_n(q,4);chosen=next(((center,idx,d) for center,idx,d in candidates if planes[idx][1].dot(n)>.65),None)
  if chosen:
   center,idx,d=chosen;pn=planes[idx][1];dist=(q-center).dot(pn)
   v.co-=pn*max(-.35,min(.35,dist))*.25
  fold=(.5+.5*sin(.44*q.x+.24*q.y+.72*q.z+.4*noise(q*.15)))**5
  v.co-=n*fold*(.45+.35*noise(q*.22))
 me.update();me.set_sharp_from_angle(angle=math.radians(32))
 print('Authored broad fracture planes',ob.name,len(planes),flush=True)


# Recessed rear wall encloses the distant water chamber. This is actual 3D bedrock,
# with deep broad folds, rather than an unbroken blue background opening.
verts=[];faces=[];nx,nz=35,24
for back in [False,True]:
 for j in range(nz+1):
  z=-7+j*1.8
  for i in range(nx+1):
   x=-35+i*2.0;y=46+2.7*sin(x*.19+z*.12)+1.4*cos(z*.39+x*.08)+.35*noise(Vector((x*.8,0,z*.7)))
   verts.append((x,y+(7 if back else 0),z))
stride=nx+1;layer=stride*(nz+1)
for j in range(nz):
 for i in range(nx):
  a=j*stride+i;b=a+1;faces.append((a,a+stride,b+stride,b));faces.append((a+layer,b+layer,b+stride+layer,a+stride+layer))
for j in range(nz):
 for i in [0,nx]:a=j*stride+i;faces.append((a,a+layer,a+stride+layer,a+stride))
for j in [0,nz]:
 for i in range(nx):a=j*stride+i;faces.append((a,a+1,a+1+layer,a+layer))
me=bpy.data.meshes.new('Geology | remote recessed chamber');me.from_pydata(verts,[],faces);bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
o=bpy.data.objects.new('Geology | remote cavern wall',me);next(c for c in bpy.data.collections if c.name.startswith('02 |')).objects.link(o)
mapped_stone(o)
o['component']='Closed distant cavern wall with broad irregular folds behind the original islands.'
