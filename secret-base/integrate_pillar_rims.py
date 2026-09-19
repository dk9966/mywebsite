"""Extend existing upper pillar shoulders around the deck; preserve lower silhouettes."""
import bpy, math, os
from collections import defaultdict
from mathutils import Vector
ROOT='/Users/danielku/mywebsite/secret-base/'
backup=ROOT+'rock-review/before-integrated-rims.blend'
if not os.path.exists(backup):bpy.ops.wm.save_as_mainfile(filepath=backup,copy=True)
def smooth(t):
    t=max(0,min(1,t));return t*t*(3-2*t)
def baseline(o):
    if o.data.users>1:o.data=o.data.copy()
    attr=o.data.attributes.get('rim_original_position')
    if not attr:
        attr=o.data.attributes.new('rim_original_position','FLOAT_VECTOR','POINT')
        for v,a in zip(o.data.vertices,attr.data):a.vector=v.co
    return [o.matrix_world@Vector(a.vector) for a in attr.data]
report=[]
for key in ['project','about','experience','contact']:
    pillar=bpy.data.objects['island_pillar_'+key]
    coll=bpy.data.collections['deck_'+key]
    floor=next(o for o in coll.objects if o.name.startswith('deck_floor'))
    rim=next(o for o in coll.objects if o.name.startswith('deck_parapet'))
    cx,cy=pillar.matrix_world.translation.xy
    fw=baseline(floor)
    floor_top=max(v.z for v in fw);floor_r=max(math.hypot(v.x-cx,v.y-cy) for v in fw)
    points=baseline(pillar);top=max(v.z for v in points)
    # Preserve all original facets; expand individual horizontal profile levels.
    radii=defaultdict(float)
    for p in points:radii[round(p.z,3)]=max(radii[round(p.z,3)],math.hypot(p.x-cx,p.y-cy))
    target_r=floor_r+.055
    inv=pillar.matrix_world.inverted();modified=0
    for vert,p in zip(pillar.data.vertices,points):
        r=math.hypot(p.x-cx,p.y-cy)
        if p.z>top-1.25 and r>1e-7:
            t=smooth((p.z-(top-1.25))/.95)
            envelope=radii[round(p.z,3)]
            scale=1+t*(target_r/envelope-1)
            p.x=cx+(p.x-cx)*scale;p.y=cy+(p.y-cy)*scale
            nr=r*scale
            # Only the stone perimeter comes above the deck. The inner cap stays below it.
            edge=smooth((nr-(floor_r-.24))/.14)
            vertical=smooth((p.z-(top-.28))/.25)
            p.z+=(floor_top+.025-top)*edge*vertical
            modified+=1
        vert.co=inv@p
    pillar.data.update()
    # Recess the manufactured fascia inside the stone, retaining its top surface.
    finv=floor.matrix_world.inverted()
    for vertex,p in zip(floor.data.vertices,fw):
        depth=floor_top-p.z
        if depth>.025 and math.hypot(p.x-cx,p.y-cy)>floor_r-.14:
            p.x=cx+(p.x-cx)*.90;p.y=cy+(p.y-cy)*.90
        vertex.co=finv@p
    floor.data.update()
    rim.hide_render=True;rim.hide_set(True)
    # Keep rail tops fixed and place the feet directly on the stone shoulder.
    for rail in coll.objects:
        if rail.type!='MESH' or not rail.name.startswith('deck_railing'):continue
        rp=baseline(rail);zmin=min(v.z for v in rp);rinv=rail.matrix_world.inverted()
        for vertex,p in zip(rail.data.vertices,rp):
            if p.z<zmin+.055:
                t=max(0,1-(p.z-zmin)/.055)
                p.z+=(floor_top+.020-zmin)*t
            vertex.co=rinv@p
        rail.data.update()
    pillar['deck_integration']='Original upper shoulder expanded to cover floor fascia; stone perimeter supports railing. Lower body preserved.'
    report.append({'island':key,'modified_vertices':modified,'stone_top':floor_top+.025,'radius':target_r})
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'base.blend')
result={'changes':report,'backup':backup}
