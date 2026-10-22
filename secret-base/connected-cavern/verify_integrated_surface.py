"""Check the joined skin against the latest upper-bay scene snapshot."""
import ast,hashlib,json,math,sys
from pathlib import Path
import bpy,bmesh,numpy as np
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree

P=Path(__file__).resolve().parent
F=Matrix.Translation((21.299999237,0,0))@Matrix.Rotation(-math.atan2(12,19),4,'Z');I=F.inverted()
src=ast.parse((P.parent/'central-metal-platform/build_metal_platform.py').read_text())
exec(compile(ast.Module(body=[n for n in src.body if isinstance(n,ast.FunctionDef) and n.name=='fingerprint'],type_ignores=[]),'fingerprint','exec'),globals())
file=P/(sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'preview-integrated-surface.blend')
bpy.ops.wm.open_mainfile(filepath=str(P/'preview-integration-source.blend'));S=bpy.context.scene
rocks=list(bpy.data.collections['07 | Continuous approved-style cave wall'].objects)
rocks.append(S.objects['Cave | single interior wall surface'])
excluded={o.name for o in rocks}
protected={o.name:fingerprint(o) for o in S.objects if o.type=='MESH' and o.name not in excluded}
def light(o):return {'matrix':[list(r) for r in o.matrix_world],'energy':o.data.energy,'color':list(o.data.color),'type':o.data.type}
lights={o.name:light(o) for o in S.objects if o.type=='LIGHT'}
def tree_for(objects):
    vs=[];fs=[]
    for o in objects:
        T=I@o.matrix_world;off=len(vs);vs.extend(T@v.co for v in o.data.vertices);fs.extend(tuple(off+i for i in p.vertices) for p in o.data.polygons)
    return BVHTree.FromPolygons(vs,fs)
source_tree=tree_for(rocks)
bpy.ops.wm.open_mainfile(filepath=str(file));S=bpy.context.scene;bpy.context.view_layer.update()
changed=[n for n,h in protected.items() if n not in S.objects or fingerprint(S.objects[n])!=h]
changed_lights=[n for n,h in lights.items() if n not in S.objects or light(S.objects[n])!=h]
wall=S.objects['Cavern | single connected interior surface'];bm=bmesh.new();bm.from_mesh(wall.data)
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
bm.free();tree=tree_for([wall]);gaps=[]
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
coverage=[]
for name in ['Interior | overview','Interior | reverse']:
    cam=S.objects[name];T=I@cam.matrix_world;p=T.translation;corners=cam.data.view_frame(scene=S)
    xmin,xmax=min(v.x for v in corners),max(v.x for v in corners);ymin,ymax=min(v.y for v in corners),max(v.y for v in corners);z=corners[0].z
    tested=0;misses=[]
    for ix in range(220):
        for iy in range(132):
            ray=(T.to_3x3()@Vector((xmin+(xmax-xmin)*(ix+.5)/220,ymin+(ymax-ymin)*(iy+.5)/132,z))).normalized()
            a=source_tree.ray_cast(p,ray,100);b=tree.ray_cast(p,ray,100)
            if a[0] is None:continue
            tested+=1
            if b[0] is None or b[3]>a[3]+.04:misses.append([ix,iy,round(a[3],3),None if b[0] is None else round(b[3],3)])
    coverage.append({'camera':name,'tested_rays':tested,'surface_misses':len(misses),'examples':misses[:15]})
temporary=sum(wall.data.materials[p.material_index].get('surface_role')=='remove' for p in wall.data.polygons)
broad_caps=[p.index for p in wall.data.polygons if p.normal.z>.94 and p.area>18 and p.center.x>3]
passed=not changed and not changed_lights and len(parts)==1 and boundary>0 and bad==0 and loose==0 and not gaps and not blocked and max(anchors)<.001 and all(checks) and not wall.modifiers and temporary==0 and not broad_caps
report={'passed':passed,'file':str(file),'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'non_wall_meshes_checked':len(protected),'changed_protected_meshes_or_materials':changed,'changed_original_lights':changed_lights,'surface_components':parts,'open_boundary_edges':boundary,'nonmanifold_edges_over_two_faces':bad,'loose_edges':loose,'wall_modifiers':list(wall.modifiers.keys()),'smooth_shaded_faces':sum(p.use_smooth for p in wall.data.polygons),'temporary_exterior_faces':temporary,'enclosure_gaps_at_sampled_heights':gaps,'bridge_obstructions':blocked,'support_anchor_distances':anchors,'open_ceiling_and_floor':all(checks),'interior_camera_coverage':coverage}
report['old_solid_cap_faces_remaining']=broad_caps
(P/'single-surface-verification.json').write_text(json.dumps(report,indent=2));print('INTEGRATED_VERIFICATION',json.dumps(report),flush=True)
assert passed
