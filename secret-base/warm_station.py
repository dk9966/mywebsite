"""Apply bluish-white station lighting, yellow lanterns and a satin metal floor.

Run in base.blend; saving is explicit. Floor material is isolated from the rock.
"""
import bpy


def warm_station():
    # One consistent bluish-white palette, with yellow reserved for fence lamps.
    colors = {obj.name: (0.52, 0.72, 1.0)
              for obj in bpy.data.collections['deck_workshop'].all_objects
              if obj.type == 'LIGHT' and not obj.name.startswith('deckLight_lantern_')}
    changed = []
    for obj in bpy.data.objects:
        if obj.type != 'LIGHT':
            continue
        color = ((1.0, 0.62, 0.22) if obj.name.startswith('deckLight_lantern_')
                 else colors.get(obj.name))
        if color is None:
            continue
        if obj.data.users > 1:
            obj.data = obj.data.copy()
        obj.data.color = color
        changed.append(obj.name)
    bpy.data.objects['deckLight_floor_sheen_b'].data.energy = 55.0

    # Restore the visible bulbs as well as the light they cast.
    warm = bpy.data.materials['lampWarm']
    node = warm.node_tree.nodes.get('Principled BSDF')
    node.inputs['Emission Color'].default_value = (1.0, 0.62, 0.22, 1.0)
    node.inputs['Emission Strength'].default_value = 3.0
    for obj in bpy.data.objects:
        if obj.type == 'MESH' and obj.name.startswith('deck_lantern_glass'):
            for slot in obj.material_slots:
                slot.material = warm

    floor = bpy.data.objects['deck_floor_b']
    name = 'stationFloorSatin'
    material = bpy.data.materials.get(name)
    if material is None:
        material = floor.data.materials[0].copy()
        material.name = name
    node = material.node_tree.nodes.get('Principled BSDF')
    node.inputs['Base Color'].default_value = (0.058, 0.074, 0.105, 1.0)
    node.inputs['Roughness'].default_value = 0.48
    node.inputs['Metallic'].default_value = 0.35
    floor.data.materials[0] = material
    bpy.context.view_layer.update()
    return {'lights': changed, 'floor_material': material.name,
            'roughness': 0.48, 'metallic': 0.35}


if __name__ == '__main__':
    result = warm_station()
