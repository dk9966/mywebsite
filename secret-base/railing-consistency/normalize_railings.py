"""Unify active guardrails in the live scene, preserving their native controls."""
import bpy
import hashlib
import json
import math
from pathlib import Path
from mathutils import Matrix, Vector

P = Path(__file__).resolve().parent
S = bpy.context.scene
UP = Vector((0, 0, 1))
CENTER = bpy.data.objects['Rig | middle radius'].matrix_world.translation.copy()
CENTER.z = 0
ALLOY = bpy.data.materials['Metal | outer walkway alloy']
STEEL = bpy.data.materials['Metal | dark structural steel']

def signature(o):
    h = hashlib.sha256()
    h.update(str([list(r) for r in o.matrix_world]).encode())
    h.update(str((o.hide_render, o.hide_get(), [c.name for c in o.users_collection])).encode())
    if o.type == 'MESH':
        h.update(str([tuple(v.co) for v in o.data.vertices]).encode())
        h.update(str([tuple(f.vertices) for f in o.data.polygons]).encode())
        h.update(str([m.name if m else None for m in o.data.materials]).encode())
    return h.hexdigest()

def vertices(o):
    e = o.evaluated_get(bpy.context.evaluated_depsgraph_get())
    return [e.matrix_world @ v.co for v in e.data.vertices]

def center(o):
    vs = vertices(o)
    return sum(vs, Vector()) / len(vs)

def ispost(o):
    return (o.name.startswith('Metal | perimeter post') or
            (o.name.startswith(('Bridge | aligned ', 'Lower | aligned perimeter post', 'Front left | perimeter post')) and o.name.endswith(' upright')) or
            (o.name.startswith('Left stairs | ') and 'guardrail upright' in o.name))

def foot_for(o):
    n = o.name
    if n.startswith('Metal | perimeter post'):
        n = n.replace('perimeter post', 'post bolted foot')
    elif 'bolted guardrail upright' in n:
        n = n.replace('bolted guardrail upright', 'guardrail mounting shoe')
    elif 'radial approach guardrail upright' in n:
        n = n.replace('radial approach guardrail upright', 'radial approach guardrail shoe')
    else:
        n = n.removesuffix('upright') + 'foot'
    return bpy.data.objects[n]

posts = [o for o in S.objects if o.type == 'MESH' and o.visible_get() and ispost(o)]
assert len(posts) == 133, len(posts)
before = {o.name: signature(o) for o in S.objects}
changed = set()

archive = bpy.data.collections.new('Archive | railing spacing before consistency')
S.collection.children.link(archive)
archive.hide_render = True
archive.hide_viewport = True

def archive_pair(o):
    for ob in (o, foot_for(o)):
        for col in list(ob.users_collection):
            col.objects.unlink(ob)
        archive.objects.link(ob)
        changed.add(ob.name)
    posts.remove(o)

def move_pair(o, delta):
    for ob in (o, foot_for(o)):
        ob.matrix_world = Matrix.Translation(delta) @ ob.matrix_world
        changed.add(ob.name)
    bpy.context.view_layer.update()

def angle(o):
    p = center(o) - CENTER
    return math.atan2(p.y, p.x)

def rotate_pair(o, delta):
    rotation = Matrix.Translation(CENTER) @ Matrix.Rotation(delta, 4, 'Z') @ Matrix.Translation(-CENTER)
    for ob in (o, foot_for(o)):
        ob.matrix_world = rotation @ ob.matrix_world
        changed.add(ob.name)
    bpy.context.view_layer.update()

# One shared support on the short stair landing return replaces the close pair.
landing = bpy.data.objects['Left stairs | bolted guardrail upright.025']
redundant = bpy.data.objects['Left stairs | radial approach guardrail upright.014']
move_pair(landing, (center(redundant) - center(landing)) / 2)
archive_pair(redundant)

# Remove the redundant support where the new bridge return meets the old circle.
archive_pair(bpy.data.objects['Metal | perimeter post.030'])
circle = [o for o in posts if o.name.startswith('Metal | perimeter post') or 'circle return post' in o.name]
arc_reports = []
for start_name, end_name in [
    ('Bridge | aligned post 1 00 upright', 'Left stairs | radial approach guardrail upright.007'),
    ('Left stairs | radial approach guardrail upright', 'Bridge | aligned post 0 00 upright'),
]:
    a = angle(bpy.data.objects[start_name])
    span = (angle(bpy.data.objects[end_name]) - a) % math.tau
    members = sorted([o for o in circle if 1e-4 < (angle(o)-a) % math.tau < span-1e-4],
                     key=lambda o: (angle(o)-a) % math.tau)
    for i, o in enumerate(members, 1):
        rotate_pair(o, a + span*i/(len(members)+1) - angle(o))
    arc_reports.append({'start': start_name, 'end': end_name, 'interior_posts': len(members),
                        'angle_interval_degrees': math.degrees(span/(len(members)+1))})
assert sum(x['interior_posts'] for x in arc_reports) == len(circle)

# Redistribute the short bridge side so its last bay is not squeezed at the apron.
bridge = [bpy.data.objects['Bridge | aligned post 1 %02d upright' % i] for i in range(4)]
a, b = center(bridge[0]), center(bridge[-1])
for i, o in enumerate(bridge[1:-1], 1):
    move_pair(o, a.lerp(b, i/3) - center(o))

def extent(vs, axis):
    values = [v.dot(axis) for v in vs]
    return max(values)-min(values)

