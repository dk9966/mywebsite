"""Apply the cave's view transform to raw reference EXRs (no compositor).
Usage: Blender --background --factory-startup --python exr_to_display.py -- in.exr out.png ..."""
import bpy, sys
args = sys.argv[sys.argv.index("--") + 1:]
scene = bpy.context.scene
scene.display_settings.display_device = "sRGB"
scene.view_settings.view_transform = "AgX"
scene.view_settings.look = "AgX - Medium High Contrast"
scene.view_settings.exposure = 0.25
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGB"
for src, dst in zip(args[::2], args[1::2]):
    image = bpy.data.images.load(src)
    image.save_render(dst, scene=scene)
    print("converted", dst)
