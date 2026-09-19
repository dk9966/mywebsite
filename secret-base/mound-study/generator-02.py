"""Headless central mound study. Reuses the original pillar's watertight mesher.

Blender --background --factory-startup --python build_mound.py -- --iteration 1
No writes to base.blend. All output lives beside this script.
"""
import argparse
import importlib.util
import json
import math
import random
import sys
from pathlib import Path

import bpy
import bmesh
import numpy as np
from mathutils import Vector, noise

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ap = argparse.ArgumentParser()
ap.add_argument('--iteration', type=int, default=1)
ap.add_argument('--final', action='store_true')
args = ap.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
IT = args.iteration
random.seed(28471)
rng = np.random.default_rng(28471)
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'secret-base/base.blend'))
s = bpy.context.scene
source = ROOT / 'meshes/pillars/island_pillar_src/shape.py'
spec = importlib.util.spec_from_file_location('original_pillar_shape', source)
pillar_shape = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pillar_shape)

col = bpy.data.collections.new('Central Mound | connected geology')
s.collection.children.link(col)
rig = bpy.data.collections.new('Mound study | cameras and lighting')
s.collection.children.link(rig)
old = bpy.data.objects['island_pillar_project']
cx, cy = old.matrix_world.translation.xy
floor = next(o for o in bpy.data.collections['deck_project'].objects if o.name.startswith('deck_floor'))
deck_top = max((floor.matrix_world @ v.co).z for v in floor.data.vertices)
rock_top = deck_top - .23
old.hide_render = True
old.hide_set(True)
for o in s.objects:
    if (any(c.name == 'deck_project' for c in o.users_collection) and ('pillar_veins' in o.name or 'vein_spill' in o.name)) or o.name == 'Pillar | fine raised stone project':
        o.hide_render = True
        o.hide_set(True)

# Same angular/height field and exact step-wall construction as shape.py.
# Replace the original persistent rib groups with a wrapped, two-dimensional
# fracture map. Each patch owns many angular samples; patch boundaries migrate
# in height, so extrusions cross the former column divisions without seams.
N, M = 128, 52
theta = np.linspace(0, math.tau, N + 1)
zbottom = -.65
zv = np.linspace(zbottom, rock_top, M + 1)
zv[1:-1] += rng.uniform(-.053, .053, M - 1)
sites = []
for row in range(-1, 9):
    for sector in range(10):
        sites.append((sector * N / 10 + rng.uniform(-4.5, 4.5),
                      row * 7 + rng.uniform(-2.8, 2.8), rng.uniform(-.19, .19)))
outer = np.zeros((N, M))
patch_ids = np.zeros((N, M), dtype=int)
for i in range(N):
    for j in range(M):
        def distance(t):
            dx = abs(i - t[0]) % N
            dx = min(dx, N - dx)
            return (dx / 10) ** 2 + ((j - t[1]) / 5.3) ** 2
        k = min(range(len(sites)), key=lambda k: distance(sites[k]))
        a, h, delta = sites[k]
        z = zbottom + (rock_top - zbottom) * max(0, min(1, h / M))
        # Broad terraced buttress, narrow irregular crown. No hourglass/plinth.
        radius = np.interp(z, [zbottom, 1.3, 2.5, 4.6, rock_top], [1.85, 1.95, 1.87, 1.48, 1.36])
        t = i / N * math.tau
        asym = .09 * math.sin(t + .3) + .06 * math.cos(t * 3 - .8)
        outer[i, j] = round((radius + delta + asym) / .13) * .13
        patch_ids[i, j] = k

# Substantial shoulder shelves and recessed fracture pockets, all parts of the
# same field (not disconnected blocks or column strips).
for start, width, low, high, depth in [
    (67, 17, 5, 45, .41), (90, 13, 0, 37, .57),
    (108, 18, 3, 42, .38), (48, 13, 0, 33, .40),
    (27, 19, 6, 43, .43), (5, 16, 0, 38, .45),
    (80, 8, 17, 31, -.21), (105, 8, 9, 28, -.22),
]:
    for i in range(start, start + width):
        outer[i % N, low:high] += depth
outer = np.round(outer / .065) * .065
# Upper shoulders descend at independent heights around the small crown.
# Their extrusion intervals overlap neighboring 2D patches across columns.
for start, width, low, high, radius in [
    (68, 15, 39, 46, 1.82), (87, 13, 32, 40, 2.16),
    (104, 20, 38, 44, 1.82), (48, 13, 25, 34, 2.28),
    (9, 15, 31, 39, 2.03), (29, 16, 38, 44, 1.94),
]:
    for i in range(start, start + width):
        outer[i % N, low:high] = np.maximum(outer[i % N, low:high], radius)
# Root continues down irregularly; there is no uniform rectangular base skirt.
for i in range(N):
    cut = int(1.5 + 1.4 * math.sin(i*.14) + .9 * math.cos(i*.31))
    if cut > 0:
        outer[i, :cut] = np.minimum(outer[i, :cut], 1.22)
