import bpy,json,math,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P/'coherent-bays.blend'));S=bpy.context.scene;bpy.context.view_layer.update()
report=json.loads((P/'coherent-bays-checks.json').read_text())
FRAME=Matrix.Translation((21.299999237,0,0))@Matrix.Rotation(-math.atan2(12,19),4,'Z');INV=FRAME.inverted()
start,end=Vector(report['bridge_start']),Vector(report['bridge_end']);axis=(end-start).normalized();side=Vector((-axis.y,axis.x,0)).normalized();dg=bpy.context.evaluated_depsgraph_get();obstacles=[]
for ob in S.objects:
    if ob.type!='MESH' or not any(s in ob.name for s in ['guard','stanchion','perimeter post']):continue
    ev=ob.evaluated_get(dg);me=ev.to_mesh();tree=BVHTree.FromPolygons([INV@(ob.matrix_world@v.co) for v in me.vertices],[tuple(p.vertices) for p in me.polygons])
    for offset in [-.26,0,.26]:
        for h in [.22,.43]:
            p=start-axis*.12+side*offset+Vector((0,0,h));q=end+axis*.16+side*offset+Vector((0,0,h));v=q-p
            if tree.ray_cast(p,v.normalized(),v.length)[0] is not None:obstacles.append([ob.name,offset,h])
    ev.to_mesh_clear()
report['saved_bridge_obstacles']=obstacles
wall=S.objects['150 | continuous cave with oblique carved rooms'];tree=BVHTree.FromPolygons([INV@(wall.matrix_world@v.co) for v in wall.data.vertices],[tuple(p.vertices) for p in wall.data.polygons])
rotation=Matrix.Rotation(math.radians(report['yaw_degrees']),4,'Z');origin=Vector((*report['origin'],0))
grounding=[];b=report['bay_info']['lower']
for x,y in [(0,-1.0),(0,.25),(-3.8,.2),(1.7,.2)]:
    p=origin+rotation@Vector((x+b['offset_x'],y+b['offset_y'],b['z']-.015));hit=tree.ray_cast(p,Vector((0,0,-1)),.30)
    grounding.append({'xy':[x,y],'rock_below':hit[0] is not None})
report['rock_seating']=grounding
report['saved_file_passed']=report['passed'] and not obstacles and all(p['rock_below'] for p in grounding)
(P/'coherent-bays-saved-checks.json').write_text(json.dumps(report,indent=2))
print(json.dumps({k:report[k] for k in ['saved_file_passed','saved_bridge_obstacles','rock_seating']}),flush=True)
