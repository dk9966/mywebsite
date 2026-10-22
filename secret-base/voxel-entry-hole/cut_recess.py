"""Open the user's sculpted rear indentation at its natural depth contour."""
import bpy, bmesh, json, hashlib, array
from pathlib import Path

P=Path('/Users/danielku/mywebsite/secret-base/voxel-entry-hole')
wall=bpy.data.objects['150 | continuous cave with oblique carved rooms']
if bpy.context.mode!='OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
assert not wall.modifiers

def signature(obj):
    h=hashlib.sha256(repr([list(r) for r in obj.matrix_world]).encode())
    h.update(repr((obj.hide_render,obj.hide_viewport,obj.hide_get())).encode())
    if obj.type=='MESH':
        coords=array.array('f',[0.0])*(len(obj.data.vertices)*3)
        obj.data.vertices.foreach_get('co',coords)
        h.update(coords.tobytes())
        loops=array.array('i',[0])*len(obj.data.loops)
        obj.data.loops.foreach_get('vertex_index',loops)
        h.update(loops.tobytes())
    return h.hexdigest()

protected={o.name:signature(o) for o in bpy.context.scene.objects if o!=wall}
original=bpy.data.meshes.get(wall.get("voxel_opening_original_mesh", "")) or wall.data
original.use_fake_user=True
original_name=original.name
new=original.copy()
new.name='Cave | sculpted rear recess with voxel opening'
bm=bmesh.new();bm.from_mesh(new)
before={'vertices':len(bm.verts),'faces':len(bm.faces),'boundary_edges':sum(e.is_boundary for e in bm.edges),'nonmanifold_edges':sum(len(e.link_faces)>2 for e in bm.edges)}
# The rear bowl is the only part extending past 14.2 in the cave's local Y.
# Its surrounding surfaces become the organic reveal; no synthetic arch is added.
removed=[v for v in bm.verts if v.co.y>14.2]
assert removed and all(-4<v.co.x<4.5 and 9<v.co.z<14 for v in removed)
bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-6,plane_co=(0,14.2,0),plane_no=(0,1,0),clear_outer=True,clear_inner=False)
ngons=[f for f in bm.faces if len(f.verts)>3 and any(abs(v.co.y-14.2)<1e-4 for v in f.verts)]
if ngons:bmesh.ops.triangulate(bm,faces=ngons,quad_method='BEAUTY',ngon_method='BEAUTY')
boundary=[e for e in bm.edges if e.is_boundary and all(abs(v.co.y-14.2)<1e-4 for v in e.verts)]
verts=set(v for e in boundary for v in e.verts)
assert len(verts)>8 and all(sum(v in e.verts for e in boundary)==2 for v in verts)
remaining=set(verts);loops=[]
while remaining:
    seed=remaining.pop();todo=[seed];component={seed}
    while todo:
        v=todo.pop()
        for e in v.link_edges:
            if e not in boundary:continue
            other=e.other_vert(v)
            if other in remaining:remaining.remove(other);component.add(other);todo.append(other)
    loops.append(len(component))
assert len(loops)==1,loops
opening_bounds=[[min(v.co[i] for v in verts),max(v.co[i] for v in verts)] for i in range(3)]
after={'vertices':len(bm.verts),'faces':len(bm.faces),'boundary_edges':sum(e.is_boundary for e in bm.edges),'nonmanifold_edges':sum(len(e.link_faces)>2 for e in bm.edges),'opening_boundary_loop_vertices':loops,'opening_bounds_local':opening_bounds}
assert after['nonmanifold_edges']==before['nonmanifold_edges']
bm.to_mesh(new);bm.free();new.update()
wall.data=new
wall['voxel_opening']='Rear sculpt indentation opened at local Y=14.2; surrounding authored slope and terrain preserved.'
wall['voxel_opening_original_mesh']=original_name
wall['voxel_opening_backup']=str(P/'before-hole-live-sculpt.blend')
assert all(signature(bpy.data.objects[n])==h for n,h in protected.items())
report={'before':before,'after':after,'protected_objects_unchanged':len(protected),'original_mesh_preserved':original_name,'saved_scene':bpy.data.filepath}
(P/'verification.json').write_text(json.dumps(report,indent=2))
result=report
