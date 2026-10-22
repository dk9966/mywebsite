"""Compare both reloaded files, then exercise the serialized native drivers.

Compare mesh and stored parent/local transforms. Cached matrix_world values of
excluded archive collections can differ between live and freshly loaded scenes.
"""
import bpy, hashlib
from pathlib import Path

P=Path(__file__).resolve().parent
saved=bpy.data.filepath

def preservation_signature(o):
    return hashlib.sha256(repr((o.parent.name if o.parent else None,
        [list(r) for r in o.matrix_basis],
        [list(r) for r in o.matrix_parent_inverse],
        [tuple(v.co) for v in o.data.vertices],
        [tuple(p.vertices) for p in o.data.polygons])).encode()).hexdigest()

bpy.ops.wm.open_mainfile(filepath=str(P/'before-circular-roof-light.blend'))
preservation_reference={o.name:preservation_signature(o)
                        for o in bpy.context.scene.objects if o.type=='MESH'}
bpy.ops.wm.open_mainfile(filepath=saved)
exec(compile((P/'verify_light.py').read_text(),str(P/'verify_light.py'),'exec'))
print('SAVED_CIRCULAR_ROOF_CHECKS_PASSED',result['passed'],flush=True)
