"""Independent reopening, shape, topology, preservation, and passage checks."""
import ast,hashlib,json,math,sys
from pathlib import Path
import bpy,bmesh,numpy as np
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent
tag=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'rock-ledge-bays'
FRAME=Matrix.Translation((21.299999237,0,0))@Matrix.Rotation(-math.atan2(12,19),4,'Z');INV=FRAME.inverted()
source=P.parent/'connected-cavern/connected-cavern-open-chamber.blend'
code=ast.parse((P.parent/'central-metal-platform/build_metal_platform.py').read_text())
exec(compile(ast.Module(body=[n for n in code.body if isinstance(n,ast.FunctionDef) and n.name=='fingerprint'],type_ignores=[]),'fingerprint','exec'),globals())
bpy.ops.wm.open_mainfile(filepath=str(source))
protected={o.name:fingerprint(o) for cn in ['01 | Approved rock and original console','02 | Machined rings and eight recessed grates'] for o in bpy.data.collections[cn].objects if o.type=='MESH'}
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'right-bays-straight-wall/straight-wall-bays.blend'))
def anchor_part(name):return any(word in name for word in ['diagonal bracket','bracket flange','bolting shoe'])
lower_before={o.name:fingerprint(o) for o in bpy.context.scene.objects if o.type=='MESH' and o.name.startswith(('Lower |','Bridge |')) and not anchor_part(o.name)}
upper_before={o.name:np.array([tuple(INV@(o.matrix_world@v.co)) for v in o.data.vertices]) for o in bpy.context.scene.objects if o.type=='MESH' and o.name.startswith('Upper |') and not anchor_part(o.name)}
bpy.ops.wm.open_mainfile(filepath=str(P/(tag+'.blend')));S=bpy.context.scene;bpy.context.view_layer.update()
report=json.loads((P/(tag+'-checks.json')).read_text());report['saved_middle_changes']=[n for n,h in protected.items() if fingerprint(S.objects[n])!=h]
report['saved_lower_or_bridge_changes']=[n for n,h in lower_before.items() if n not in S.objects or fingerprint(S.objects[n])!=h]
expected_shift=np.array([*report['upper_slide_vector'],0]);shift_errors=[]
for name,before in upper_before.items():
    ob=S.objects.get(name)
    if ob is None or len(ob.data.vertices)!=len(before):shift_errors.append([name,'missing or changed mesh']);continue
    after=np.array([tuple(INV@(ob.matrix_world@v.co)) for v in ob.data.vertices]);error=float(np.max(np.linalg.norm(after-before-expected_shift,axis=1)))
    if error>2e-5:shift_errors.append([name,error])
report['upper_rigid_shift_errors']=shift_errors
wall=S.objects['150 | continuous cave with oblique carved rooms'];tree=BVHTree.FromPolygons([INV@(wall.matrix_world@v.co) for v in wall.data.vertices],[tuple(p.vertices) for p in wall.data.polygons])
R=Matrix.Rotation(math.radians(report['common_yaw_degrees']),4,'Z');origin=Vector((*report['origin'],0));F=6.871178627
def at(x,y,z):return origin+R@Vector((x,y,z))
grounding=[]
for x,y in [(0,-1.5),(0,.25),(-3.8,.20),(1.7,.2)]:
    probe=at(x,y+report['lower_offset_y'],report['lower_floor_z']-.15)
    hit=tree.ray_cast(probe,Vector((0,0,-1)),.20)
    grounding.append({'local_xy':[x,y],'rock_below':hit[0] is not None,'gap_from_probe':hit[3] if hit[0] is not None else None})
report['lower_deck_rock_seating']=grounding
def inside(x,y,poly):
    yes=False
    for p,q in zip(poly,poly[1:]+poly[:1]):
        if (p[1]>y)!=(q[1]>y) and x<(q[0]-p[0])*(y-p[1])/(q[1]-p[1])+p[0]:yes=not yes
    return yes
intrusions=[]
for label,z,poly in [('lower',report['lower_floor_z'],report['lower_polygon']),('upper',report['upper_floor_z'],report['upper_polygon'])]:
    for x in np.arange(min(v[0] for v in poly)+.13,max(v[0] for v in poly),.22):
        for y in np.arange(min(v[1] for v in poly)+.13,max(v[1] for v in poly),.22):
            if inside(x,y,poly):
                hit=tree.ray_cast(at(x+(report['upper_offset_x'] if label=='upper' else 0),y+(report['lower_offset_y'] if label=='lower' else 0),z+.09),Vector((0,0,1)),1.75)
                if hit[0] is not None:intrusions.append([label,float(x),float(y),list(hit[0])])