surface = pillar_shape.mesh_field(theta, zv, np.ones(M + 1), np.zeros_like(outer), outer)
tri, raw = surface.arrays()
# Convert the source's Y-up to Blender Z-up and warp each ring to a squared
# outcrop. The same position transform is applied to every shared vertex.
verts = []
for x, z, y in raw:
    r = math.hypot(x, y)
    if r > 1e-7:
        ang = math.atan2(y, x)
        square = 1 / max(abs(math.cos(ang)), abs(math.sin(ang)))
        x *= square
        y *= square
    # Global planar direction at a slight angle to the deck, not camera-facing.
    rot = .21
    xx, yy = x * math.cos(rot) - y * math.sin(rot), x * math.sin(rot) + y * math.cos(rot)
    verts.append((cx + xx, cy + yy, z))
me = bpy.data.meshes.new('Connected mound surface from pillar mesher')
me.from_pydata(verts, [], tri.tolist())
me.update()
ob = bpy.data.objects.new('Central rock mound | continuous cross-column extrusions', me)
col.objects.link(ob)
bm = bmesh.new()
bm.from_mesh(me)
bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
bmesh.ops.dissolve_limit(bm, angle_limit=.0001, verts=list(bm.verts), edges=list(bm.edges), delimit={'NORMAL'})
bm.to_mesh(me)
bm.free()

def stone_material():
    m = bpy.data.materials.new('Mound | dry fractured charcoal basalt')
    m.use_nodes = True
    nt = m.node_tree
    p = nt.nodes.get('Principled BSDF')
    p.inputs['Roughness'].default_value = .89
    p.inputs['Specular IOR Level'].default_value = .24
    tex = nt.nodes.new('ShaderNodeTexCoord')
    broad = nt.nodes.new('ShaderNodeTexNoise')
    broad.inputs['Scale'].default_value = 2.3
    broad.inputs['Detail'].default_value = 3
    nt.links.new(tex.outputs['Object'], broad.inputs['Vector'])
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position = .18
    ramp.color_ramp.elements[0].color = (.009,.012,.016,1)
    ramp.color_ramp.elements[1].position = .84
    ramp.color_ramp.elements[1].color = (.033,.039,.046,1)
    nt.links.new(broad.outputs['Fac'], ramp.inputs[0])
    nt.links.new(ramp.outputs[0], p.inputs['Base Color'])
    cells = nt.nodes.new('ShaderNodeTexVoronoi')
    cells.feature = 'DISTANCE_TO_EDGE'
    cells.inputs['Scale'].default_value = 2.5
    cells.inputs['Randomness'].default_value = .92
    nt.links.new(tex.outputs['Object'], cells.inputs['Vector'])
    cramp = nt.nodes.new('ShaderNodeValToRGB')
    cramp.color_ramp.elements[0].position = .002
    cramp.color_ramp.elements[1].position = .024
    nt.links.new(cells.outputs['Distance'], cramp.inputs[0])
    b = nt.nodes.new('ShaderNodeBump')
    b.inputs['Strength'].default_value = .2
    b.inputs['Distance'].default_value = .048
    nt.links.new(cramp.outputs[0], b.inputs['Height'])
    grain = nt.nodes.new('ShaderNodeTexNoise')
    grain.inputs['Scale'].default_value = 42
    grain.inputs['Detail'].default_value = 2.2
    nt.links.new(tex.outputs['Object'], grain.inputs['Vector'])
    b2 = nt.nodes.new('ShaderNodeBump')
    b2.inputs['Strength'].default_value = .23
    b2.inputs['Distance'].default_value = .028
    nt.links.new(grain.outputs['Fac'], b2.inputs['Height'])
    nt.links.new(b.outputs['Normal'], b2.inputs['Normal'])
    nt.links.new(b2.outputs['Normal'], p.inputs['Normal'])
    return m
me.materials.append(stone_material())
bev = ob.modifiers.new('Small chipped ledge edges', 'BEVEL')
bev.width = .032
bev.segments = 1
bev.limit_method = 'ANGLE'
bev.angle_limit = .4
sub = ob.modifiers.new('Fracture surface tessellation', 'SUBSURF')
sub.subdivision_type = 'SIMPLE'
sub.levels = 2
sub.render_levels = 2
tex = bpy.data.textures.new('Mound | actual small stone chips',type='CLOUDS')
tex.noise_scale = .21
tex.noise_depth = 2
dis = ob.modifiers.new('Real irregular stone faces', 'DISPLACE')
dis.texture = tex
dis.strength = .066
dis.mid_level = .5
ob['source_generator'] = str(source.relative_to(ROOT))
ob['method'] = 'Original mesh_field with a wrapped 2D fracture field; no fixed rib/channel groups.'
ob['seed'] = 28471

def camera(name, offset, target, scale):
    o = bpy.data.objects.new(name, bpy.data.cameras.new(name))
    rig.objects.link(o)
    o.location = Vector((cx,cy,0)) + Vector(offset)
    o.rotation_euler = (Vector(target) - o.location).to_track_quat('-Z','Y').to_euler()
    o.data.type = 'ORTHO'
    o.data.ortho_scale = scale
    o.data.lens = 48
    return o
