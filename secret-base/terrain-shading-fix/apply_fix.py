"""Repair cave shading in place while preserving the user's current geometry and rig."""
import bpy, json
from pathlib import Path
from mathutils import Vector
P=Path('/Users/danielku/mywebsite/secret-base/terrain-shading-fix')
s=bpy.context.scene
wall=bpy.data.objects['150 | continuous cave with oblique carved rooms']
if wall.get('Terrain shading repair v1'):
    raise RuntimeError('Terrain shading fix already applied; refusing to reverse normals twice.')
original_mode=bpy.context.object.mode if bpy.context.object else 'OBJECT'
if original_mode!='OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')
# Preserve the latest user state, including edits made during render comparisons.
bpy.ops.wm.save_as_mainfile(filepath=str(P/'before-applying-fix.blend'),copy=True,compress=True)
# The open cave shell had its entire visible side facing away from the cavity.
# Reverse winding only: all vertex positions, faces, sculpt attributes, and modifiers remain.
assert not wall.data.has_custom_normals
wall.data.flip_normals();wall.data.update()
wall['Terrain shading repair v1']='Cavity-facing normals; restrained bump; softer local mist and lower rock bounce.'
changes={}
for o in [wall,bpy.data.objects['Central rock mound | continuous cross-column extrusions']]:
    mat=o.data.materials[0]
    nt=mat.node_tree
    updates={'Weathered broad relief':{'Strength':.16,'Distance':.045},
             'Subtle stone grain':{'Strength':.12,'Distance':.008},
             'Matte charcoal slate':{'Roughness':.90,'Specular IOR Level':.18}}
    for name,sockets in updates.items():
        for socket,value in sockets.items():
            nt.nodes[name].inputs[socket].default_value=value
    changes[mat.name]=updates
mist={}
for mat in bpy.data.materials:
    if not mat.name.startswith('RL mist | '):continue
    scale=.22 if mat.name in ['RL mist | Center','RL mist | Front left'] else .6
    for fc in mat.node_tree.animation_data.drivers:
        fc.driver.expression='('+fc.driver.expression+')*'+str(scale)
    mist[mat.name]=scale
for side in [-1,1]:
    o=bpy.data.objects[f'RL | Cave | lower reflected bounce {side:+d}']
    o.location=(side*6.,-12.,4.)
    target=Vector((side*4.,1.,3.5))
    o.rotation_euler=(target-o.location).to_track_quat('-Z','Y').to_euler()
    o.data.size=10.
    o['Base power (W)']=500.
    o.data.specular_factor=.15
    o['Lighting role']='Wide camera-side rock bounce below the decks; softens shelf shadows while keeping the platform lighting separate.'
s.frame_set(s.frame_current);bpy.context.view_layer.update()
if original_mode!='OBJECT':
    bpy.ops.object.mode_set(mode=original_mode)
notes=bpy.data.texts.get('READ ME - Terrain shading repair') or bpy.data.texts.new('READ ME - Terrain shading repair')
notes.clear();notes.write((P/'README.md').read_text())
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath,compress=True)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'terrain-shading-fixed.blend'),copy=True,compress=True)
result={'saved':bpy.data.filepath,'backup':str(P/'before-applying-fix.blend'),'materials':changes,'local_mist_multipliers':mist,'mode_restored':original_mode}
(P/'applied-settings.json').write_text(json.dumps(result,indent=2))
