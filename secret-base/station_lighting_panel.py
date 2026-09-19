"""Live station light controls. Run this text to enable N > Station Lights.

Controls only workshop lamps, excluding every yellow fence-post light.
Baselines and slider values persist in the .blend. Register this text on load.
"""
import bpy

GROUPS = (
    ('ambient', 'Main lighting'),
    ('pillar', 'Pillar'),
    ('floor', 'Circular floor lights'),
    ('sheen', 'Floor sheen'),
    ('desk', 'Desk and monitors'),
    ('accents', 'Rings, hub and accents'),
)
PREFIX = 'station_lighting_'
BASE_POWER = '_station_lighting_power'
BASE_COLOR = '_station_lighting_color'
_guard = False


def lamps(scene):
    collection = bpy.data.collections.get('deck_workshop')
    if collection:
        for obj in collection.all_objects:
            if (obj.type == 'LIGHT' and obj.name in scene.objects
                    and not obj.name.startswith('deckLight_lantern_')):
                yield obj


def group_for(obj):
    name = obj.name
    if 'floor_sheen' in name:
        return 'sheen'
    if 'floor_glow' in name:
        return 'floor'
    if 'shaft' in name or 'vein_spill' in name:
        return 'pillar'
    if 'desk' in name or 'monitor' in name:
        return 'desk'
    if name in ('deckLight_key_b', 'deckLight_fill_b', 'deckLight_rim_b'):
        return 'ambient'
    return 'accents'


def capture(scene, overwrite=False):
    floor = bpy.data.objects.get('deck_floor_b')
    if floor and floor.active_material and floor.active_material.node_tree:
        node = floor.active_material.node_tree.nodes.get('Principled BSDF')
        if node and (overwrite or '_station_floor_sheen_reset' not in scene):
            scene['_station_floor_sheen_reset'] = (0.95 - node.inputs['Roughness'].default_value) / 0.8
    for obj in lamps(scene):
        # A shared data block must never let a control change an excluded lamp.
        if obj.data.users > 1:
            obj.data = obj.data.copy()
        if overwrite or BASE_POWER not in obj:
            obj[BASE_POWER] = obj.data.energy
            obj[BASE_COLOR] = list(obj.data.color)


def apply(scene, context=None):
    if _guard:
        return
    capture(scene)
    master = scene.station_lighting_master
    tint = scene.station_lighting_tint
    for obj in lamps(scene):
        group = group_for(obj)
        strength = getattr(scene, PREFIX + group + '_power')
        color = getattr(scene, PREFIX + group + '_color')
        mix = getattr(scene, PREFIX + group + '_mix')
        obj.data.energy = obj[BASE_POWER] * master * strength
        original = obj[BASE_COLOR]
        base = [((1 - mix) * original[i] + mix * color[i]) * tint[i] for i in range(3)]
        blue = scene.station_lighting_blue
        if blue <= 0.5:
            peak = max(base)
            base = [peak + (channel - peak) * blue * 2 for channel in base]
        else:
            amount = (blue - 0.5) * 2
            base[0] *= 1 - 0.6 * amount
            base[1] *= 1 - 0.3 * amount
        obj.data.color = base
    floor = bpy.data.objects.get('deck_floor_b')
    if floor and floor.active_material and floor.active_material.node_tree:
        node = floor.active_material.node_tree.nodes.get('Principled BSDF')
        if node:
            node.inputs['Roughness'].default_value = 0.95 - 0.8 * scene.station_lighting_sheen
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()


def reset_sliders(scene):
    global _guard
    _guard = True
    try:
        scene.station_lighting_blue = 0.5
        scene.station_lighting_sheen = scene.get('_station_floor_sheen_reset', 0.5875)
        scene.station_lighting_master = 1
        scene.station_lighting_tint = (1, 1, 1)
        for key, _ in GROUPS:
            setattr(scene, PREFIX + key + '_power', 1)
            setattr(scene, PREFIX + key + '_mix', 0)
    finally:
        _guard = False
    apply(scene)


class STATIONLIGHT_OT_reset(bpy.types.Operator):
    bl_idname = 'stationlight.reset'
    bl_label = 'Reset to saved look'
    bl_description = 'Restore captured light colors and brightness; leave fence lights untouched'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        reset_sliders(context.scene)
        return {'FINISHED'}


