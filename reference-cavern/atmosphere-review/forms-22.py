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
 relief=.38*noise_vector(Vector((q.x*.55,q.y*.55,q.z*1.05))).x+.11*sin(bed*7+noise(q*.5)*3)
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
