"""Render the refined rear workshop wall without changing the live camera."""
import bpy, argparse, sys
from mathutils import Vector
from pathlib import Path

P=Path(__file__).resolve().parent
parser=argparse.ArgumentParser()
parser.add_argument('--close-bay',action='store_true')
parser.add_argument('--output',default='refined-supports-detail.png')
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
S=bpy.context.scene
wall=bpy.data.objects['Lower | octagon rear bay 1']
wall2=bpy.data.objects['Lower | octagon rear bay 2']
vs=[wall.matrix_world@v.co for v in wall.data.vertices]
a,b,c,d=vs[:4]
t=(b-a).normalized();u=(d-a).normalized();n=(a-vs[4]).normalized()
mid1=(a+b+c+d)/4
mid2=sum((wall2.matrix_world@v.co for v in list(wall2.data.vertices)[:4]),Vector())/4
target=(mid1+mid2)/2-u*.08
if args.close_bay:target=mid1-u*.02
data=bpy.data.cameras.new('Support detail inspection')
cam=bpy.data.objects.new(data.name,data);S.collection.objects.link(cam)
cam.location=target+n*6.8+t*.65+u*.26
cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
data.type='ORTHO';data.ortho_scale=5.35;S.camera=cam
if args.close_bay:data.ortho_scale=3.2
S.render.engine='CYCLES';S.cycles.samples=32;S.cycles.use_denoising=True
S.cycles.device='CPU'
S.render.resolution_x=1400;S.render.resolution_y=850;S.render.resolution_percentage=100
if args.close_bay:S.render.resolution_x=1100;S.render.resolution_y=1000
S.render.use_border=False
S.render.image_settings.file_format='PNG'
S.render.filepath=str(P/args.output)
bpy.ops.render.render(write_still=True)