def resize_profile(o, axes, desired):
    """Scale around the mesh center; translation-only and uniform-size nodes stay live."""
    vs = vertices(o)
    factors = [size / extent(vs, axis) for axis, size in zip(axes, desired)]
    inv = o.matrix_world.inverted().to_3x3()
    raw_center = sum((v.co for v in o.data.vertices), Vector()) / len(o.data.vertices)
    for v in o.data.vertices:
        offset = o.matrix_world.to_3x3() @ (v.co-raw_center)
        delta = sum((axis * offset.dot(axis) * (factor-1) for axis, factor in zip(axes, factors)), Vector())
        v.co += inv @ delta
    o.data.update()
    changed.add(o.name)

# All upright sections are 28 mm square. All shoes are 52 x 52 x 24 mm.
# The stair shoes retain their below-tread mounting elevation.
for o in posts:
    foot = foot_for(o)
    if o.name.startswith('Metal | perimeter post'):
        radial = center(o) - CENTER
        radial.z = 0
        x = radial.normalized()
    else:
        # Every later shoe is an eight-vertex box. A horizontal edge gives its axes.
        candidates = []
        for e in foot.data.edges:
            d = foot.matrix_world.to_3x3() @ (foot.data.vertices[e.vertices[1]].co-foot.data.vertices[e.vertices[0]].co)
            if d.length > .001 and abs(d.z) < .0001:
                candidates.append(d)
        x = max(candidates, key=lambda d: d.length).normalized()
    y = UP.cross(x).normalized()
    resize_profile(o, (x, y), (.028, .028))
    resize_profile(foot, (x, y, UP), (.052, .052, .024))
    if o.name.startswith('Metal | perimeter post'):
        # Match the existing small feet: 11 mm inset, 13 mm above the deck.
        foot.matrix_world = Matrix.Translation((0, 0, -.010)) @ foot.matrix_world
    foot.data.materials.clear()
    foot.data.materials.append(ALLOY)
    o.data.materials.clear()
    o.data.materials.append(STEEL)
    for m in foot.modifiers:
        if m.type == 'BEVEL':
            m.width = .0015 / max(foot.matrix_world.to_scale())
            m.segments = 2
    o['railing_profile_mm'] = '28 x 28'
    foot['railing_foot_mm'] = '52 x 52 x 24'
    bpy.context.view_layer.update()

# Match stair rail cross sections to the existing 25 x 18 mm perimeter rails.
stair_rails = [o for o in S.objects if o.visible_get() and o.type == 'MESH' and
               o.name.startswith('Left stairs | ') and ('continuous' in o.name and 'rail' in o.name or 'triangle outer rail return' in o.name)]
for o in stair_rails:
    edges = [o.matrix_world.to_3x3() @ (o.data.vertices[e.vertices[1]].co-o.data.vertices[e.vertices[0]].co) for e in o.data.edges]
    tangent = max(edges, key=lambda e: e.length).normalized()
    side = UP.cross(tangent).normalized()
    depth = tangent.cross(side).normalized()
    resize_profile(o, (side, depth), (.025, .018))
    o.data.materials.clear()
    o.data.materials.append(STEEL)

bpy.context.view_layer.update()

# Check actual evaluated geometry, including modifiers and existing controls.
foot_errors = []
centering_errors = []
for o in posts:
    foot = foot_for(o)
    vs = vertices(foot)
    # The horizontal box edges supply oriented dimensions without AABB inflation.
    ev = foot.evaluated_get(bpy.context.evaluated_depsgraph_get())
    raw_edges = [foot.matrix_world.to_3x3() @ (foot.data.vertices[e.vertices[1]].co-foot.data.vertices[e.vertices[0]].co) for e in foot.data.edges]
    x = max((d for d in raw_edges if abs(d.z)<.0001), key=lambda d:d.length).normalized()
    sizes = [extent(vs, axis) for axis in (x, UP.cross(x), UP)]
    if max(abs(a-b) for a,b in zip(sizes, (.052,.052,.024))) > .00015:
        foot_errors.append((foot.name, sizes))
    delta = center(o)-center(foot)
    if math.hypot(delta.x,delta.y) > .0002:
        centering_errors.append((o.name,list(delta)))
assert not foot_errors, foot_errors
assert not centering_errors, centering_errors
points = [(o.name, center(o)) for o in posts]
nearest = sorted(((a-b).length, n, m) for i,(n,a) in enumerate(points) for m,b in points[i+1:])
assert nearest[0][0] > .40, nearest[:5]
unexpected = [n for n,h in before.items() if n not in changed and signature(bpy.data.objects[n]) != h]
assert not unexpected, unexpected
invalid = [(o.name, f.data_path) for o in S.objects if o.animation_data for f in o.animation_data.drivers if not f.driver.is_valid]
assert not invalid, invalid
report = {'active_posts':len(posts), 'compact_feet':len(posts), 'large_feet_replaced':26,
          'archived_redundant_posts':2, 'foot_dimensions_m':[.052,.052,.024],
          'post_dimensions_m':[.028,.028], 'circle_arcs':arc_reports,
          'minimum_post_center_spacing_m':nearest[0][0], 'closest_pairs':nearest[:8],
          'matched_stair_rail_sections':len(stair_rails), 'invalid_drivers':invalid,
          'unaffected_objects_verified':len(before)-len(changed), 'changed_objects':sorted(changed),
          'saved':bpy.data.filepath}
P.joinpath('verification.json').write_text(json.dumps(report,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath,compress=True)
result = {k:v for k,v in report.items() if k not in ('changed_objects','closest_pairs')}
