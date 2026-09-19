"""Match the two station structures to the 5174 rig; preserve all desk/prop meshes.

Run in the open base.blend. Saving/exporting is explicit. Safe to rerun.
"""
import json
import math
import re
from pathlib import Path
import bpy
from mathutils import Vector, Matrix


def match_station_lighting():
    root = Path(__file__).resolve().parent
    source = (root / 'components/scene/stationLights.tsx').read_text()
    project = bpy.data.objects['island_pillar_project']
    experience = bpy.data.objects['island_pillar_experience']
    bpy.context.view_layer.update()
    origin = project.matrix_world.translation.copy()
    target = experience.matrix_world.translation.copy()
    scale = experience.dimensions.x / project.dimensions.x
    shaft_scale = experience.dimensions.z / project.dimensions.z
    def top(ob):
        return max((ob.matrix_world @ Vector(c)).z for c in ob.bound_box)
    floor = top(bpy.data.objects['deck_floor_b'])
    other_floor = top(bpy.data.objects['deck_floor_experience'])
    def vec(v): return Vector((v[0], -v[2], v[1]))
    gains = {'rune': .3, 'shaft': 1.6, 'lantern': .4, 'key': .2,
             'fill': .2, 'rim': 1.4, 'floor': 1}
    updated = []
    for kind, name, args in re.findall(r'(point|area)\("([^"]+)", (.*?)\),', source):
        if not re.match(r'^(rune_|shaft_|floor_glow_|key$|fill$|rim$)', name):
            continue
        args = json.loads('[' + args + ']')
        for suffix, host, coll in [('b', project, 'deck_project'), ('experience', experience, 'deck_experience')]:
            obj_name = 'deckLight_' + name + '_' + suffix
            ob = bpy.data.objects.get(obj_name)
            if ob is None:
                data = bpy.data.lights.new(obj_name, 'POINT' if kind == 'point' else 'AREA')
                ob = bpy.data.objects.new(obj_name, data)
                bpy.data.collections[coll].objects.link(ob)
            elif ob.data.users > 1: ob.data = ob.data.copy()
            p = vec(args[0])
            ratio = scale if suffix == 'experience' else 1
            if suffix == 'experience':
                p.x = target.x + (p.x-origin.x)*scale
                p.y = target.y + (p.y-origin.y)*scale
                p.z = p.z*shaft_scale if name.startswith('shaft_') else other_floor+(p.z-floor)*scale
            ob.parent = host
            ob.matrix_world = Matrix.Translation(p)
            ob.data.type = 'POINT' if kind == 'point' else 'AREA'
            data = ob.data
            gain = gains[name.split('_')[0]]
            if kind == 'point':
                color, intensity = args[1:]
                data.energy = intensity*gain*4*math.pi*ratio*ratio
                data.shadow_soft_size = .22*ratio
            else:
                forward, color, width, intensity, *height = args[1:]
                height = height[0] if height else width
                ob.matrix_world = Matrix.Translation(p) @ vec(forward).to_track_quat('-Z', 'Y').to_matrix().to_4x4()
                data.shape = 'RECTANGLE'
                data.size, data.size_y = width*ratio, height*ratio
                data.energy = intensity*gain*width*height*math.pi*ratio*ratio
            # EEVEE needs a less saturated source to reproduce the pale blue
            # appearance of the 5174 AgX/bloom chain (visual reference match).
            data.color = (.48, .69, 1)
            data.energy *= max(color)
            if name.startswith('shaft_'): data.energy *= 1.6
            if name in ('key', 'fill'): data.energy *= 1.3
            # WebGL rectangle lamps do not cast shadows; keep the same soft
            # coverage instead of losing entire faces behind the deck rim.
            data.use_shadow = False
            ob.hide_render = False
            ob.hide_viewport = False
            ob.hide_set(False)
            updated.append(obj_name)

    # Existing lantern meshes are already fitted to the narrower Experience rim.
    # Their light origins were left near world zero by the bridge migration.
    for ob in bpy.data.objects:
        if ob.type != 'LIGHT' or not re.match(r'^(experience_lantern_|bridge_lantern_).*_light$', ob.name): continue
        glass = bpy.data.objects.get(ob.name.removesuffix('_light')+'_glass')
        if glass is None: continue
        center = sum((glass.matrix_world @ Vector(c) for c in glass.bound_box), Vector())/8
        ob.matrix_world = Matrix.Translation(center)
        if ob.data.users > 1: ob.data = ob.data.copy()
        ob.data.color = (1, .6, .28)
        ob.data.energy = .557*.4*4*math.pi*scale*scale
        ob.data.shadow_soft_size = .09
        updated.append(ob.name)

    # Copy only the missing floor light fixtures; no hub, desk or machinery.
    transform = Matrix.Translation(Vector((target.x, target.y, other_floor))) @ Matrix.Diagonal((scale, scale, scale, 1)) @ Matrix.Translation(Vector((-origin.x, -origin.y, -floor)))
    for name in ['deck_braziers_b', 'deck_brazier_flames_b']:
        destination = name.removesuffix('_b')+'_experience'
        if bpy.data.objects.get(destination): continue
        src = bpy.data.objects[name]
        ob = src.copy(); ob.data = src.data.copy(); ob.name = destination
        bpy.data.collections['deck_experience'].objects.link(ob)
        ob.parent = experience
        ob.matrix_world = transform @ src.matrix_world

    # Architectural emitters use the same HDR peak and emission strength in both renderers.
    materials = {slot.material for host in (project, experience) for ob in [host, *host.children_recursive]
                 if ob.type == 'MESH' and not ob.name.startswith('deck_desk') for slot in ob.material_slots if slot.material}
    for material in materials:
        if not material.use_nodes or material.name == 'lampWarm': continue
        node = material.node_tree.nodes.get('Principled BSDF')
        if node is None: continue
        emission = node.inputs['Emission Color']
        peak = max(emission.default_value[:3])
        if peak and node.inputs['Emission Strength'].default_value:
            emission.default_value = (.52*peak, .78*peak, peak, 1)
    # Retire the old supplementary washes that have no counterpart on 5174.
    for ob in bpy.data.objects:
        if ob.type == 'LIGHT' and re.match(r'^deckLight_(floor_sheen|vein_spill_\d+)_(b|experience)$', ob.name):
            ob.hide_render = True
            ob.hide_set(True)
    bpy.context.view_layer.update()
    return {'updated_lights': updated, 'scale': scale, 'floor_heights': [floor, other_floor]}


if __name__ == '__main__':
    result = match_station_lighting()
