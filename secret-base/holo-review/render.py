import bpy, sys
from mathutils import Vector
s=bpy.context.scene
floor=bpy.data.objects['deck_floor_about']; pts=[floor.matrix_world@Vector(v) for v in floor.bound_box]
c=Vector(((min(p.x for p in pts)+max(p.x for p in pts))/2,(min(p.y for p in pts)+max(p.y for p in pts))/2,max(p.z for p in pts)))
cam=bpy.data.objects.new('holo_review_camera',bpy.data.cameras.new('holo_review_camera'));s.collection.objects.link(cam)
cam.location=c+Vector((5,-7,5.7)); cam.rotation_euler=(c+Vector((0,0,.35))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=6.8;s.camera=cam
s.render.resolution_x=1100;s.render.resolution_y=950;s.render.resolution_percentage=100
s.render.filepath='/Users/danielku/mywebsite/secret-base/holo-review/iteration-1.png'
bpy.ops.render.render(write_still=True)
