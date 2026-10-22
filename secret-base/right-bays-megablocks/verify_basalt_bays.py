"""Independent reopening, shape, topology, preservation, and passage checks."""
import ast,hashlib,json,math,sys
from pathlib import Path
import bpy,bmesh,numpy as np
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent
tag=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'basalt-bays'
FRAME=Matrix.Translation((21.299999237,0,0))@Matrix.Rotation(-math.atan2(12,19),4,'Z');INV=FRAME.inverted()
source=P.parent/'connected-cavern/connected-cavern-open-chamber.blend'
code=ast.parse((P.parent/'central-metal-platform/build_metal_platform.py').read_text())
exec(compile(ast.Module(body=[n for n in code.body if isinstance(n,ast.FunctionDef) and n.name=='fingerprint'],type_ignores=[]),'fingerprint','exec'),globals())
bpy.ops.wm.open_mainfile(filepath=str(source))
protected={o.name:fingerprint(o) for cn in ['01 | Approved rock and original console','02 | Machined rings and eight recessed grates'] for o in bpy.data.collections[cn].objects if o.type=='MESH'}
bpy.ops.wm.open_mainfile(filepath=str(P/(tag+'.blend')));S=bpy.context.scene;bpy.context.view_layer.update()
report=json.loads((P/(tag+'-checks.json')).read_text());report['saved_middle_changes']=[n for n,h in protected.items() if fingerprint(S.objects[n])!=h]
wall=S.objects['150 | continuous cave with oblique carved rooms'];tree=BVHTree.FromPolygons([INV@(wall.matrix_world@v.co) for v in wall.data.vertices],[tuple(p.vertices) for p in wall.data.polygons])
R=Matrix.Rotation(math.radians(report['common_yaw_degrees']),4,'Z');origin=Vector((*report['origin'],0));F=6.871178627
def at(x,y,z):return origin+R@Vector((x,y,z))
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
                hit=tree.ray_cast(at(x,y+(report['lower_offset_y'] if label=='lower' else 0),z+.09),Vector((0,0,1)),1.75)
                if hit[0] is not None:intrusions.append([label,float(x),float(y),list(hit[0])])
report['standing_space_rock_intrusions']=intrusions
visibility=[]
for camera in ['150 | main cave camera','150 | same azimuth detail']:
    pos=INV@S.objects[camera].location
    for label,p in [('lower center',(0,report['lower_offset_y'],F+.03)),('lower front',(0,-1.5+report['lower_offset_y'],F+.03)),('wing',(-3.6,-.6+report['lower_offset_y'],F+.03)),('upper apron',(-1,-.25,report['upper_floor_z']+.03))]:
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
report['sha256']=hashlib.sha256((P/(tag+'.blend')).read_bytes()).hexdigest();report['saved_file_passed']=report['passed'] and not report['saved_middle_changes'] and not intrusions and not visibility and not obstacles and report['bearing_error']<.01 and report['octagon_landing_error']<.001
(P/(tag+'-saved-checks.json')).write_text(json.dumps(report,indent=2));print('SAVED_CHECK',json.dumps({k:report[k] for k in ['saved_file_passed','saved_middle_changes','standing_space_rock_intrusions','key_floor_occlusions','bridge_railing_obstacles']}),flush=True)
