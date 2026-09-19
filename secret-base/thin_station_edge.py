"""Thin the selected station parapet and extend the fence posts to meet it.

Run in base.blend. Original mesh coordinates are retained for repeatable tuning.
"""
import bpy
from mathutils import Vector

ATTRIBUTE = 'station_edge_original_position'


def original_positions(obj):
    if obj.data.users > 1:
        obj.data = obj.data.copy()
    attr = obj.data.attributes.get(ATTRIBUTE)
    if attr is None:
        attr = obj.data.attributes.new(ATTRIBUTE, 'FLOAT_VECTOR', 'POINT')
        for vertex, item in zip(obj.data.vertices, attr.data):
            item.vector = vertex.co
    return [Vector(item.vector) for item in attr.data]


def thin_station_edge():
    floor = bpy.data.objects['deck_floor_b']
    rim = bpy.data.objects['deck_parapet_b']
    railings = [bpy.data.objects[n] for n in ('deck_railing_b', 'deck_railing_back_b')]
    floor_top = max((floor.matrix_world @ v.co).z for v in floor.data.vertices)
    points = original_positions(rim)
    world = [rim.matrix_world @ p for p in points]
    bottom = min(p.z for p in world)
    old_top = max(p.z for p in world)
    top = floor_top + 0.065
    factor = (top - bottom) / (old_top - bottom)
    inverse = rim.matrix_world.inverted()
    for vertex, point in zip(rim.data.vertices, world):
        point.z = bottom + (point.z - bottom) * factor
        vertex.co = inverse @ point
    rim.data.update()
    # Use the same finish so the floor and its edge do not form contrasting bands.
    rim.data.materials.clear()
    for material in floor.data.materials:
        rim.data.materials.append(material)

    counts = {}
    for obj in railings:
        points = [obj.matrix_world @ p for p in original_positions(obj)]
        post_bottom = min(p.z for p in points)
        target = bottom + (post_bottom - bottom) * factor
        inverse = obj.matrix_world.inverted()
        moved = 0
        for vertex, point in zip(obj.data.vertices, points):
            # Only post feet are this low; rail heights and lamp tops stay fixed.
            if point.z < post_bottom + 0.001:
                point.z = target
                moved += 1
            vertex.co = inverse @ point
        obj.data.update()
        counts[obj.name] = moved
    bpy.context.view_layer.update()
    return {'old_height': old_top - bottom, 'new_height': top - bottom,
            'floor_top': floor_top, 'rim_top': top, 'extended_post_vertices': counts}


if __name__ == '__main__':
    result = thin_station_edge()
