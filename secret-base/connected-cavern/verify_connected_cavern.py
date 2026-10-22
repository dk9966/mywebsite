"""Verify restored geometry and materials plus the new open interior surface."""
import ast,hashlib,json,math
from pathlib import Path
import bpy,bmesh,numpy as np
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent;SOURCE=P.parent/'right-cave-bays/central-pillar-right-cave-bays.blend';OUTPUT=P/'connected-cavern.blend'
FRAME=Matrix.Translation((21.299999237,0,0))@Matrix.Rotation(-math.atan2(12,19),4,'Z');INV=FRAME.inverted()
meta=json.loads((P/'interior-preservation.json').read_text());allowed=set(meta['upper_mouth_rock_objects'])
src=ast.parse((P.parent/'central-metal-platform/build_metal_platform.py').read_text())
exec(compile(ast.Module(body=[n for n in src.body if isinstance(n,ast.FunctionDef) and n.name=='fingerprint'],type_ignores=[]),'fingerprint','exec'),globals())
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
protected={o.name:fingerprint(o) for o in bpy.context.scene.objects if o.type=='MESH' and o.name not in allowed}
original_points={}
for name in allowed:
    ob=bpy.data.objects[name];T=INV@ob.matrix_world
    original_points[name]=[T@ob.data.vertices[i].co for i in range(0,len(ob.data.vertices),max(1,len(ob.data.vertices)//2200))]
bpy.ops.wm.open_mainfile(filepath=str(OUTPUT));S=bpy.context.scene
changed=[n for n,h in protected.items() if n not in S.objects or fingerprint(S.objects[n])!=h]
wall=S.objects['Cave | single interior wall surface'];bm=bmesh.new();bm.from_mesh(wall.data);boundary=sum(e.is_boundary for e in bm.edges);bad=sum(not e.is_manifold and not e.is_boundary for e in bm.edges);seen=set();parts=[]
for vertex in bm.verts:
    if vertex in seen:continue
    stack=[vertex];seen.add(vertex);count=0
    while stack:
        vv=stack.pop();count+=1
        for e in vv.link_edges:
            q=e.other_vert(vv)
            if q not in seen:seen.add(q);stack.append(q)
    parts.append(count)
bm.free()
def tree_for(objects):
    vs=[];fs=[]
    for ob in objects:
        off=len(vs);T=INV@ob.matrix_world;vs.extend(T@v.co for v in ob.data.vertices);fs.extend(tuple(off+i for i in p.vertices) for p in ob.data.polygons)
    return BVHTree.FromPolygons(vs,fs)
audit=json.loads((P.parent/'right-cave-bays/right-bays-audit.json').read_text());hp=[Vector(p) for p in audit['upper_floor_polygon']];u=(hp[1]-hp[0]).normalized();v=Vector((-u.y,u.x));origin=(hp[0]+hp[1])/2
section=meta['upper_mouth_cut_section'];depth=meta['upper_mouth_cut_depth'];xmin=min(p[0] for p in section)-.1;xmax=max(p[0] for p in section)+.1;zmin=min(p[1] for p in section)-.1;zmax=max(p[1] for p in section)+.1
outside_errors=[];checked=0
for name,points in original_points.items():
    tree=tree_for([S.objects[name]])
    for pt in points:
        xy=pt.xy-origin;x=xy.dot(u);y=xy.dot(v)
        if xmin<=x<=xmax and depth[0]-.1<=y<=depth[1]+.1 and zmin<=pt.z<=zmax:continue
        checked+=1;near=tree.find_nearest(pt)
        if near[3]>.001:outside_errors.append({'object':name,'point':list(pt),'distance':near[3]})
rocks=list(bpy.data.collections['07 | Continuous approved-style cave wall'].objects)+[wall];tree=tree_for(rocks);spec=json.loads(S['right_bay_geometry']);start,end=Vector(spec['start']),Vector(spec['end']);axis=(end-start).normalized();side=Vector((-axis.y,axis.x,0));bridge=[]
for lane in [-.30,0,.30]:
    for height in [.2,.55,1.05]:
        p=start-axis*.15+side*lane+Vector((0,0,height));q=end+axis*.1+side*lane+Vector((0,0,height));hit=tree.ray_cast(p,(q-p).normalized(),(q-p).length)
        if hit[0] is not None:bridge.append([lane,height])
gaps=[]
for z in [3.,7.15,9.]:
    for d in range(0,360,3):
        t=math.radians(d);hit=tree.ray_cast(Vector((0,0,z)),Vector((math.cos(t),math.sin(t),0)),70)
        if hit[0] is None:gaps.append([z,d])
anchors=[tree.find_nearest(Vector(b['rock_anchor']))[3] for b in json.loads(S['engineered_supports_revision'])['brackets']]
no_caps=all(tree.ray_cast(Vector((0,0,7)),Vector((0,0,z)),70)[0] is None for z in [-1,1])
passed=not changed and not outside_errors and len(parts)==1 and boundary>0 and bad==0 and len(wall.modifiers)==0 and not bridge and not gaps and max(anchors)<.001 and no_caps
report={'passed':passed,'file':str(OUTPUT),'sha256':hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),'preserved_original_meshes_and_materials':len(protected),'unexpected_changes':changed,'upper_mouth_edited_rock_objects':sorted(allowed),'original_rock_samples_outside_upper_cut':checked,'rock_changes_outside_upper_cut':outside_errors,'interior_surface_components':parts,'interior_surface_vertices':len(wall.data.vertices),'open_boundary_edges':boundary,'nonmanifold_nonboundary_edges':bad,'interior_surface_modifiers':len(wall.modifiers),'thickness':0,'bridge_obstructions':bridge,'enclosure_gaps':gaps,'support_anchor_distances':anchors,'no_ceiling_or_floor':no_caps}
(P/'saved-file-verification.json').write_text(json.dumps(report,indent=2));print('VERIFY_INTERIOR',json.dumps(report),flush=True);assert passed
