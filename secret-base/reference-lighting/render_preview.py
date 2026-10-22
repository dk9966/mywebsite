"""Render the saved camera without persisting temporary render settings."""
import bpy
import sys
from pathlib import Path

args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
output = args[0] if args else 'preview.png'
width = int(args[1]) if len(args) > 1 else 1100
samples = int(args[2]) if len(args) > 2 else 32
s = bpy.context.scene
s.render.engine = 'CYCLES'
s.cycles.device = 'CPU'
s.cycles.samples = samples
s.cycles.use_denoising = True
s.render.resolution_y = round(width * s.render.resolution_y / s.render.resolution_x)
s.render.resolution_x = width
s.render.resolution_percentage = 100
s.render.use_border = False
s.render.use_crop_to_border = False
s.render.image_settings.file_format = 'PNG'
s.render.filepath = str(Path(__file__).resolve().parent / output)
bpy.ops.render.render(write_still=True)
