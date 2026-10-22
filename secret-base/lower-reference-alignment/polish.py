exec(compile(open('/Users/danielku/mywebsite/secret-base/lower-reference-alignment/helpers.py').read(),'helpers.py','exec'))
from mathutils.geometry import intersect_point_tri_2d
import bmesh
# Subdivide the gently folded wall faces into actual recessed panel tiles.
patch=[]
for i in range(4):
 ob=bpy.data.objects['Lower | fitted recessed bay %02d'%i]
 a,b,c,d=[ob.matrix_world@v.co for v in list(ob.data.vertices)[:4]]
 norm=(b-a).cross(d-a).normalized()
 if norm.dot(CAM.location-(a+b+c+d)/4)<0:norm=-norm
 patch.append(([a,b,c,d],norm))
 def point(u,v):return a.lerp(b,u).lerp(d.lerp(c,u),v)
 # The bay's full face is one smooth, internally subdivided surface.
 verts=[tuple(point(x/8,y/8)) for y in range(9) for x in range(9)]
 faces=[(y*9+x,y*9+x+1,(y+1)*9+x+1,(y+1)*9+x) for y in range(8) for x in range(8)]
 ob.hide_render=True;ob.hide_set(True)
 mesh('Lower | fitted bay backing %02d'%i,verts,faces,trim)
 for ix in range(2):
  for iy in range(4):
   u0=ix/2+.006;u1=(ix+1)/2-.006;v0=iy/4+.006;v1=(iy+1)/4-.006
   vs=[tuple(point(u0+(u1-u0)*x/4,v0+(v1-v0)*y/4)+norm*.016) for y in range(5) for x in range(5)]
   fs=[(y*5+x,y*5+x+1,(y+1)*5+x+1,(y+1)*5+x) for y in range(4) for x in range(4)]
   mesh('Lower | fitted recessed metal panel',vs,fs,wall)
# Remove the obsolete seam beams that were embedded in the old nonplanar quad.
for o in list(ARCH.objects):
 if any(t in o.name for t in ['panel reveal']):o.hide_render=True;o.hide_set(True)
# Recess the existing rock only where it intrudes into the newly fitted room.
terrain=bpy.data.objects['150 | continuous cave with oblique carved rooms']
if 'reference_fit_source_mesh' not in terrain:
 terrain.data.use_fake_user=True;terrain['reference_fit_source_mesh']=terrain.data.name;terrain.data=terrain.data.copy()
# Preserve that same continuous cliff, adding local resolution for its cut edge.
bm=bmesh.new();bm.from_mesh(terrain.data)
world=terrain.matrix_world;invworld=world.inverted()
def in_room(p):
 q=uv(p)
 return 1228<q.x<1684 and 385<q.y<585
edges=[e for e in bm.edges if all(in_room(world@v.co) for v in e.verts)]
if edges:bmesh.ops.subdivide_edges(bm,edges=edges,cuts=2,use_grid_fill=True)
bm.to_mesh(terrain.data);bm.free()
changed=0
for v in terrain.data.vertices:
 w=world@v.co
 if not in_room(w):continue
 orig,dr=ray(uv(w));hit=None
 for (a,b,c,d),norm in patch:
  for tri in [(a,b,c),(a,c,d)]:
   pt=intersect_ray_tri(*tri,dr,orig,True)
   if pt is not None and (hit is None or (pt-orig).length<(hit-orig).length):hit=pt
 if hit is not None and (w-orig).dot(dr)<(hit-orig).dot(dr)+.2:
  v.co=invworld@(hit+dr*.24);changed+=1
terrain.data.update()
# Practical hood light provides the broad pool seen over the circular pad.
ld=bpy.data.lights.new('Lower | fitted overhead pool','AREA');ld.energy=100;ld.color=(.65,.82,1);ld.shape='DISK';ld.size=1.4
lo=bpy.data.objects.new('Lower | fitted overhead pool',ld);ARCH.objects.link(lo);lo.location=at_z((1440,442),F+1.7);aim=at_z((1418,598),F);lo.rotation_euler=(aim-lo.location).to_track_quat('-Z','Y').to_euler();mw=lo.matrix_world.copy();lo.parent=lower;lo.matrix_world=mw
# Delicate highlights keep the architecture legible without turning it bright gray.
ld=bpy.data.lights.new('Lower | fitted broad soft fill','AREA');ld.energy=45;ld.color=(.56,.71,.85);ld.shape='DISK';ld.size=3.0
lo=bpy.data.objects.new('Lower | fitted broad soft fill',ld);ARCH.objects.link(lo);lo.location=at_z((1360,670),F+1.0);aim=at_z((1430,512),F+.7);lo.rotation_euler=(aim-lo.location).to_track_quat('-Z','Y').to_euler();mw=lo.matrix_world.copy();lo.parent=lower;lo.matrix_world=mw
bpy.context.view_layer.update()
S.camera.data.background_images[0].alpha=.5
bpy.ops.wm.save_as_mainfile(filepath=str(P/'pass-03.blend'),copy=True,compress=True)
result={'terrain_vertices_recessed':changed,'saved_checkpoint':str(P/'pass-03.blend')}
