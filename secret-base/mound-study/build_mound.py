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
bpy.context.preferences.filepaths.save_version = 0
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

# Medium-sized connected fracture plates: span 4-12 underlying columns and
# terminate independently. This supplies the scale between buttresses/chips.
for k in range(64):
    a = int(rng.integers(0, N))
    width = int(rng.integers(4, 13))
    j = int(rng.integers(3, M-3))
    height = int(rng.integers(5, 12))
    change = float(rng.choice([-.21, -.145, .13, .195]))
    for i in range(a, a + width):
        outer[i % N, j:min(M,j+height)] += change
# Deliberate upper cap hierarchy, with fewer tiny notches on the skyline.
for start,width,low,high,depth in [(71,9,44,M,-.23),(86,8,46,M,-.33),
                                  (100,8,42,48,-.2),(57,10,24,34,-.24),
                                  (75,10,13,25,-.22),(94,7,4,17,-.25)]:
    for i in range(start,start+width):
        outer[i % N,low:high] += depth
# Unequal shoulder terminations define the outer silhouette, independently of
# the connected core. No broad block continues at full width to the deck.
for i in range(40,59):
    outer[i,30:40] = np.minimum(outer[i,30:40], 1.64)
    outer[i,40:] = np.minimum(outer[i,40:], 1.29)
    outer[i,:30] = np.minimum(outer[i,:30], 2.16)
for i in range(103,122):
    outer[i,35:45] = np.minimum(outer[i,35:45], 1.8)
    outer[i,45:] = np.minimum(outer[i,45:], 1.32)
    outer[i,:35] = np.minimum(outer[i,:35], 2.13)
outer = np.round(outer/.065)*.065

# A four-cell saddle can make two raised regions touch along only one edge.
# Bridge its shallower side by the minimum required depth, so the source
# mesher emits a manifold solid and every apparent connection has volume.
saddle_fixes = 0
for _ in range(12):
    fixes = 0
    for i in range(N):
        k = (i+1)%N
        for j in range(M-1):
            a,b,c,d = outer[i,j],outer[k,j],outer[i,j+1],outer[k,j+1]
            if min(a,d) > max(b,c) + 1e-7:
                if b >= c: outer[k,j] = min(a,d)
                else: outer[i,j+1] = min(a,d)
                fixes += 1
            elif min(b,c) > max(a,d) + 1e-7:
                if a >= d: outer[i,j] = min(b,c)
                else: outer[k,j+1] = min(b,c)
                fixes += 1
    saddle_fixes += fixes
    if not fixes: break
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
# Uniform sampling prevents long fan triangles from stretching stone detail.
rem = ob.modifiers.new('Uniform closed stone surface', 'REMESH')
rem.mode = 'VOXEL'
rem.voxel_size = .038
rem.use_smooth_shade = False
rem.use_remove_disconnected = False
tex = bpy.data.textures.new('Mound | actual small stone chips',type='CLOUDS')
tex.noise_scale = .28
tex.noise_depth = 2
dis = ob.modifiers.new('Real irregular stone faces', 'DISPLACE')
dis.texture = tex
dis.strength = .053
dis.mid_level = .5
dec = ob.modifiers.new('Angular fracture planes', 'DECIMATE')
dec.ratio = .33
dec.use_collapse_triangulate = True
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
s.render.resolution_x = 1600 if args.final else 1000
s.render.resolution_y = 1740 if args.final else 1080
output = HERE / ('central-platform-rock-mound.blend' if args.final else f'iteration-{IT:02d}.blend')
tag = 'final' if args.final else f'iteration-{IT:02d}'
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
    bpy.ops.render.render(write_still=True,scene=s.name)

def visible_members(collection):
    if collection.hide_render:
        return set()
    result = {o for o in collection.objects if not o.hide_render}
    for child in collection.children:
        result.update(visible_members(child))
    return result

hero_members = visible_members(s.collection)
render(hero, f'{tag}-hero.png', s.render.resolution_x, s.render.resolution_y)
for name, val in hidden.items():
    bpy.data.objects[name].hide_render = val
render(wide, f'{tag}-context.png', 1800 if args.final else 1150, 1230 if args.final else 790)
audit = pillar_shape.audit(tri, np.array(verts))
audit.update({'iteration':IT,'source':str(source),'cross_column_patch_count':len(sites),'saddle_fixes':saddle_fixes,
              'angular_samples':N,'height_samples':M,'rock_top':rock_top,'deck_top':deck_top,
              'blend':str(output),'mesh_objects_in_mound':len(col.objects)})