class STATIONLIGHT_OT_capture(bpy.types.Operator):
    bl_idname = 'stationlight.capture'
    bl_label = 'Use current look as baseline'
    bl_description = 'Make the current lamp settings the new 1x values and reset target'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        capture(context.scene, overwrite=True)
        reset_sliders(context.scene)
        return {'FINISHED'}


class STATIONLIGHT_PT_panel(bpy.types.Panel):
    bl_label = 'Station Lighting'
    bl_idname = 'STATIONLIGHT_PT_panel'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Station Lights'

    def draw(self, context):
        scene, layout = context.scene, self.layout
        layout.label(text='Yellow fence lamps stay unchanged', icon='LOCKED')
        layout.prop(scene, PREFIX + 'blue', slider=True)
        layout.prop(scene, PREFIX + 'sheen', slider=True)
        layout.prop(scene, PREFIX + 'master', slider=True)
        layout.prop(scene, PREFIX + 'tint')
        for key, label in GROUPS:
            box = layout.box()
            box.label(text=label)
            box.prop(scene, PREFIX + key + '_power', text='Brightness', slider=True)
            box.prop(scene, PREFIX + key + '_color', text='Color')
            box.prop(scene, PREFIX + key + '_mix', text='Color override', slider=True)
        layout.label(text='0% keeps original colors; 100% uses Color')
        layout.operator('stationlight.reset', icon='LOOP_BACK')
        layout.operator('stationlight.capture', icon='CHECKMARK')
        layout.label(text='Save the .blend to keep your settings')


CLASSES = (STATIONLIGHT_OT_reset, STATIONLIGHT_OT_capture, STATIONLIGHT_PT_panel)
PROPS = [PREFIX + key for key in ('master', 'tint', 'blue', 'sheen')] + [
    PREFIX + key + suffix for key, _ in GROUPS for suffix in ('_power', '_color', '_mix')
]


def register():
    # Safe to rerun from the Text Editor without duplicate registered classes.
    for cls in reversed(CLASSES):
        old = getattr(bpy.types, cls.__name__, None)
        if old:
            bpy.utils.unregister_class(old)
    for prop in PROPS:
        if hasattr(bpy.types.Scene, prop):
            delattr(bpy.types.Scene, prop)
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    scene_type = bpy.types.Scene
    scene_type.station_lighting_blue = bpy.props.FloatProperty(
        name='Blue tint', subtype='FACTOR', default=0.5, min=0, max=1,
        description='0% neutral white, 50% saved blue-white, 100% deeper blue; excludes fence lamps', update=apply)
    scene_type.station_lighting_sheen = bpy.props.FloatProperty(
        name='Floor sheen', subtype='FACTOR', default=0.5875, min=0, max=1,
        description='From matte to polished reflections on the floor and matching edge', update=apply)
    scene_type.station_lighting_master = bpy.props.FloatProperty(
        name='Overall brightness', default=1, min=0, max=10, soft_max=3,
        description='Brightness multiplier for all station lights except yellow fence lamps', update=apply)
    scene_type.station_lighting_tint = bpy.props.FloatVectorProperty(
        name='Overall tint', subtype='COLOR', size=3, default=(1, 1, 1), min=0, max=1,
        description='White preserves the palette; choose a tint to color all controlled lights', update=apply)
    for key, _ in GROUPS:
        setattr(scene_type, PREFIX + key + '_power', bpy.props.FloatProperty(
            name='Brightness', default=1, min=0, max=10, soft_max=3, update=apply))
        setattr(scene_type, PREFIX + key + '_color', bpy.props.FloatVectorProperty(
            name='Color', subtype='COLOR', size=3, default=(0.52, 0.72, 1.0),
            min=0, max=1, update=apply))
        setattr(scene_type, PREFIX + key + '_mix', bpy.props.FloatProperty(
            name='Color override', subtype='FACTOR', default=0, min=0, max=1,
            description='Blend from the captured colors to the chosen color', update=apply))
    capture(bpy.context.scene)
    apply(bpy.context.scene)


def unregister():
    for cls in reversed(CLASSES):
        old = getattr(bpy.types, cls.__name__, None)
        if old:
            bpy.utils.unregister_class(old)
    for prop in PROPS:
        if hasattr(bpy.types.Scene, prop):
            delattr(bpy.types.Scene, prop)


if __name__ == '__main__':
    register()
