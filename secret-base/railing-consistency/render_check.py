"""Render inspections in a separate process; never save presentation changes."""
import bpy
import sys
from pathlib import Path
from mathutils import Vector

P = Path(__file__).resolve().parent
label = sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'after'
view_filter = sys.argv[sys.argv.index('--')+2:] if '--' in sys.argv else []
s = bpy.context.scene
s.render.engine = 'CYCLES'
s.cycles.device = 'CPU'
s.cycles.samples = 24
s.cycles.use_denoising = True
s.render.resolution_x = 1200
s.render.resolution_y = 900
s.render.resolution_percentage = 100
s.render.use_border = False
s.render.use_crop_to_border = False
s.render.image_settings.file_format = 'PNG'
s.render.film_transparent = False

# Hide the cave shell for an unobstructed material and attachment inspection.
keep = ['02 | Machined rings and eight recessed grates',
        '03 | Uniform slender steel railings',
        '158 | Connected bridge and railings',
        '166 | Left bridge and right-turn steel stairs',
        '167 | Left platform matching steel railings',
        '170 | Rear-left connected platform']
visible = {o.name for name in keep for o in bpy.data.collections[name].objects if not o.hide_render}
visible.add('Front left | beveled rectangle landing')
for o in s.objects:
    if o.type == 'MESH':
        o.hide_render = o.name not in visible
    elif o.type == 'LIGHT':
        o.hide_render = True

world = bpy.data.worlds.new('Railing inspection studio')
world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = (.16,.20,.25,1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value = .7
s.world = world
camera = bpy.data.objects.new('Railing inspection camera', bpy.data.cameras.new('Railing inspection camera'))
s.collection.objects.link(camera)
camera.data.type = 'ORTHO'
s.camera = camera
light = bpy.data.objects.new('Railing inspection softbox', bpy.data.lights.new('Railing inspection softbox','AREA'))
s.collection.objects.link(light)
light.data.energy = 550
light.data.shape = 'DISK'
light.data.size = 4

views = [
    ('circle-detail', (24.38,-1.72,6.99), (2.3,-3.2,2.0), 2.65),
    ('stairs-detail', (13.72,-.95,4.97), (-1.5,-2.2,1.8), 2.55),
    ('railing-overview', (21.3,0,6.98), (7,-10,9), 9.0),
    ('rear-junction', (20.1,3.5,7.02), (2.5,2.2,2.3), 2.7),
]
for name, pos, offset, scale in views:
    if view_filter and name not in view_filter:
        continue
    if label == 'before' and name != 'circle-detail':
        continue
    target = Vector(pos)
    camera.location = target + Vector(offset)
    camera.rotation_euler = (target-camera.location).to_track_quat('-Z','Y').to_euler()
    camera.data.ortho_scale = scale
    light.location = target + Vector((1,-1,4))
    light.rotation_euler = (target-light.location).to_track_quat('-Z','Y').to_euler()
    s.render.filepath = str(P / (label+'-'+name+'.png'))
    bpy.ops.render.render(write_still=True)
