"""Read the saved scene back and check preservation, clearance, and joints."""
import ast,hashlib,json,math,sys
from pathlib import Path
import bpy,bmesh,numpy as np
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent
FRAME=Matrix.Translation((21.299999237,0,0))@Matrix.Rotation(-math.atan2(12,19),4,'Z');INV=FRAME.inverted()
meta=json.loads((P/'upper-recess-preservation.json').read_text());allowed=set(meta['upper_rock_objects']);removed=set(meta['removed_upper_objects'])
src=ast.parse((P.parent/'central-metal-platform/build_metal_platform.py').read_text())
exec(compile(ast.Module(body=[n for n in src.body if isinstance(n,ast.FunctionDef) and n.name=='fingerprint'],type_ignores=[]),'fingerprint','exec'),globals())
bpy.ops.wm.open_mainfile(filepath=str(P/'preview-source.blend'));S=bpy.context.scene
protected={o.name:fingerprint(o) for o in S.objects if o.type=='MESH' and o.name not in allowed|removed}
points={}
for name in allowed:
    ob=S.objects[name];T=INV@ob.matrix_world
    points[name]=[T@ob.data.vertices[i].co for i in range(0,len(ob.data.vertices),max(1,len(ob.data.vertices)//6500)) if (T@ob.data.vertices[i].co).z<meta['rock_edit_min_z']-.001]
file=P/('preview-upper-recess.blend' if '--preview' in sys.argv else 'upper-recess.blend')
bpy.ops.wm.open_mainfile(filepath=str(file));S=bpy.context.scene
changed=[n for n,h in protected.items() if n not in S.objects or fingerprint(S.objects[n])!=h]
def tree_for(obs):
    vs=[];fs=[]
    for ob in obs:
        T=INV@ob.matrix_world;k=len(vs);vs.extend(T@v.co for v in ob.data.vertices);fs.extend(tuple(k+i for i in p.vertices) for p in ob.data.polygons)
    return BVHTree.FromPolygons(vs,fs)
errors=[];checked=0;rock_join_boundaries={}
for name,pts in points.items():
    tree=tree_for([S.objects[name]])
    bm=bmesh.new();bm.from_mesh(S.objects[name].data)
    rock_join_boundaries[name]=sum(e.is_boundary and all(abs(v.co.z-meta['rock_edit_min_z'])<.0001 for v in e.verts) for e in bm.edges)
    bm.free()
    for p in pts:
        checked+=1;hit=tree.find_nearest(p)
        if hit[3]>.0001:errors.append([name,list(p),hit[3]])
portal=S.objects[meta['arch_frame_single_connected_mesh']];bm=bmesh.new();bm.from_mesh(portal.data);unseen=set(bm.verts);parts=[]
while unseen:
    v=unseen.pop();todo=[v];n=0
    while todo:
        v=todo.pop();n+=1
        for e in v.link_edges:
            q=e.other_vert(v)
            if q in unseen:unseen.remove(q);todo.append(q)
    parts.append(n)
bad=sum(not e.is_manifold for e in bm.edges);bm.free()
origin=Vector(meta['upper_origin']);t=math.radians(meta['bay_angle_degrees']);u=Vector((math.cos(t),math.sin(t)));v=Vector((-u.y,u.x));H=meta['floor_z']
def at(x,y,z):return Vector((*(origin+u*x*meta['bay_x_scale']+v*y),z))
rocks=[o for o in bpy.data.collections['07 | Continuous approved-style cave wall'].objects if o.type=='MESH']
rocktree=tree_for(rocks+[S.objects['Metal | Upper | connected rock reveal and rear']])
obstructions=[]
for x in np.linspace(-2.36,2.36,13):
    for y in np.linspace(0,4.9,19):
        hit=rocktree.ray_cast(at(x,y,H+.03),Vector((0,0,1)),1.82)
        if hit[0] is not None:obstructions.append([float(x),float(y),hit[3]])
ptree=tree_for([portal]);joints=[]
for x in [-2.52,2.52]:
    for z in [H+.21,H+.45]:
        # Rail end sockets overlap the frame depth and frame cross-section.
        p=at(x,.61,z);h=ptree.ray_cast(p,Vector((*v,0)),.20);joints.append(h[3])
props=[o.name for o in bpy.data.collections['16 | Clean recessed upper balcony'].objects if any(s in o.name.lower() for s in ['tower','case','cabinet','gantry','aircraft','vehicle'])]
lights=[o.name for o in S.objects if o.type=='LIGHT' and o.name.startswith('Upper |')]
passed=not changed and not errors and parts==[24] and bad==0 and not obstructions and all(d is not None and d<.1 for d in joints) and not props and len(lights)==1
report={'passed':passed,'file':str(file),'unchanged_meshes_and_materials':len(protected),'unexpected_changes':changed,'lower_rock_samples_checked':checked,'lower_rock_errors':errors,'upper_rock_join_boundary_edges':rock_join_boundaries,'entrance_frame_components':parts,'entrance_frame_nonmanifold_edges':bad,'walkable_clearance_samples':13*19,'clearance_obstructions':obstructions,'rail_to_frame_distances':joints,'unwanted_upper_props':props,'upper_lights':lights,'sha256':hashlib.sha256(file.read_bytes()).hexdigest()}
(P/'verification.json').write_text(json.dumps(report,indent=2));print('UPPER_VERIFY',json.dumps(report),flush=True);assert passed
