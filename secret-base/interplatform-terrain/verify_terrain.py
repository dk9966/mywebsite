import bpy,bmesh,json,math,hashlib,struct
from pathlib import Path
from mathutils import Vector,Matrix
P=Path(__file__).resolve().parent;S=bpy.context.scene
w=bpy.data.objects['150 | continuous cave with oblique carved rooms']
ctrl=bpy.data.objects['SCENE SLIDERS'];mod=ctrl.modifiers['Scene Sliders']
sockets={i.name:i.identifier for i in mod.node_group.interface.items_tree if i.item_type=='SOCKET' and i.in_out=='INPUT'}
hk=sockets['Light height above walls (m)'];rk=sockets['Light radius (m)']
initial=(mod[hk],mod[rk]);checks=[]
D=json.loads((P.parent/'upper-right-platform/build-report.json').read_text());F=Matrix(D['frame']);H=D['height']
roofs=[o for o in S.objects if o.name.startswith('Lower | roof slope ')]
root=bpy.data.objects['Lower | circular roof assembly']
for height,radius in [initial,(.35,.85),(1.49,1.46),(2.10,2.10)]:
    mod[hk]=height;mod[rk]=radius;ctrl.update_tag();S.frame_set(S.frame_current);bpy.context.view_layer.update()
    dg=bpy.context.evaluated_depsgraph_get();e=w.evaluated_get(dg);inv=e.matrix_world.inverted();M=inv@F
    gaps=[]
    for i in range(21):
        for j in range(21):
            x=-2.75+5.5*i/20;y=-2.75+5.5*j/20
            hit,p,n,idx=e.ray_cast(M@Vector((x,y,H-.15)),Vector((0,0,-1)),distance=10)
            gaps.append(H-.20-(F.inverted()@e.matrix_world@p).z if hit else 100.)
    contact={}
    for roof in roofs:
        re=roof.evaluated_get(dg);rm=inv@re.matrix_world;distances=[]
        for poly in re.data.polygons:
            if poly.normal.z<.25:continue
            p=rm@poly.center
            hit,q,n,idx=e.ray_cast(p-Vector((0,0,.18)),Vector((0,0,1)),distance=.4)
            if hit:distances.append(q.z-p.z)
        close=[v for v in distances if -.075<v<.025]
        contact[roof.name]={'contact_samples':len(close),'contact_gap_min_max':([min(close),max(close)] if close else None)}
    ce=bpy.data.objects['Lower | circular light upper cover'].evaluated_get(dg)
    cv=[ce.matrix_world@v.co for v in ce.data.vertices];ztop=max(p.z for p in cv)
    center=inv@root.matrix_world.translation
    intrusions=[]
    for i in range(17):
        for j in range(17):
            x=radius*(i-8)/8*.96;y=radius*(j-8)/8*.96
            if x*x+y*y>radius*radius*.96**2:continue
            hit,p,n,idx=e.ray_cast(Vector((center.x+x,center.y+y,ztop-.22)),Vector((0,0,1)),distance=.225)
            if hit:intrusions.append([x,y,p.z-ztop])
    checks.append({'height':height,'radius':radius,'upper_bearing_gap_m':[min(gaps),max(gaps)],'unsupported_upper_samples':sum(abs(v)>.045 for v in gaps),'roof_contact':contact,'fixture_intrusions':len(intrusions),'intrusion_examples':intrusions[:3]})
mod[hk],mod[rk]=initial;ctrl.update_tag();S.frame_set(S.frame_current);bpy.context.view_layer.update()
e=w.evaluated_get(bpy.context.evaluated_depsgraph_get());bm=bmesh.new();bm.from_mesh(e.data);left=set(bm.verts);components=[]
while left:
    stack=[left.pop()];count=0
    while stack:
        v=stack.pop();count+=1
        for ed in v.link_edges:
            other=ed.other_vert(v)
            if other in left:left.remove(other);stack.append(other)
    components.append(count)
local_bad=[]
for f in bm.faces:
    c=f.calc_center_median()
    if f.calc_area()<1e-10 and 3.25<c.x<14.1 and -7<c.y<4 and 8.98<c.z<11.35:local_bad.append(list(c))
def digest(o):
    h=hashlib.sha256();h.update(str([list(r) for r in o.matrix_world]).encode());h.update(str((o.hide_viewport,o.hide_render,o.hide_get())).encode())
    if o.type=='MESH':
        for v in o.data.vertices:h.update(struct.pack('3f',*v.co))
        for p in o.data.polygons:h.update(str(tuple(p.vertices)).encode())
    return h.hexdigest()
protected=json.loads((P/'protected-before.json').read_text())
changed=[name for name,h in protected.items() if name not in bpy.data.objects or digest(bpy.data.objects[name])!=h]
preservation=json.loads((P/'preservation-live.json').read_text())
result={'triangles_before':72208,'triangles_after':sum(len(f.vertices)-2 for f in e.data.polygons),'connected_components':len(components),'loose_edges':sum(not ed.link_faces for ed in bm.edges),'nonmanifold_junctions':sum(len(ed.link_faces)>2 for ed in bm.edges),'degenerate_faces_in_edit':local_bad,'unrelated_object_changes_live':preservation['changed'],'reopen_fingerprint_differences':len(changed),'preservation_note':'Live fingerprints are authoritative; reopened files recompute transforms and per-view-layer visibility.','checked_objects':len(protected),'controls_restored':initial,'control_checks':checks}
bm.free();(P/'verification.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
