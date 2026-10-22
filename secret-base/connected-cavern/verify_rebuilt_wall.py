"""Reopen the saved wall revision and check preservation and usable bay space."""
import ast,hashlib,json,math
from pathlib import Path
import bpy,bmesh,numpy as np
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent
F=Matrix.Translation((21.299999237,0,0))@Matrix.Rotation(-math.atan2(12,19),4,'Z');I=F.inverted()
src=ast.parse((P.parent/'central-metal-platform/build_metal_platform.py').read_text());exec(compile(ast.Module(body=[n for n in src.body if isinstance(n,ast.FunctionDef) and n.name=='fingerprint'],type_ignores=[]),'fingerprint','exec'),globals())
def wall_tree(ob):
    T=I@ob.matrix_world
    return BVHTree.FromPolygons([T@v.co for v in ob.data.vertices],[tuple(p.vertices) for p in ob.data.polygons])
def light(ob):return ([list(row) for row in ob.matrix_world],ob.data.type,list(ob.data.color),ob.data.energy)
bpy.ops.wm.open_mainfile(filepath=str(P/'connected-cavern-single-surface.blend'));S=bpy.context.scene
old=S.objects['Cavern | single connected interior surface'];before=wall_tree(old)
protected={o.name:fingerprint(o) for o in S.objects if o.type=='MESH' and o!=old};lights={o.name:light(o) for o in S.objects if o.type=='LIGHT'}
file=P/'connected-cavern-right-wall-rebuilt.blend';bpy.ops.wm.open_mainfile(filepath=str(file));S=bpy.context.scene;bpy.context.view_layer.update()
wall=S.objects['Cavern | rebuilt continuous interior wall'];after=wall_tree(wall)
changed=[name for name,value in protected.items() if name not in S.objects or fingerprint(S.objects[name])!=value];changed_lights=[name for name,value in lights.items() if name not in S.objects or light(S.objects[name])!=value]
left_deltas=[]
for z in [0.,3.,7.,10.,14.]:
    for deg in range(90,286,2):
        t=math.radians(deg+.3);p=Vector((0,0,z));v=Vector((math.cos(t),math.sin(t),0));a=before.ray_cast(p,v,50);b=after.ray_cast(p,v,50)
        left_deltas.append(abs(a[3]-b[3]) if a[0] is not None and b[0] is not None else 100.)
layout=json.loads((P.parent/'right-cave-bays/right-bays-audit.json').read_text());intrusions=[];sampled=0
def inside(p,poly):
    odd=False
    for a,b in zip(poly,poly[1:]+poly[:1]):
        if (a[1]>p[1])!=(b[1]>p[1]) and p[0]<(b[0]-a[0])*(p[1]-a[1])/(b[1]-a[1])+a[0]:odd=not odd
    return odd
for which in ['lower','upper']:
    poly=layout[which+'_floor_polygon'];z=layout[which+'_floor_height']
    for x in np.arange(min(p[0] for p in poly)+.18,max(p[0] for p in poly),.32):
        for y in np.arange(min(p[1] for p in poly)+.18,max(p[1] for p in poly),.32):
            if not inside((x,y),poly):continue
            sampled+=1;hit=after.ray_cast(Vector((x,y,z+.12)),Vector((0,0,1)),1.60)
            if hit[0] is not None:intrusions.append([which,float(x),float(y),float(hit[0].z)])
base=json.loads((P/'right-wall-rebuilt-verification.json').read_text())
report={**base,'file':str(file),'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'reopened_saved_file':True,'changed_non_wall_meshes':changed,'changed_lights':changed_lights,'left_wall_sample_count':len(left_deltas),'left_wall_max_surface_difference':max(left_deltas),'platform_clearance_samples':sampled,'rock_intrusions_into_bay_standing_space':intrusions}
report['passed']=base['passed'] and not changed and not changed_lights and max(left_deltas)<.02 and not intrusions
(P/'right-wall-rebuilt-verification.json').write_text(json.dumps(report,indent=2));print('SAVED_WALL_VERIFICATION',json.dumps(report),flush=True);assert report['passed']
