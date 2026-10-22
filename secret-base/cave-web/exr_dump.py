"""Dump EXRs as raw float32 RGBA (bottom-up rows) for the node comparison tools.
Usage: Blender --background --factory-startup --python exr_dump.py -- a.exr a.f32 ..."""
import bpy, sys, numpy as np
args = sys.argv[sys.argv.index("--") + 1:]
for src, dst in zip(args[::2], args[1::2]):
    image = bpy.data.images.load(src)
    w, h = image.size
    data = np.empty(w * h * 4, dtype=np.float32)
    image.pixels.foreach_get(data)
    data.tofile(dst)
    print("dumped", dst, w, h)
