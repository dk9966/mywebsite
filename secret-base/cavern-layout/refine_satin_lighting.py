"""Dry-cavern satin finish and cool cinematic lighting; no geometry changes.

Run headlessly from the repository root. The matched layout is a read-only input.
--verify independently reopens both saved files and checks geometry and rock shaders.
"""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent
SOURCE = HERE / 'cavern-matched-islands.blend'
FINAL = HERE / 'cavern-satin-lighting.blend'
parser = argparse.ArgumentParser()
parser.add_argument('--pass', dest='stage', type=int, default=1)
parser.add_argument('--final', action='store_true')
parser.add_argument('--verify', action='store_true')
parser.add_argument('--samples', type=int, default=32)
parser.add_argument('--width', type=int, default=1500)
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])


def geometry_snapshot():
    data_hashes, result = {}, {}
    for obj in bpy.context.scene.objects:
        if obj.type == 'LIGHT':
            continue
        h = hashlib.sha256(np.array(obj.matrix_world, dtype=np.float64).tobytes())
        h.update(str((obj.type, obj.hide_render)).encode())
        if obj.type == 'MESH':
            if obj.data not in data_hashes:
                mh = hashlib.sha256()
                for prop, field, count, dtype in [('vertices', 'co', 3, np.float32), ('loops', 'vertex_index', 1, np.int32), ('polygons', 'material_index', 1, np.int32)]:
                    items = getattr(obj.data, prop)
                    values = np.empty(len(items) * count, dtype=dtype)
                    items.foreach_get(field, values)
                    mh.update(values.tobytes())
                data_hashes[obj.data] = mh.digest()
            h.update(data_hashes[obj.data])
        h.update(str([(m.name, m.type) for m in obj.modifiers]).encode())
        result[obj.name] = h.hexdigest()
    return result


def rock_snapshot():
    materials = bpy.data.objects['Central rock mound | continuous cross-column extrusions'].data.materials
    result = {}
    for material in materials:
        nodes = {}
        for node in material.node_tree.nodes:
            inputs = {}
            for socket in node.inputs:
                if not hasattr(socket, 'default_value'):
                    continue
                value = socket.default_value
                if not isinstance(value, (str, int, float, bool)):
                    try:
                        value = list(value)
                    except TypeError:
                        value = str(value)
                inputs[socket.identifier] = value
            nodes[node.name] = {'type': node.bl_idname, 'inputs': inputs}
        links = sorted((l.from_node.name, l.from_socket.identifier, l.to_node.name, l.to_socket.identifier) for l in material.node_tree.links)
        result[material.name] = {'nodes': nodes, 'links': links}
    return result


bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
bpy.context.preferences.filepaths.save_version = 0
scene = bpy.context.scene
bpy.context.view_layer.update()
before = geometry_snapshot()
rock_before = rock_snapshot()
if args.verify:
    bpy.ops.wm.open_mainfile(filepath=str(FINAL))
    bpy.context.view_layer.update()
    after = geometry_snapshot()
    changed = sorted(k for k in before if before[k] != after.get(k))
    added = sorted(set(after) - set(before))
    report = {
        'source': str(SOURCE), 'output': str(FINAL),
        'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        'output_sha256': hashlib.sha256(FINAL.read_bytes()).hexdigest(),
        'non_light_objects_checked': len(before),
        'changed_geometry_or_transforms': changed, 'added_non_light_objects': added,
        'rock_shaders_unchanged': rock_before == rock_snapshot(),
        'water_added': False,
        'scope': 'Platform and equipment shader finish plus lighting; geometry and terrain retained.',
    }
    report['passed'] = not changed and not added and report['rock_shaders_unchanged']
    (HERE / 'satin-preservation.json').write_text(json.dumps(report, indent=2))
    print('SATIN_VERIFICATION', json.dumps(report), flush=True)
    assert report['passed'], report
    sys.exit(0)

frame = Matrix.Translation((21.299999237, 0, 0)) @ Matrix.Rotation(-math.atan2(12, 19), 4, 'Z')
lighting = bpy.data.collections.new('08 | Dry cavern satin lighting')
scene.collection.children.link(lighting)
changes = {}
material_report = {}


def satin(source, name, roughness, metallic, coat, color=None):
    material = source.copy()
    material.name = name
    for node in material.node_tree.nodes:
        if node.type != 'BSDF_PRINCIPLED':
            continue
        node.inputs['Roughness'].default_value = roughness
        node.inputs['Metallic'].default_value = metallic
        node.inputs['Coat Weight'].default_value = coat
        node.inputs['Coat Roughness'].default_value = .30
        if color:
            node.inputs['Base Color'].default_value = (*color, 1)
    changes[source] = material
    material_report[name] = {'source': source.name, 'roughness': roughness, 'metallic': metallic, 'coat': coat}
    return material


