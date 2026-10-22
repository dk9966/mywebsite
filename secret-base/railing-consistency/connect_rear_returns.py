"""Close the short rail gaps between the rear bridge and circular guardrail."""
import bpy
import json
from pathlib import Path
from mathutils import Vector

P=Path(__file__).resolve().parent
D=bpy.context.evaluated_depsgraph_get()
UP=Vector((0,0,1))
COL=bpy.data.collections['170 | Rear-left connected platform']
made=[]
for name,height in [('Metal | continuous steel guardrail',.19),('Metal | continuous steel guardrail.001',.345)]:
    e=bpy.data.objects[name].evaluated_get(D)
    for side in (0,1):
        post=bpy.data.objects['Rear left | side %d upright'%side].evaluated_get(D)
        ps=[post.matrix_world@v.co for v in post.data.vertices]
        end=sum(ps,Vector())/len(ps)
        end.z=min(v.z for v in ps)+height
        candidates=[]
        for f in e.data.polygons:
            vs=[e.matrix_world@e.data.vertices[i].co for i in f.vertices]
            p=sum(vs,Vector())/len(vs)
            normal=(e.matrix_world.to_3x3()@f.normal).normalized()
            radial=Vector((p.x-21.3,p.y,0)).normalized()
            tangent=UP.cross(radial)
            if abs(normal.dot(tangent))>.85 and abs(p.z-end.z)<.002:
                candidates.append(((p-end).length,p,normal,vs))
        distance,start,normal,cap=min(candidates,key=lambda x:x[0])
        assert distance<.12,distance
        # Loft a short elbow from the actual circular cap to the bridge cap.
        start_axis=UP.cross(normal).normalized()
        rail=bpy.data.objects['Rear left | side %d continuous rail'%side]
        edges=[rail.matrix_world.to_3x3()@(rail.data.vertices[x.vertices[1]].co-rail.data.vertices[x.vertices[0]].co) for x in rail.data.edges]
        direction=max(edges,key=lambda x:x.length).normalized()
        end_axis=UP.cross(direction).normalized()
        span=end-start
        across=UP.cross(span).normalized()
        if start_axis.dot(across)<0:start_axis=-start_axis
        if end_axis.dot(across)<0:end_axis=-end_axis
        halfwidth=max(abs((v-start).dot(start_axis)) for v in cap)
        halfheight=(max(v.z for v in cap)-min(v.z for v in cap))/2
        vertices=[]
        for p,axis,w,h in [(start,start_axis,halfwidth,halfheight),(end,end_axis,.0125,.009)]:
            vertices.extend(tuple(p+axis*sg*w+UP*z*h) for sg,z in [(-1,-1),(1,-1),(1,1),(-1,1)])
        faces=[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
        label='Rear left | continuous entrance return %d %.3f'%(side,height)
        mesh=bpy.data.meshes.new(label);mesh.from_pydata(vertices,[],faces);mesh.update()
        ob=bpy.data.objects.new(label,mesh);COL.objects.link(ob)
        mesh.materials.append(bpy.data.materials['Metal | dark structural steel'])
        bevel=ob.modifiers.new('Matching small fabricated edge','BEVEL');bevel.width=.0006;bevel.segments=2
        ob.modifiers.new('Weighted fabricated normals','WEIGHTED_NORMAL')
        made.append({'name':label,'length_m':distance})
report=json.loads(P.joinpath('verification.json').read_text())
report['rear_entrance_rail_connections']=made
P.joinpath('verification.json').write_text(json.dumps(report,indent=2))
result={'rear_entrance_rail_connections':made}
