"""Bake Blender's view transform into a 3D LUT for the web renderer.

Blender's AgX + look + exposure is an OCIO transform; three.js has no OCIO.
This feeds a grid of scene-linear colours through Blender's own colour
management and stores the display-referred sRGB result, so the browser applies
the identical curve. The input axis is log2-encoded:

  linear = 2 ** (MIN_EV + coord * (MAX_EV - MIN_EV))     coord in [0, 1]

Writes models/cave/view-lut.bin: SIZE^3 RGB uint8, red fastest, then green, blue.
Usage: Blender --background --factory-startup --python gen_view_lut.py
"""
import bpy, os, numpy as np

SIZE, MIN_EV, MAX_EV = 48, -14.0, 10.0
VIEW = dict(view_transform="AgX", look="AgX - Medium High Contrast", exposure=0.25, gamma=1.0)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "models", "cave", "view-lut.bin")

scene = bpy.context.scene
scene.display_settings.display_device = "sRGB"
for key, value in VIEW.items():
    setattr(scene.view_settings, key, value)
scene.view_settings.use_curve_mapping = False

coords = np.linspace(0, 1, SIZE, dtype=np.float32)
linear = 2.0 ** (MIN_EV + coords * (MAX_EV - MIN_EV))
# Exact black has to map to black, not to 2^MIN_EV.
linear[0] = 0.0
r, g, b = np.meshgrid(linear, linear, linear, indexing="xy")  # r varies along columns
# Image layout: width = SIZE*SIZE (red + blue*SIZE), height = SIZE (green).
width, height = SIZE * SIZE, SIZE
pixels = np.zeros((height, width, 4), dtype=np.float32)
for bi in range(SIZE):
    for gi in range(SIZE):
        pixels[gi, bi * SIZE:(bi + 1) * SIZE, 0] = linear
        pixels[gi, bi * SIZE:(bi + 1) * SIZE, 1] = linear[gi]
        pixels[gi, bi * SIZE:(bi + 1) * SIZE, 2] = linear[bi]
pixels[..., 3] = 1
image = bpy.data.images.new("lut-input", width, height, alpha=True, float_buffer=True)
image.colorspace_settings.name = "Linear Rec.709"
image.pixels.foreach_set(pixels.ravel())
tmp = OUT + ".png"
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_depth = "16"
scene.render.image_settings.color_mode = "RGB"
image.save_render(tmp, scene=scene)
out = bpy.data.images.load(tmp)
out.colorspace_settings.name = "Non-Color"
data = np.empty(width * height * 4, dtype=np.float32)
out.pixels.foreach_get(data)
data = data.reshape(height, width, 4)  # Blender rows are bottom-up; row index == gi here
lut = np.zeros((SIZE, SIZE, SIZE, 3), dtype=np.float32)  # [b][g][r]
for bi in range(SIZE):
    lut[bi] = data[:, bi * SIZE:(bi + 1) * SIZE, :3]
np.clip(np.round(lut * 255), 0, 255).astype(np.uint8).tofile(OUT)
os.remove(tmp)
mid = lut[SIZE // 2, SIZE // 2, SIZE // 2]
print("LUT_DONE", OUT, "mid-grey", 2 ** (MIN_EV + 0.5 * (MAX_EV - MIN_EV)), "->", mid)