hero = camera('Mound | reference angle', (-12,-19,11.2), (cx,cy,3.2), 12.2)
detail = camera('Mound | surface detail', (-10,-17,9.2), (cx,cy,3.05), 10.8)
reverse = camera('Mound | reverse inspection', (14,12,10), (cx,cy,2.7), 12.6)
wide = bpy.data.objects['Cave_Composition_Camera']

def area(name, pos, target, power, color, size):
    d = bpy.data.lights.new(name, 'AREA')
    d.energy = power
    d.color = color
    d.shape = 'DISK'
    d.size = size
    o = bpy.data.objects.new(name, d)
    rig.objects.link(o)
    o.location = (cx+pos[0],cy+pos[1],pos[2])
    o.rotation_euler = (Vector((cx+target[0],cy+target[1],target[2]))-o.location).to_track_quat('-Z','Y').to_euler()
    return o
area('Mound | soft overhead key',(-6,-8,13),(0,0,3.5),1900,(.69,.78,1),7)
area('Mound | broad neutral fill',(5,-8,6),(0,0,3.5),1000,(.68,.76,.85),8)
area('Mound | ledge rim',(2,5,11),(0,0,4),2100,(.38,.55,.78),5)
s.world = bpy.data.worlds.new('Mound | charcoal environment')
s.world.use_nodes = True
s.world.node_tree.nodes['Background'].inputs[0].default_value = (.025,.034,.05,1)
s.world.node_tree.nodes['Background'].inputs[1].default_value = .35
s.render.engine = 'CYCLES'
s.cycles.samples = 40 if not args.final else 88
s.cycles.use_denoising = True
s.cycles.device = 'CPU'
s.cycles.max_bounces = 6
s.render.image_settings.file_format = 'PNG'
s.render.film_transparent = False
s.render.resolution_percentage = 100
s.view_settings.view_transform = 'AgX'
s.view_settings.look = 'AgX - Medium High Contrast'
s.view_settings.exposure = .1
s.use_nodes = False
s.render.use_compositing = False

# Persist source and notes inside the new .blend for reproducibility.
for name, content in [('mound_generator.py', Path(__file__).read_text()),
                      ('original_pillar_shape.py', source.read_text())]:
    t = bpy.data.texts.new(name)
    t.write(content)
s['mound_notes'] = 'New central rock mound only. Original base.blend untouched. Reuses original pillar mesher with cross-column fracture regions.'
s.camera = hero
s.render.resolution_x = 1300 if args.final else 1000
s.render.resolution_y = 1400 if args.final else 1080
output = HERE / ('central-platform-rock-mound.blend' if args.final else f'iteration-{IT:02d}.blend')
bpy.ops.wm.save_as_mainfile(filepath=str(output))

# Show the actual central platform and short bridge context, while suppressing
# neighbouring decks in the close-up only. The saved scene keeps all of them.
hidden = {}
for o in s.objects:
    if any(c.name in ['deck_about','deck_contact','deck_experience','contact_antenna','about_holo_table','Pillar_Surface_Relief'] for c in o.users_collection) or o.name in ['island_pillar_about','island_pillar_contact','island_pillar_experience']:
        hidden[o.name] = o.hide_render
        o.hide_render = True
    if o.type == 'MESH' and any(c.name.startswith('bridge_project_') for c in o.users_collection):
        # Keep only bridge pieces near the central rock for a useful close view.
        center = o.matrix_world @ (sum((Vector(p) for p in o.bound_box), Vector()) / 8)
        if (Vector((center.x,center.y))-Vector((cx,cy))).length > 4.2:
            hidden[o.name] = o.hide_render
            o.hide_render = True

def render(cam, name, x, y):
    s.camera = cam
    s.render.resolution_x, s.render.resolution_y = x,y
    s.render.filepath = str(HERE / name)
    bpy.ops.render.render(write_still=True)

render(hero, f'iteration-{IT:02d}-hero.png', s.render.resolution_x, s.render.resolution_y)
for name, val in hidden.items():
    bpy.data.objects[name].hide_render = val
render(wide, f'iteration-{IT:02d}-context.png', 1450 if args.final else 1150, 1000 if args.final else 790)
s.camera = hero
s.render.resolution_x, s.render.resolution_y = (1300,1400)
bpy.ops.wm.save_as_mainfile(filepath=str(output))
audit = pillar_shape.audit(tri, np.array(verts))
audit.update({'iteration':IT,'source':str(source),'cross_column_patch_count':len(sites),
              'angular_samples':N,'height_samples':M,'rock_top':rock_top,'deck_top':deck_top,
              'blend':str(output),'mesh_objects_in_mound':len(col.objects)})
(HERE / f'iteration-{IT:02d}-audit.json').write_text(json.dumps(audit,indent=2))
print('MOUND_RESULT',json.dumps(audit))