if args.final:
    # A separate linked scene makes the saved close-up identical to its render,
    # without globally hiding objects needed by the full-layout scene.
    full_scene = s
    full_scene.name = '02 Full layout - new central terrain'
    def presentation_scene(name, members, cam):
        sc = bpy.data.scenes.new(name)
        members = set(members)
        for o in list(members):
            parent = o.parent
            while parent:
                # Referenced parents still provide transforms without scene
                # membership. Only link non-rendering ancestors, otherwise a
                # bridge can accidentally bring a neighboring pillar back.
                if parent.hide_render or parent.type != 'MESH':
                    members.add(parent)
                parent = parent.parent
        objects_col = bpy.data.collections.new(name + ' | objects')
        sc.collection.children.link(objects_col)
        for o in members:
            objects_col.objects.link(o)
        sc.camera = cam
        sc.world = full_scene.world
        sc.render.engine = 'CYCLES'
        sc.cycles.samples = 88
        sc.cycles.max_bounces = 6
        sc.cycles.use_denoising = True
        sc.render.resolution_percentage = 100
        sc.render.resolution_x, sc.render.resolution_y = 1600,1740
        sc.render.image_settings.file_format = 'PNG'
        sc.render.use_compositing = False
        sc.view_settings.view_transform = 'AgX'
        sc.view_settings.look = 'AgX - Medium High Contrast'
        sc.view_settings.exposure = .1
        return sc

    hero_scene = presentation_scene('01 Central mound - platform close-up', hero_members, hero)
    rockcam = camera('Mound | rock only',(-12,-19,11.8),(cx,cy,3),9.5)
    rock_members = {ob,rockcam,reverse} | {o for o in hero_members if o.type=='LIGHT'}
    rock_scene = presentation_scene('03 Rock only - geometry inspection',rock_members,rockcam)
    rock_scene.view_settings.exposure = .6
    s = rock_scene
    render(rockcam, 'final-rock-only.png',1500,1500)
    render(reverse, 'final-reverse.png',1500,1500)
    rock_scene.camera = rockcam
    rock_scene.render.filepath = str(HERE/'final-rock-only.png')

    # Verify the saved presentation scene, rather than only the temporary view.
    s = hero_scene
    render(hero, 'final-hero.png',1600,1740)
    bpy.context.window.scene = hero_scene
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    evaluated = ob.evaluated_get(dg)
    ev = evaluated.to_mesh()
    ev.calc_loop_triangles()
    eval_tri = np.array([t.vertices[:] for t in ev.loop_triangles])
    eval_pos = np.array([v.co[:] for v in ev.vertices])
    audit['finished_mesh'] = pillar_shape.audit(eval_tri,eval_pos)
    bm = bmesh.new()
    bm.from_mesh(ev)
    unvisited = set(bm.verts)
    counts = []
    while unvisited:
        stack = [unvisited.pop()]
        size = 0
        while stack:
            v = stack.pop()
            size += 1
            for edge in v.link_edges:
                other = edge.other_vert(v)
                if other in unvisited:
                    unvisited.remove(other)
                    stack.append(other)
        counts.append(size)
    audit['finished_mesh']['connected_components'] = len(counts)
    audit['finished_mesh']['component_vertex_counts'] = sorted(counts,reverse=True)
    bm.free()
    evaluated.to_mesh_clear()
    assert audit['boundary'] == 0 and audit['nonmanifold'] == 0, audit
    assert audit['finished_mesh']['boundary'] == 0, audit
    assert audit['finished_mesh']['nonmanifold'] == 0, audit
    assert len(counts) == 1, audit
    bpy.ops.file.pack_all()
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                area.spaces.active.region_3d.view_perspective = 'CAMERA'
    for o in bpy.context.selected_objects:
        o.select_set(False)
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    audit['scenes'] = [sc.name for sc in bpy.data.scenes]
else:
    s.camera = hero
    s.render.resolution_x, s.render.resolution_y = (1300,1400)

bpy.ops.wm.save_as_mainfile(filepath=str(output))
(HERE / f'{tag}-audit.json').write_text(json.dumps(audit,indent=2))
print('MOUND_RESULT',json.dumps(audit))
