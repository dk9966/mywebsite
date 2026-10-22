import bpy, json
from pathlib import Path
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2]
result={}
for tag,path in [('approved',ROOT/'secret-base/mound-study/central-platform-rock-mound-balanced.blend'),('assets',ROOT/'reference-cavern/cavern-portfolio.blend')]:
    bpy.ops.wm.open_mainfile(filepath=str(path))
    cols=[]
    for c in bpy.data.collections:
        objects=[o for o in c.objects if not o.hide_render and o.type in {'MESH','CURVE','FONT'}]
        pts=[o.matrix_world@Vector(v) for o in objects for v in o.bound_box]
        if not pts:continue
        bounds=[[min(p[k] for p in pts),max(p[k] for p in pts)] for k in range(3)]
        cols.append({'name':c.name,'objects':len(objects),'bounds':bounds})
    keys=[o for o in bpy.data.objects if o.name.startswith(('deck_floor','island_pillar','NAV |','CAMERA |','Central rock mound'))]
    result[tag]={'scenes':[s.name for s in bpy.data.scenes],'collections':cols,'keys':[{'name':o.name,'location':list(o.matrix_world.translation),'rotation':list(o.rotation_euler),'scale':list(o.scale),'hidden':o.hide_render} for o in keys]}
    if tag=='approved':
        result[tag]['bridges']=[{'name':o.name,'bounds':[list(o.matrix_world@Vector(v)) for v in o.bound_box]} for o in bpy.data.objects if o.type=='MESH' and any(c.name.startswith('bridge_project') for c in o.users_collection) and not o.hide_render][:80]
(Path(__file__).parent/'source-inventory.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result))
