"""Restore a restrained grazing reflection in Blender's station floor.

Run in base.blend. Keeps the circular fixture lights and floor material intact.
Does not save automatically.
"""
import bpy
from mathutils import Vector


def tune_floor_sheen():
    collection = bpy.data.collections['deck_workshop']
    fill = bpy.data.objects['deckLight_fill_b']
    if fill.data.users > 1:
        fill.data = fill.data.copy()
    fill.data.energy = 52.0

    name = 'deckLight_floor_sheen_b'
    lamp = bpy.data.objects.get(name)
    if lamp is None:
        lamp = bpy.data.objects.new(name, bpy.data.lights.new(name, 'AREA'))
        collection.objects.link(lamp)
    elif lamp.type != 'LIGHT':
        raise RuntimeError('Sheen light name is occupied by a non-light object')
    elif lamp.data.users > 1:
        lamp.data = lamp.data.copy()
    lamp.parent = None
    lamp.location = (24.9, -0.8, 8.1)
    target = Vector((21.3, -0.3, 6.87))
    lamp.rotation_euler = (target - lamp.location).to_track_quat('-Z', 'Y').to_euler()
    lamp.scale = (1, 1, 1)
    lamp.data.type = 'AREA'
    lamp.data.shape = 'RECTANGLE'
    lamp.data.size = 3.4
    lamp.data.size_y = 1.2
    lamp.data.energy = 55.0
    lamp.data.color = (0.52, 0.72, 1.0)
    lamp.data.diffuse_factor = 0.25
    lamp.data.specular_factor = 1.0
    lamp.data.use_shadow = True
    lamp.hide_render = False
    lamp.hide_viewport = False
    lamp.hide_set(False)
    bpy.context.view_layer.update()
    return {'fill_watts': fill.data.energy, 'sheen_watts': lamp.data.energy}


if __name__ == '__main__':
    result = tune_floor_sheen()
