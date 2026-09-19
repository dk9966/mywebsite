"""Sync the replacement pillar and circular floor lights from stationLights.tsx.

Run in the open base.blend. Other Blender lighting, materials and geometry stay
authored in Blender. This script does not save the file automatically.
"""
import json
import math
import re
from pathlib import Path

import bpy
from mathutils import Vector


def sync_station_lights():
    root = Path(__file__).resolve().parent
    source = (root / "components/scene/stationLights.tsx").read_text()
    collection = bpy.data.collections.get("deck_workshop")
    if collection is None:
        raise RuntimeError("Open the station scene with deck_workshop first")

    # Restrict synchronization to the light groups replaced in the web scene.
    specs = []
    for kind, name, args in re.findall(
        r'(point|area)\("((?:shaft_|floor_glow_)[^"]+)", (.*?)\),', source
    ):
        specs.append((kind, name, json.loads("[" + args + "]")))
    if len(specs) != 7:
        raise RuntimeError("Expected three pillar areas and four floor points")

    desired = {"deckLight_" + name + "_b" for _, name, _ in specs}
    removed = []
    for obj in list(collection.objects):
        if (obj.type == 'LIGHT' and obj.name.endswith('_b')
                and obj.name.startswith(("deckLight_shaft_", "deckLight_graze_", "deckLight_brazier_"))
                and obj.name not in desired):
            removed.append(obj.name)
            bpy.data.objects.remove(obj, do_unlink=True)

    def blender_vector(xyz):
        # Inverse of glTF's Blender XYZ -> X, Z, -Y conversion.
        return Vector((xyz[0], -xyz[2], xyz[1]))

    updated = []
    for kind, name, args in specs:
        object_name = "deckLight_" + name + "_b"
        light_type = 'POINT' if kind == 'point' else 'AREA'
        obj = bpy.data.objects.get(object_name)
        if obj is None:
            data = bpy.data.lights.new(object_name, light_type)
            obj = bpy.data.objects.new(object_name, data)
            collection.objects.link(obj)
        elif obj.type != 'LIGHT':
            raise RuntimeError("Name occupied by non-light: " + object_name)
        elif obj.data.users > 1:
            obj.data = obj.data.copy()
        obj.data.type = light_type
        obj.parent = None
        obj.scale = (1, 1, 1)
        obj.location = blender_vector(args[0])
        if kind == 'point':
            _, color, intensity = args
            obj.data.energy = intensity * 4 * math.pi
            obj.data.shadow_soft_size = 0.22
            obj.data.use_shadow = False
        else:
            _, forward, color, width, intensity, height = args
            obj.rotation_euler = blender_vector(forward).to_track_quat('-Z', 'Y').to_euler()
            obj.data.shape = 'RECTANGLE'
            obj.data.size = width
            obj.data.size_y = height
            obj.data.energy = intensity * width * height * math.pi
            obj.data.use_shadow = True
        # Blender uses one bluish-white palette outside the yellow fence lamps.
        obj.data.color = (0.52, 0.72, 1.0)
        obj.hide_render = False
        obj.hide_viewport = False
        obj.hide_set(False)
        obj['station_light_source'] = 'components/scene/stationLights.tsx'
        updated.append(object_name)
    bpy.context.view_layer.update()
    return {'removed': removed, 'updated': updated}


if __name__ == '__main__':
    result = sync_station_lights()
