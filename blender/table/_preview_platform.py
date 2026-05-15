"""One-off: render top + 3/4 previews of test.blend showing the platform."""

import bpy
import math
from mathutils import Vector

bpy.ops.wm.open_mainfile(
    filepath="/Users/danielku/mywebsite/blender/test.blend"
)

# Hide PCB / extra collections so the table area is the focus.
for lc in bpy.context.view_layer.layer_collection.children:
    if lc.name in ("PCB", "PCB_Roster_Z", "TronBaseMesh"):
        lc.exclude = True

scene = bpy.context.scene
scene.use_nodes = False
scene.render.use_compositing = False
scene.render.use_sequencer = False

scene.render.engine = "CYCLES"
scene.cycles.samples = 32
scene.cycles.use_denoising = True
scene.render.resolution_x = 1280
scene.render.resolution_y = 800
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"

# Add a simple sun + ground plane wash for visibility.
sun_data = bpy.data.lights.new("PreviewSun", "SUN")
sun_data.energy = 4.0
sun = bpy.data.objects.new("PreviewSun", sun_data)
sun.rotation_euler = (math.radians(45), math.radians(20), 0.0)
bpy.context.collection.objects.link(sun)


def add_camera(name, location, look_at, ortho_scale=None):
    cam_data = bpy.data.cameras.new(name)
    cam = bpy.data.objects.new(name, cam_data)
    bpy.context.collection.objects.link(cam)
    cam.location = location
    direction = Vector(look_at) - Vector(location)
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    if ortho_scale is not None:
        cam_data.type = "ORTHO"
        cam_data.ortho_scale = ortho_scale
    return cam


# Frame the area roughly centered on the platform / table midpoint.
mid = (0.0, 1.4, 0.0)

top_cam = add_camera("PreviewTop", (mid[0], mid[1], 8.0), mid, ortho_scale=4.4)
quart_cam = add_camera(
    "PreviewQuart", (3.4, -2.8, 2.6), (0.0, 1.6, 0.4)
)
# Close-up of just the platform from a 3/4 angle similar to the reference.
plat_cam = add_camera(
    "PreviewPlatform", (1.4, 1.05, 0.95), (0.0, 2.42, 0.05)
)


def render(cam, path):
    scene.camera = cam
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


render(top_cam, "/Users/danielku/mywebsite/blender/table/_preview_top.png")
render(quart_cam, "/Users/danielku/mywebsite/blender/table/_preview_quart.png")
render(plat_cam, "/Users/danielku/mywebsite/blender/table/_preview_platform.png")
print("DONE")
