"""Render the comparison reference from the scene camera.

Writes, into cave-web/reference/:
  blender-camera.png   final image (compositor bloom + AgX look), the target
  linear-with-haze.exr scene-linear render, no compositor
  linear-no-haze.exr   the same with the mist volumes hidden

Usage: Blender --background SCENE.blend --python render_reference.py -- [WIDTH]
"""
import bpy, os, sys

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reference")
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
scene = bpy.context.scene
if argv:
    width = int(argv[0])
    scale = width / scene.render.resolution_x
    scene.render.resolution_x = width
    scene.render.resolution_y = round(scene.render.resolution_y * scale)
scene.render.resolution_percentage = 100

scene.render.filepath = os.path.join(OUT, "blender-camera.png")
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_depth = "8"
bpy.ops.render.render(write_still=True)

# Raw scene-linear renders (no compositor bloom, no view transform) for
# calibrating the web haze: with every mist volume, and with none of them.
scene.render.use_compositing = False
settings = scene.render.image_settings
settings.file_format = "OPEN_EXR"
settings.color_depth = "32"
settings.color_mode = "RGB"
def volume_only(o):
    if o.type != "MESH" or not o.material_slots:
        return False
    for slot in o.material_slots:
        nodes = slot.material.node_tree.nodes if slot.material and slot.material.node_tree else []
        out = next((n for n in nodes if n.bl_idname == "ShaderNodeOutputMaterial" and n.is_active_output), None)
        if not out or out.inputs["Surface"].is_linked or not out.inputs["Volume"].is_linked:
            return False
    return True


# Every volume, including the viewport-hidden main cave haze.
volumes = [o for o in scene.objects if volume_only(o) and not o.hide_render]
for name, hidden in (("linear-with-haze.exr", False), ("linear-no-haze.exr", True)):
    for o in volumes:
        o.hide_render = hidden
    bpy.ops.render.render()
    bpy.data.images["Render Result"].save_render(os.path.join(OUT, name), scene=scene)
print("REFERENCE_DONE", scene.render.resolution_x, scene.render.resolution_y, len(volumes))
