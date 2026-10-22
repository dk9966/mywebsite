"""Check exact original-scene preservation and the open surface extension."""
import argparse,ast,hashlib,json,math,sys
from pathlib import Path
import bpy,bmesh,numpy as np
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent
ap=argparse.ArgumentParser();ap.add_argument('--file',default='connected-cavern.blend');args=ap.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
src=ast.parse((P.parent/'central-metal-platform/build_metal_platform.py').read_text())
exec(compile(ast.Module(body=[n for n in src.body if isinstance(n,ast.FunctionDef) and n.name=='fingerprint'],type_ignores=[]),'fingerprint','exec'),globals())
F=Matrix.Translation((21.299999237,0,0))@Matrix.Rotation(-math.atan2(12,19),4,'Z');I=F.inverted()
source=P.parent/'right-cave-bays/central-pillar-right-cave-bays.blend';bpy.ops.wm.open_mainfile(filepath=str(source))
protected={o.name:fingerprint(o) for o in bpy.context.scene.objects if o.type=='MESH'}
rocks=[o.name for o in bpy.data.collections['07 | Continuous approved-style cave wall'].objects]
def light(o):return {'matrix':[list(r) for r in o.matrix_world],'energy':o.data.energy,'color':list(o.data.color),'type':o.data.type}
lights={o.name:light(o) for o in bpy.context.scene.objects if o.type=='LIGHT'}
file=P/args.file;bpy.ops.wm.open_mainfile(filepath=str(file));S=bpy.context.scene
changed=[n for n,h in protected.items() if n not in S.objects or fingerprint(S.objects[n])!=h]
changed_lights=[n for n,h in lights.items() if n not in S.objects or light(S.objects[n])!=h]
wall=S.objects['Cavern | single interior rock surface'];bm=bmesh.new();bm.from_mesh(wall.data)
boundary=sum(e.is_boundary for e in bm.edges);bad=sum(len(e.link_faces)>2 for e in bm.edges);loose=sum(len(e.link_faces)==0 for e in bm.edges);seen=set();parts=[]
for v in bm.verts:
    if v in seen:continue
    stack=[v];seen.add(v);n=0
    while stack:
        p=stack.pop();n+=1
        for e in p.link_edges:
            q=e.other_vert(p)
            if q not in seen:seen.add(q);stack.append(q)
    parts.append(n)
bm.free();vs=[];fs=[]
for o in [S.objects[n] for n in rocks]+[wall]:
    T=I@o.matrix_world;off=len(vs);vs.extend(T@v.co for v in o.data.vertices);fs.extend(tuple(off+i for i in p.vertices) for p in o.data.polygons)
tree=BVHTree.FromPolygons(vs,fs);gaps=[]
for z in [3.,7.15,9.]:
    for deg in range(0,360,3):
        t=math.radians(deg);hit=tree.ray_cast(Vector((0,0,z)),Vector((math.cos(t),math.sin(t),0)),60)
        if hit[0] is None:gaps.append([z,deg])
spec=json.loads(S['right_bay_geometry']);start,end=Vector(spec['start']),Vector(spec['end']);axis=(end-start).normalized();side=Vector((-axis.y,axis.x,0));blocked=[]
for lane in [-.3,0,.3]:
    for height in [.2,.6,1.0]:
        p=start-axis*.15+side*lane+Vector((0,0,height));q=end+axis*.1+side*lane+Vector((0,0,height))
        hit=tree.ray_cast(p,(q-p).normalized(),(q-p).length)
        if hit[0] is not None:blocked.append([lane,height])
contacts=json.loads(S['engineered_supports_revision'])['brackets'];anchors=[tree.find_nearest(Vector(b['rock_anchor']))[3] for b in contacts]
checks=[]
for x,y in [(0,0),(0,-6),(-2,-3),(-2,2)]:
    for direction in [-1,1]:checks.append(tree.ray_cast(Vector((x,y,7)),Vector((0,0,direction)),80)[0] is None)
passed=not changed and not changed_lights and len(parts)==1 and boundary>0 and bad==0 and loose==0 and not gaps and not blocked and max(anchors)<.001 and all(checks) and not wall.modifiers and not any(p.use_smooth for p in wall.data.polygons)
report={'passed':passed,'file':str(file),'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'original_meshes_checked':len(protected),'changed_original_meshes_or_material_nodes':changed,'original_rock_objects_restored_exactly':rocks if not any(n in changed for n in rocks) else [],'changed_original_lights':changed_lights,'new_surface_components':parts,'open_boundary_edges':boundary,'interior_nonmanifold_edges':bad,'loose_edges':loose,'new_surface_modifiers':list(wall.modifiers.keys()),'smooth_shaded_faces':sum(p.use_smooth for p in wall.data.polygons),'enclosure_gaps_at_sampled_heights':gaps,'bridge_obstructions':blocked,'support_anchor_distances':anchors,'open_ceiling_and_floor':all(checks),'construction':'One open sheet for the new interior wall. No exterior layer, thickness, smoothing, voxel remesh, top cap or bottom cap.'}
out='surface-verification.json' if args.file=='connected-cavern.blend' else 'preview-surface-verification.json'
(P/out).write_text(json.dumps(report,indent=2));print('SURFACE_VERIFICATION',json.dumps(report),flush=True);assert passed
