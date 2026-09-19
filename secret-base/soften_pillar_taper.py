"""Broaden the existing upper shaft into a long, gentle shoulder."""
import bpy, math, os, bisect
from collections import defaultdict
from mathutils import Vector
ROOT='/Users/danielku/mywebsite/secret-base/'
backup=ROOT+'rock-review/before-gentle-taper.blend'
if not os.path.exists(backup):bpy.ops.wm.save_as_mainfile(filepath=backup,copy=True)
def baseline(o):
    if o.data.users>1:o.data=o.data.copy()
    a=o.data.attributes.get('gentle_taper_original')
    if a is None:
        a=o.data.attributes.new('gentle_taper_original','FLOAT_VECTOR','POINT')
        for v,item in zip(o.data.vertices,a.data):item.vector=v.co
    return [o.matrix_world@Vector(item.vector) for item in a.data]
def profile(points,cx,cy):
    bins=defaultdict(float)
    for p in points:
        z=round(p.z,3);bins[z]=max(bins[z],math.hypot(p.x-cx,p.y-cy))
    return sorted(bins),bins
def interp(z,zs,rs):
    j=bisect.bisect_left(zs,z)
    if j==0:return rs[zs[0]]
    if j==len(zs):return rs[zs[-1]]
    a,b=zs[j-1],zs[j];t=(z-a)/(b-a)
    return rs[a]*(1-t)+rs[b]*t
result={'pillars':[]}
for key in ['project','about','experience','contact']:
    o=bpy.data.objects['island_pillar_'+key];cx,cy=o.matrix_world.translation.xy
    pts=baseline(o);zs,rs=profile(pts,cx,cy)
    top=max(zs);start=top*.29;end=top-.57
    r0=interp(start,zs,rs);r1=max(rs.values())
    def radius(z):
        old=interp(z,zs,rs)
        if z<=start or z>=end:return old
        t=(z-start)/(end-start)
        desired=r0+(r1-r0)*(t*t*(3-2*t))
        return max(old,desired)
    inv=o.matrix_world.inverted()
    for v,p in zip(o.data.vertices,pts):
        old=interp(p.z,zs,rs);f=radius(p.z)/old if old else 1
        p.x=cx+(p.x-cx)*f;p.y=cy+(p.y-cy)*f;v.co=inv@p
    o.data.update()
    # Carry the luminous inlays with the rock, including the prior rim extension.
    original=o.data.attributes.get('rim_original_position')
    original_pts=[o.matrix_world@Vector(a.vector) for a in original.data] if original else pts
    oz,orr=profile(original_pts,cx,cy)
    for vein in bpy.data.collections['deck_'+key].objects:
        if vein.type!='MESH' or 'pillar_veins' not in vein.name:continue
        vp=baseline(vein);vi=vein.matrix_world.inverted()
        for v,p in zip(vein.data.vertices,vp):
            old=interp(p.z,oz,orr);f=radius(p.z)/old if old else 1
            p.x=cx+(p.x-cx)*f;p.y=cy+(p.y-cy)*f;v.co=vi@p
        vein.data.update()
    result['pillars'].append({'name':key,'transition_start':start,'transition_end':end,'height_unchanged':True})
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'base.blend')