report['standing_space_rock_intrusions']=intrusions
visibility=[]
for camera in ['150 | main cave camera','150 | same azimuth detail']:
    pos=INV@S.objects[camera].location
    for label,p in [('lower center',(0,report['lower_offset_y'],F+.03)),('lower front',(0,-1.5+report['lower_offset_y'],F+.03)),('wing',(-3.6,-.6+report['lower_offset_y'],F+.03)),('upper apron',(-1+report['upper_offset_x'],-.25,report['upper_floor_z']+.03))]:
        v=at(*p)-pos;hit=tree.ray_cast(pos,v.normalized(),v.length-.05)
        if hit[0] is not None:visibility.append([camera,label,list(hit[0])])
report['key_floor_occlusions']=visibility
start,end=Vector(report['bridge_start']),Vector(report['bridge_end']);axis=(end-start).normalized();side=Vector((-axis.y,axis.x,0)).normalized();obstacles=[];dg=bpy.context.evaluated_depsgraph_get()
for ob in S.objects:
    if ob.type!='MESH' or not any(s in ob.name for s in ['guard','stanchion','perimeter post']):continue
    ev=ob.evaluated_get(dg);me=ev.to_mesh();bt=BVHTree.FromPolygons([INV@(ob.matrix_world@v.co) for v in me.vertices],[tuple(p.vertices) for p in me.polygons])
    for offset in [-.30,0,.30]:
        for h in [.22,.43]:
            p=start-axis*.16+side*offset+Vector((0,0,h));q=end+axis*.22+side*offset+Vector((0,0,h));v=q-p
            if bt.ray_cast(p,v.normalized(),v.length)[0] is not None:obstacles.append([ob.name,offset,h])
    ev.to_mesh_clear()
report['bridge_railing_obstacles']=obstacles
bearing=math.degrees(math.atan2(start.x,start.y))%360
report['actual_bridge_attachment_bearing']=bearing
report['bearing_error']=abs(bearing-report['bridge_attachment_bearing'])
report['octagon_landing_error']=(end-at(0,-2.5+.14+report['lower_offset_y'],report['lower_floor_z']+.006)).length
# Recompute wall connectivity on the saved geometry, including the straightened
# former corner. It must remain a single inside surface, with open top/bottom.
bm=bmesh.new();bm.from_mesh(wall.data);seen=set();components=[]
for vertex in bm.verts:
    if vertex in seen:continue
    todo=[vertex];seen.add(vertex);count=0
    while todo:
        current=todo.pop();count+=1
        for edge in current.link_edges:
            neighbor=edge.other_vert(current)
            if neighbor not in seen:seen.add(neighbor);todo.append(neighbor)
    components.append(count)
report['saved_wall_components']=components
report['saved_wall_invalid_edges']=sum(len(e.link_faces)>2 or not e.link_faces for e in bm.edges);bm.free()
wall_plan=np.array(report['wall_plan']);turns=[]
for i in [0,1]:
    incoming=wall_plan[i]-wall_plan[i-1];outgoing=wall_plan[(i+1)%len(wall_plan)]-wall_plan[i]
    turns.append(float(math.degrees(math.acos(np.clip(np.dot(incoming,outgoing)/(np.linalg.norm(incoming)*np.linalg.norm(outgoing)),-1,1)))))
report['right_continuation_turns_degrees']=turns
report['sha256']=hashlib.sha256((P/(tag+'.blend')).read_bytes()).hexdigest();report['saved_file_passed']=report['passed'] and not report['saved_middle_changes'] and not intrusions and not visibility and not obstacles and report['bearing_error']<.01 and report['octagon_landing_error']<.001 and len(components)==1 and not report['saved_wall_invalid_edges'] and max(turns)<.01
report['saved_file_passed']=report['saved_file_passed'] and not report['saved_lower_or_bridge_changes'] and not shift_errors and all(g['rock_below'] for g in grounding)
(P/(tag+'-saved-checks.json')).write_text(json.dumps(report,indent=2));print('SAVED_CHECK',json.dumps({k:report[k] for k in ['saved_file_passed','saved_middle_changes','standing_space_rock_intrusions','key_floor_occlusions','bridge_railing_obstacles']}),flush=True)
