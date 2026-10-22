"""Check saved bay geometry, camera visibility, and bridge passage."""
import argparse,ast,hashlib,json,math,sys
from pathlib import Path
import bpy,bmesh,numpy as np
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent
ap=argparse.ArgumentParser();ap.add_argument('--final',action='store_true');a=ap.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
tag='reference-bays' if a.final else 'preview-reference-bays';file=P/(tag+'.blend')
FRAME=Matrix.Translation((21.299999237,0,0))@Matrix.Rotation(-math.atan2(12,19),4,'Z');INV=FRAME.inverted()
src=ast.parse((P.parent/'central-metal-platform/build_metal_platform.py').read_text());exec(compile(ast.Module(body=[n for n in src.body if isinstance(n,ast.FunctionDef) and n.name=='fingerprint'],type_ignores=[]),'fingerprint','exec'),globals())
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'connected-cavern/connected-cavern-open-chamber.blend'))
protected={o.name:fingerprint(o) for c in ['01 | Approved rock and original console','02 | Machined rings and eight recessed grates'] for o in bpy.data.collections[c].objects if o.type=='MESH'}
bpy.ops.wm.open_mainfile(filepath=str(file));S=bpy.context.scene;bpy.context.view_layer.update();wall=S.objects['Cave | single wall with two recessed bays']
tree=BVHTree.FromPolygons([INV@(wall.matrix_world@v.co) for v in wall.data.vertices],[tuple(p.vertices) for p in wall.data.polygons])
report=json.loads((P/(tag+'-verification.json')).read_text())
def at(which,x,y,z):
    t=math.radians(report[which+'_yaw_degrees']);ox,oy=report[which+'_origin']
    return Vector((ox+math.cos(t)*x-math.sin(t)*y,oy+math.sin(t)*x+math.cos(t)*y,report[which+'_floor_z']+z))
occlusions=[];visibility_samples=0
for name in ['Rebuilt bays | reference overview','Rebuilt bays | architecture close-up']:
    origin=INV@S.objects[name].location
    for which,points in [('lower',[(0,0,.08),(-1.4,0,.08),(1.4,0,.08),(0,-1.4,.08),(0,1.4,.08),(-2.8,0,.08),(0,0,1.96)]),('upper',[(-2.8,.8,.08),(-.7,1.1,.08),(1.6,.8,.08),(.1,1.95,2.49)])]:
        for p in points:
            target=at(which,*p);ray=target-origin;visibility_samples+=1;hit=tree.ray_cast(origin,ray.normalized(),ray.length-.04)
            if hit[0] is not None:occlusions.append({'camera':name,'bay':which,'target':p,'hit':list(hit[0])})
# Test both the original perimeter gate and the wing entry using evaluated rails.
start,end=Vector(report['bridge_start']),Vector(report['bridge_end']);axis=(end-start).normalized();side=Vector((-axis.y,axis.x,0)).normalized();hits=[]
dg=bpy.context.evaluated_depsgraph_get()
for ob in S.objects:
    if ob.type!='MESH' or not ('guard' in ob.name or 'perimeter post' in ob.name or 'Bridge | post' in ob.name):continue
    ev=ob.evaluated_get(dg);me=ev.to_mesh();tr=BVHTree.FromPolygons([INV@(ob.matrix_world@v.co) for v in me.vertices],[tuple(p.vertices) for p in me.polygons])
    for lane in [-.31,0,.31]:
        for h in [.20,.38]:
            p=start-axis*.20+side*lane+Vector((0,0,h));q=end+axis*.28+side*lane+Vector((0,0,h));v=q-p
            hit=tr.ray_cast(p,v.normalized(),v.length)
            if hit[0] is not None:hits.append({'object':ob.name,'lane':lane,'height':h,'hit':list(hit[0])})
    ev.to_mesh_clear()
changed=[n for n,h in protected.items() if n not in S.objects or fingerprint(S.objects[n])!=h]
report.update({'reopened_saved_file':True,'saved_center_mesh_changes':changed,'camera_visibility_samples':visibility_samples,'camera_rock_occlusions':occlusions,'bridge_rail_obstructions':hits,'sha256':hashlib.sha256(file.read_bytes()).hexdigest()})
report['saved_checks_passed']=not changed and not occlusions and not hits
(P/(tag+'-saved-check.json')).write_text(json.dumps(report,indent=2));print('SAVED_BAYS_CHECK',json.dumps({k:report[k] for k in ['saved_checks_passed','camera_rock_occlusions','bridge_rail_obstructions','saved_center_mesh_changes']}),flush=True)
if a.final:assert report['passed'] and report['saved_checks_passed']
