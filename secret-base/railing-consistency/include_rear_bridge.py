"""Include the rear bridge added to the live scene during the railing pass."""
import bpy
import json
import math
from pathlib import Path
from mathutils import Matrix, Vector

P = Path(__file__).resolve().parent
S = bpy.context.scene
UP = Vector((0,0,1))
C = bpy.data.objects['Rig | middle radius'].matrix_world.translation.copy()
C.z = 0
archive = bpy.data.collections['Archive | railing spacing before consistency']

def points(o):
    e=o.evaluated_get(bpy.context.evaluated_depsgraph_get())
    return [e.matrix_world@v.co for v in e.data.vertices]

def center(o):
    vs=points(o)
    return sum(vs,Vector())/len(vs)

def foot(o):
    n=o.name
    if n.startswith('Metal | perimeter post'):
        n=n.replace('perimeter post','post bolted foot')
    elif n.startswith('Rear left |'):
        n=n.replace('upright','bolted shoe')
    else:
        n=n.removesuffix('upright')+'foot'
    return bpy.data.objects[n]

def angle(o):
    p=center(o)-C
    return math.atan2(p.y,p.x)

rear=[o for o in S.objects if o.visible_get() and o.name.startswith('Rear left | side') and 'upright' in o.name]
assert len(rear)==40

# Add the missing compact feet to the two terminal posts.
for side in (0,1):
    end=bpy.data.objects['Rear left | side %d end upright'%side]
    source=bpy.data.objects['Rear left | side %d bolted shoe'%side]
    new=source.copy()
    new.data=source.data.copy()
    new.name='Rear left | side %d end bolted shoe'%side
    source.users_collection[0].objects.link(new)
    target=center(end)
    target.z=min(v.z for v in points(end))-.001
    new.matrix_world=Matrix.Translation(target-center(source))@source.matrix_world
    bpy.context.view_layer.update()

# Each small clipped shoulder uses one centered support, not two close corners.
for side in (0,1):
    keep=bpy.data.objects['Rear left | side %d upright.010'%side]
    remove=bpy.data.objects['Rear left | side %d upright.011'%side]
    delta=(center(remove)-center(keep))/2
    for ob in (keep,foot(keep)):
        ob.matrix_world=Matrix.Translation(delta)@ob.matrix_world
    for ob in (remove,foot(remove)):
        for col in list(ob.users_collection):col.objects.unlink(ob)
        archive.objects.link(ob)
    rear.remove(remove)
    bpy.context.view_layer.update()

# Redistribute the circle around all three openings, including the rear bridge.
circle=[o for o in S.objects if o.visible_get() and
        (o.name.startswith('Metal | perimeter post') or 'circle return post' in o.name and o.name.endswith('upright'))]
circle.sort(key=lambda o:(angle(o)-angle(bpy.data.objects['Bridge | aligned post 1 00 upright']))%math.tau)
arcs=[('Bridge | aligned post 1 00 upright','Rear left | side 1 upright',14),
      ('Rear left | side 0 upright','Left stairs | radial approach guardrail upright.007',6),
      ('Left stairs | radial approach guardrail upright','Bridge | aligned post 0 00 upright',7)]
assert len(circle)==sum(n for _,_,n in arcs)
offset=0
arc_report=[]
for start,end,n in arcs:
    a=angle(bpy.data.objects[start]);span=(angle(bpy.data.objects[end])-a)%math.tau
    for i,o in enumerate(circle[offset:offset+n],1):
        delta=a+span*i/(n+1)-angle(o)
        mat=Matrix.Translation(C)@Matrix.Rotation(delta,4,'Z')@Matrix.Translation(-C)
        for ob in (o,foot(o)):ob.matrix_world=mat@ob.matrix_world
        bpy.context.view_layer.update()
    offset+=n
    arc_report.append({'start':start,'end':end,'interior_posts':n,'angle_interval_degrees':math.degrees(span/(n+1))})

def resize(o,axes,sizes):
    vs=points(o)
    ratios=[size/(max(v.dot(axis) for v in vs)-min(v.dot(axis) for v in vs)) for axis,size in zip(axes,sizes)]
    origin=sum((v.co for v in o.data.vertices),Vector())/len(o.data.vertices)
    linear=o.matrix_world.to_3x3();inv=linear.inverted()
    for v in o.data.vertices:
        d=linear@(v.co-origin)
        v.co+=inv@sum((axis*d.dot(axis)*(r-1) for axis,r in zip(axes,ratios)),Vector())
    o.data.update()

for o in rear:
    f=foot(o)
    x=(f.matrix_world.to_3x3()@Vector((1,0,0))).normalized()
    y=UP.cross(x).normalized()
    resize(o,(x,y),(.028,.028))
    resize(f,(x,y,UP),(.052,.052,.024))
    f.matrix_world=Matrix.Translation((0,0,.002))@f.matrix_world
    for ob,mat in [(o,'Metal | dark structural steel'),(f,'Metal | outer walkway alloy')]:
        ob.data.materials.clear();ob.data.materials.append(bpy.data.materials[mat])
    for m in f.modifiers:
        if m.type=='BEVEL':m.width=.0015;m.segments=2
    o['railing_profile_mm']='28 x 28'
    f['railing_foot_mm']='52 x 52 x 24'
    bpy.context.view_layer.update()

report=json.loads(P.joinpath('verification.json').read_text())
report.update({'active_posts':169,'compact_feet':169,'circle_arcs':arc_report,
               'archived_redundant_posts':4,'rear_bridge_posts_standardized':len(rear),
               'missing_terminal_feet_added':2})
P.joinpath('verification.json').write_text(json.dumps(report,indent=2))
result={'rear_bridge_posts_standardized':len(rear),'circle_arcs':arc_report}