satin(bpy.data.objects['deck_floor_b'].data.materials[0], 'Satin | cool platform paving', .42, .46, .09, (.047, .062, .083))
satin(bpy.data.objects['deck_desk_b'].data.materials[0], 'Satin | graphite trim and equipment', .40, .50, .05, (.052, .069, .095))
satin(bpy.data.objects['deck_desk_metal_b'].data.materials[0], 'Satin | brushed metal details', .34, .65, .04)

# Copy each shared mesh once. Retain instancing and leave the earlier scenes' data alone.
data_copies = {}
restyled = []
for obj in list(scene.objects):
    if obj.type not in {'MESH', 'CURVE', 'FONT'}:
        continue
    if not any(material in changes for material in obj.data.materials):
        continue
    original = obj.data
    if original not in data_copies:
        copy = original.copy()
        for index, material in enumerate(copy.materials):
            if material in changes:
                copy.materials[index] = changes[material]
        data_copies[original] = copy
    obj.data = data_copies[original]
    restyled.append(obj.name)

# Overhangs stay powder-coated so their reflections do not compete with the floors.
roof = bpy.data.objects['deck_desk_b'].data.materials[0].copy()
roof.name = 'Satin | restrained powdercoat roofs'
for node in roof.node_tree.nodes:
    if node.type == 'BSDF_PRINCIPLED':
        node.inputs['Roughness'].default_value = .62
        node.inputs['Metallic'].default_value = .28
        node.inputs['Coat Weight'].default_value = 0
        node.inputs['Base Color'].default_value = (.039, .050, .066, 1)
for name in ['Education | open storage shelter | ceiling', 'About | hangar | ceiling', 'Workshop | portal | ceiling']:
    obj = bpy.data.objects[name]
    obj.data = obj.data.copy()
    obj.data.materials.clear()
    obj.data.materials.append(roof)
material_report[roof.name] = {'roughness': .62, 'metallic': .28, 'coat': 0}


def adjust(name, factor=1, color=None, size=None):
    obj = bpy.data.objects[name]
    obj.data = obj.data.copy()
    obj.data.energy *= factor
    if color:
        obj.data.color = color
    if size is not None and obj.data.type == 'AREA':
        obj.data.size = size


# Reduce frontal wash so the satin highlights have a darker body to sit against.
adjust('Cavern | very soft camera bounce', .52, (.43, .62, .76))
adjust('Rock | central soft grazing', .66, (.38, .57, .70))
adjust('Rock | left support grazing', .66, (.38, .57, .70))
adjust('Rock | right support grazing', .66, (.38, .57, .70))
adjust('Projects | broad overhead', 1.16, (.50, .72, .86), 3.1)
adjust('Contact | operations fill', .70, (.53, .76, .86))
adjust('Education | cool counter wash', .78, (.52, .73, .83))
adjust('About | room soft fill', .70, (.48, .71, .85))
adjust('About | deck and stairs', .75, (.49, .71, .85))
adjust('Chasm | overhead', 1.40, (.46, .71, .86))
adjust('Cavern | distant haze', 1.30, (.37, .64, .77))
adjust('Contact | overhead', 1.14, (.55, .79, .88))
adjust('Education | ceiling', 1.18, (.58, .80, .89))
adjust('About | ceiling', 1.22, (.53, .78, .89))
adjust('Workshop | overhead', 1.15, (.62, .77, .86))
adjust('Workshop | warm task wash.002', .74)
adjust('Workshop | warm floor bounce', .55)
adjust('Workshop | low warm fill', .65)


def area(name, position, target, watts, color, width, depth):
    data = bpy.data.lights.new(name, 'AREA')
    data.energy = watts
    data.volume_factor = .08
    data.color = color
    data.shape = 'RECTANGLE'
    data.size, data.size_y = width, depth
    obj = bpy.data.objects.new(name, data)
    lighting.objects.link(obj)
    obj.location = frame @ Vector(position)
    obj.rotation_euler = (frame @ Vector(target) - obj.location).to_track_quat('-Z', 'Y').to_euler()
    return obj


