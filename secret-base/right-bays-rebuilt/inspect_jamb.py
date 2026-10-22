import bpy,math,json
from pathlib import Path
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P/'preview-reference-bays.blend'));S=bpy.context.scene
F=Matrix.Translation((21.299999237,0,0))@Matrix.Rotation(-math.atan2(12,19),4,'Z');I=F.inverted()
wall=S.objects['Cave | single wall with two recessed bays'];tree=BVHTree.FromPolygons([I@(wall.matrix_world@v.co) for v in wall.data.vertices],[tuple(p.vertices) for p in wall.data.polygons])
cam=S.objects['Rebuilt bays | architecture close-up'];fr=cam.data.view_frame(scene=S);xmin=min(p.x for p in fr);xmax=max(p.x for p in fr);ymin=min(p.y for p in fr);ymax=max(p.y for p in fr);z=fr[0].z;origin=I@cam.location
out=[]
for x,y in [(1400,550),(1430,620),(1400,670),(1440,730),(1320,585),(1340,650)]:
    direction=I.to_3x3()@cam.matrix_world.to_3x3()@Vector((xmin+(xmax-xmin)*x/1500,ymax-(ymax-ymin)*y/818,z));hit=tree.ray_cast(origin,direction.normalized(),80)
    if hit[0] is None:continue
    face=wall.data.polygons[hit[2]];vs=[I@(wall.matrix_world@wall.data.vertices[k].co) for k in face.vertices]
    out.append({'pixel':[x,y],'point':list(hit[0]),'theta':math.degrees(math.atan2(hit[0].y,hit[0].x)),'normal':list(hit[1]),'face':hit[2],'vertices':[list(v) for v in vs]})
(P/'jamb-diagnostic.json').write_text(json.dumps(out,indent=2));print(json.dumps(out),flush=True)
