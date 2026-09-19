"""Remove neighboring renderable parents from the close-up scene only."""
from pathlib import Path
import bpy

root = Path(__file__).resolve().parent
bpy.context.preferences.filepaths.save_version = 0
scene = bpy.data.scenes['01 Central mound - platform close-up']
for name in ('island_pillar_about','island_pillar_contact','island_pillar_experience'):
    o = scene.objects.get(name)
    if o:
        for c in list(o.users_collection):
            if c.name.startswith('01 Central mound - platform close-up'):
                c.objects.unlink(o)
bpy.context.window.scene = scene
bpy.data.texts['mound_generator.py'].clear()
bpy.data.texts['mound_generator.py'].write((root/'build_mound.py').read_text())
scene.render.filepath = str(root/'final-hero.png')
bpy.ops.render.render(write_still=True,scene=scene.name)
bpy.ops.wm.save_as_mainfile(filepath=str(root/'central-platform-rock-mound.blend'))
print('PRESENTATION_FINALIZED', len(scene.objects))