# Broad ceiling sources create restrained elongated reflections on the dry decks.
area('Satin | Projects soft ceiling reflection', (-.5, 4.2, 11.2), (0, -.2, 6.87), 250, (.54, .79, .91), 4.0, 1.5)
area('Satin | Contact soft ceiling reflection', (-7.4, 5.8, 11.7), (-7.2, 2.9, 8.59), 110, (.52, .81, .91), 2.8, .85)
area('Satin | Education soft ceiling reflection', (-7.4, -1.1, 8.1), (-7.2, -3.1, 6.14), 85, (.55, .80, .88), 3.1, .65)
area('Satin | Work soft ceiling reflection', (-7.2, -2.65, 7.75), (-7.3, -5.0, 5.33), 75, (.55, .79, .87), 3.3, .70)
area('Satin | About soft ceiling reflection', (8.4, .1, 8.12), (8.0, -2.3, 6.02), 130, (.50, .78, .91), 3.0, .75)
area('Satin | Workshop ceiling reflection', (8.4, 4.7, 10.6), (8.0, 3.5, 8.40), 100, (.69, .80, .85), 2.8, .65)
area('Satin | deep dry chasm fill', (0, 6.0, 2.2), (0, -.5, .5), 180, (.24, .52, .69), 5.0, 3.0).data.volume_factor = .35

# Existing haze only: no water surfaces, waterfalls, wet-rock shaders, or new terrain.
scene.world = scene.world.copy()
scene.world.node_tree.nodes['Background'].inputs[1].default_value = .035
atmosphere = bpy.data.objects['Cavern | atmosphere volume']
atmosphere.data = atmosphere.data.copy()
haze = atmosphere.data.materials[0].copy()
haze.name = 'Satin | restrained dry cavern haze'
atmosphere.data.materials[0] = haze
for node in haze.node_tree.nodes:
    if node.type == 'PRINCIPLED_VOLUME':
        node.inputs['Density'].default_value = .0065
scene.view_settings.exposure = .08
scene['finish_revision'] = 'Subtle satin platforms; cool overhead reflections; dry cavern'
scene['central_island_geometry_locked'] = True
scene['center_unchanged'] = False  # Geometry retained; platform finish intentionally updated.
scene['central_material_finish_updated'] = True
scene['water_added'] = False
scene['finish_reference_image'] = str(HERE.parents[1] / 'design-references/misty-abyss/dry-cavern-satin-lighting-reference.png')
bpy.context.view_layer.update()
assert before == geometry_snapshot(), 'Geometry, layout, or camera transforms changed'
assert rock_before == rock_snapshot(), 'The approved rock shaders changed'

tag = 'satin' if args.final else f'satin-preview-{args.stage:02d}'
output = FINAL if args.final else HERE / (tag + '.blend')
source = bpy.data.texts.get('refine_satin_lighting.py') or bpy.data.texts.new('refine_satin_lighting.py')
source.clear()
source.write(Path(__file__).read_text())
scene.camera = bpy.data.objects['Camera | reference composition']
scene.cycles.samples = args.samples
scene.render.resolution_x = args.width
scene.render.resolution_y = round(args.width * 927 / 1696)
scene.render.resolution_percentage = 100
scene.render.filepath = str(HERE / (tag + '-overview.png'))
bpy.ops.wm.save_as_mainfile(filepath=str(output), compress=True)
bpy.ops.render.render(write_still=True)
if args.final:
    for camera, label in [('Camera | Contact and Experiences', 'contact-experiences'), ('Camera | Workshop and About', 'workshop-about')]:
        scene.camera = bpy.data.objects[camera]
        scene.render.resolution_x = scene.render.resolution_y = 1400
        scene.cycles.samples = 64
        scene.render.filepath = str(HERE / (tag + '-' + label + '.png'))
        bpy.ops.render.render(write_still=True)
    scene.camera = bpy.data.objects['Camera | reference composition']
    scene.render.resolution_x = args.width
    scene.render.resolution_y = round(args.width * 927 / 1696)
    scene.cycles.samples = args.samples
    scene.render.filepath = str(HERE / (tag + '-overview.png'))
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(output), compress=True)
audit = {'source': str(SOURCE), 'output': str(output), 'geometry_unchanged': True, 'terrain_shaders_unchanged': True, 'water_added': False, 'materials': material_report, 'restyled_objects': len(restyled), 'non_light_objects_checked': len(before), 'added_lights': [o.name for o in lighting.objects]}
(HERE / (tag + '-audit.json')).write_text(json.dumps(audit, indent=2))
print('SATIN_RESULT', json.dumps(audit), flush=True)
