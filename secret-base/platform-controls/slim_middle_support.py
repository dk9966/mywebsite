"""Slim the steel frame; halve its lower drop beneath the lower collar."""
import bpy, math
from mathutils import Vector
S=bpy.context.scene
path=bpy.data.filepath
bpy.ops.wm.save_as_mainfile(filepath=path.replace('.blend','-before-slim-support.blend'),copy=True,compress=True)
col=bpy.data.collections['07 | Middle platform steel underframe']
cut=5.625
factor=.65
changed=[]
for o in col.objects:
    if o.type!='MESH':continue
    o.data=o.data.copy()
    if 'collar' in o.name or 'upper load-bearing rim' in o.name:
        vs=o.data.vertices
        radii=[math.hypot(v.co.x,v.co.y) for v in vs]
        rmid=(min(radii)+max(radii))/2
        zmid=(min(v.co.z for v in vs)+max(v.co.z for v in vs))/2
        newmid=cut+(zmid-cut)*.5 if 'rock anchor collar' in o.name else zmid
        for v in vs:
            r=math.hypot(v.co.x,v.co.y)
            nr=rmid+(r-rmid)*factor
            v.co.x*=nr/r;v.co.y*=nr/r
            v.co.z=newmid+(v.co.z-zmid)*factor
    else:
        for v in o.data.vertices:
            v.co.x*=factor;v.co.y*=factor
        if 'rock-to-rim diagonal bracket' in o.name:
            half=max(v.co.z for v in o.data.vertices)
            rot=o.rotation_euler.to_matrix()
            a=o.location+rot@Vector((0,0,-half))
            b=o.location+rot@Vector((0,0,half))
            old=(b-a).length
            a.z=cut+(a.z-cut)*.5
            o.location=(a+b)/2
            o.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler()
            for v in o.data.vertices:v.co.z*=(b-a).length/old
    for m in o.modifiers:
        if m.type=='BEVEL':m.width*=factor
    o.data.update()
    changed.append(o.name)
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=path,compress=True)
result={'saved':path,'members_slimmed':len(changed),'thickness_factor':factor,'lower_drop_before':5.625-4.49,'lower_drop_after':(5.625-4.49)*.5}
