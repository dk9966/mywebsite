"""Extend the lower workshop with two opposite bays and a beveled return.

Run once in the inspected live scene. Existing mesh datablocks and a complete
before-extension.blend checkpoint preserve the prior sculpt and railing.
"""
import ast
import bpy
import bmesh
import hashlib
import json
import math
from pathlib import Path
from mathutils import Matrix, Vector

P = Path('/Users/danielku/mywebsite/secret-base/opposite-interior-walls')
S = bpy.context.scene
assert bpy.context.mode == 'OBJECT'
assert not bpy.data.collections.get('163 | Opposite interior workshop walls')
lower = bpy.data.objects['Lower | plain octagon']
rock = bpy.data.objects['150 | continuous cave with oblique carved rooms']
FRAME = rock.matrix_world.copy()
INV = FRAME.inverted()
UP = Vector((0, 0, 1))
foot = [INV @ lower.matrix_world @ v.co for v in list(lower.data.vertices)[8:]]
F = foot[0].z
H = 2.03
C = bpy.data.collections.new('163 | Opposite interior workshop walls')
S.collection.children.link(C)

def signature(o):
    return hashlib.sha256(repr((list(map(list, o.matrix_world)),
        [tuple(v.co) for v in o.data.vertices],
        [tuple(p.vertices) for p in o.data.polygons])).encode()).hexdigest()

untouched = {o.name: signature(o) for o in S.objects if o.type == 'MESH'
    and (o == lower or o.name.startswith(('Lower | fitted ', 'Bridge |')))}
steel = bpy.data.materials['Metal | dark structural steel']
alloy = bpy.data.materials['Metal | outer walkway alloy']
black = bpy.data.materials['Metal | unlit grate recess']
wall = bpy.data.materials['Lower | aligned blue graphite panels']
trim = bpy.data.materials['Lower | aligned architectural trim']
white = bpy.data.materials['Lower | cool white practical diffuser']
roof = bpy.data.materials['Lower | matte roof cassette']
made = []
# Reuse the exact existing fabricated mesh helpers without replaying that pass.
source = ast.parse((P.parent/'octagon-wall-alignment/align_walls.py').read_text())
helpers = [n for n in source.body if isinstance(n, ast.FunctionDef)
           and n.name in ('mesh', 'beam', 'plate')]
exec(compile(ast.Module(body=helpers, type_ignores=[]), '<existing wall helpers>', 'exec'))

points = [foot[4].copy(), foot[4].lerp(foot[3], .5), foot[3].copy(), foot[2].copy()]
segments = list(zip(points, points[1:]))
normals = [Vector(((q-p).y, -(q-p).x, 0)).normalized() for p, q in segments]
labels = ['opposite bay 1', 'opposite bay 2', 'far right beveled bay']
panels = []
previous_normal = Vector(((foot[4]-foot[5]).y, -(foot[4]-foot[5]).x, 0)).normalized()
joint_normals = [previous_normal] + normals

for i, (p, q) in enumerate(segments):
    normal, tangent = normals[i], (q-p).normalized()
    length = (q-p).length
    prefix = 'Lower | ' + labels[i]
    lo, hi = p+tangent*.08+UP*.035, q-tangent*.08+UP*(H-.075)
    panel = plate(prefix, [lo, Vector((hi.x, hi.y, lo.z)), hi,
                          Vector((lo.x, lo.y, hi.z))], normal, .12, trim)
    panel['wall_section'] = labels[i]
    panel['octagon_edge_vertices'] = [4, 3] if i < 2 else [3, 2]
    panels.append(panel)
    for ix in range(2):
        for iy in range(4):
            x0 = .08+(length-.16)*ix/2+.005
            x1 = .08+(length-.16)*(ix+1)/2-.005
            z0 = .035+(H-.11)*iy/4+.006
            z1 = .035+(H-.11)*(iy+1)/4-.006
            vs = [p+tangent*x+UP*z+normal*.014
                  for x, z in [(x0,z0),(x1,z0),(x1,z1),(x0,z1)]]
            plate(prefix+' recessed panel', vs, normal, .018, wall, .0015)
    for z in (.035, H-.045):
        beam(prefix+' panel border', p+UP*z+normal*.028,
             q+UP*z+normal*.028, .055, .06, trim)
    beam(prefix+' roof fascia', p+UP*H+normal*.08,
         q+UP*H+normal*.08, .20, .15, steel, .005)
    # Miter adjoining canopy panels in real plan coordinates.
    def offset_at(j, amount):
        if j == len(points)-1:
            return normals[-1]*amount
        n0 = previous_normal if j == 0 else normals[j-1]
        n1 = normals[j]
        bisector = (n0+n1).normalized()
        return bisector*amount/bisector.dot(n1)
    plate(prefix+' roof cassette',
          [p+UP*(H+.06)+offset_at(i,.16),
           q+UP*(H+.06)+offset_at(i+1,.16),
           q+UP*(H+.06)+offset_at(i+1,-.48),
           p+UP*(H+.06)+offset_at(i,-.48)], UP, .10, roof)
    beam(prefix+' roof edge', p+UP*(H+.07)+offset_at(i,.19),
         q+UP*(H+.07)+offset_at(i+1,.19), .025, .022, alloy, .002)
    center = (p+q)/2+UP*1.48+normal*.045
    half = min(.36, length*.23)
    la, lb = center-tangent*half, center+tangent*half
    beam(prefix+' strip light housing', la, lb, .065, .065, steel)
    beam(prefix+' white strip diffuser', la+normal*.038,
         lb+normal*.038, .025, .018, white, .001)
    ld = bpy.data.lights.new(prefix+' wall wash', 'AREA')
    ld.energy = 28
    ld.color = (.65, .82, 1)
    ld.shape = 'RECTANGLE'
    ld.size, ld.size_y = half*2, .14
    light = bpy.data.objects.new(ld.name, ld)
    C.objects.link(light)
    light.location = FRAME @ (center+normal*.17)
    target = FRAME @ ((p+q)/2+UP*.25+normal*.20)
    light.rotation_euler = (target-light.location).to_track_quat('-Z','Y').to_euler()
    mw = light.matrix_world.copy()
    light.parent = lower
    light.matrix_world = mw

# The old corner already has a full-height pier; share that first joint.
for i, p in enumerate(points[1:], 1):
    normal = normals[-1] if i == 3 else (normals[i-1]+normals[i]).normalized()
    prefix = 'Lower | opposite joint %d ' % i
    beam(prefix+'upright pier', p+normal*.045, p+UP*H+normal*.045, .14,.19,trim,.007)
    beam(prefix+'pier edge', p+normal*.15, p+UP*H+normal*.15,.022,.018,alloy)
    beam(prefix+'splayed pier foot', p+normal*.20+UP*.025,
         p+normal*.06+UP*.34,.22,.16,trim,.006)
    beam(prefix+'foot inset', p+normal*.29+UP*.04,
         p+normal*.14+UP*.29,.065,.023,black,.002)

# Terminate the existing guardrail at the new end jamb. Preserve all named
# point attributes, which drive the bridge position and railing-height sliders.
rail_changes = []
for name in ['Lower | aligned continuous rail 0 0.190',
             'Lower | aligned continuous rail 0 0.345',
             'Lower | aligned perimeter curb 0']:
    ob = bpy.data.objects[name]
    ob.data.use_fake_user = True
    ob['before_opposite_walls_mesh'] = ob.data.name
    ob.data = ob.data.copy()
    bm = bmesh.new(); bm.from_mesh(ob.data); bm.verts.ensure_lookup_table()
    keep = len(bm.verts)-8
    bmesh.ops.delete(bm, geom=list(bm.verts)[keep:], context='VERTS')
    bm.verts.ensure_lookup_table()
    bm.faces.new(tuple(bm.verts[j] for j in range(keep-4, keep)))
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(ob.data); bm.free(); ob.data.update()
    rail_changes.append(name)
hidden_posts = []
for ob in S.objects:
    if ob.name.startswith(('Lower | aligned perimeter post 0 03 ',
                           'Lower | aligned perimeter post 0 04 ')):
        ob.hide_set(True); ob.hide_render = True
        hidden_posts.append(ob.name)

# Recess the connected sculpt behind the new physical wall planes. Subdivide
# only the nearby patch, keeping original terrain in a retained mesh datablock.
rock.data.use_fake_user = True
rock['before_opposite_walls_mesh'] = rock.data.name
rock.data = rock.data.copy()
rock.data.name = 'Cave | sculpt recessed behind opposite interior walls'
mx = INV @ rock.matrix_world
back = mx.inverted()
top = F+H
def inside(v):
    p = mx@v.co
    return 8.1 < p.x < 14.2 and -7.55 < p.y < .5 and F-.75 < p.z < top+1.5
bm = bmesh.new(); bm.from_mesh(rock.data)
edges = [e for e in bm.edges if any(inside(v) for v in e.verts)]
edge_count = len(edges)
if edges:
    bmesh.ops.subdivide_edges(bm, edges=edges, cuts=1, use_grid_fill=True)
bm.to_mesh(rock.data); bm.free()

def smooth(a, b, x):
    t = min(1., max(0., (x-a)/(b-a)))
    return t*t*(3-2*t)

changed = 0
for v in rock.data.vertices:
    p = mx@v.co
    if not inside(v):
        continue
    weight = (smooth(8.1, 9.0, p.x) * (1-smooth(13.5,14.2,p.x)) *
              smooth(-7.55,-6.60,p.y) * (1-smooth(-.80,.50,p.y)) *
              smooth(F-.75,F-.15,p.z) * (1-smooth(top+.40,top+1.50,p.z)))
    # Beyond the corner, follow its 45-degree line with equal normal clearance.
    boundary = foot[3].x + min(0., p.y-foot[3].y)
    clearance = .87 if p.y >= foot[3].y else .87*math.sqrt(2)
    target = boundary+clearance+.07*math.sin(p.y*3.1+p.z*2.3)
    delta = max(0., target-p.x)*weight
    if delta > 1e-7:
        p.x += delta
        v.co = back@p
        changed += 1
rock.data.update()
rock['opposite_wall_recess'] = 'Local physical recess behind two side bays and a 45-degree return; original sculpt retained.'
bpy.context.view_layer.update()
report = {'new_sections':labels,'base_points_local':[list(p) for p in points],
          'height_m':H,'rock_vertices_recessed':changed,
          'local_rock_edges_subdivided':edge_count,'shortened_rails':rail_changes,
          'hidden_replaced_posts':hidden_posts,
          'platform_pad_and_bridge_unchanged':all(signature(bpy.data.objects[n]) == h for n,h in untouched.items()),
          'new_objects':len(C.objects)}
assert report['platform_pad_and_bridge_unchanged']
(P/'extension-report.json').write_text(json.dumps(report, indent=2))
text = bpy.data.texts.new('extend_opposite_interior_walls.py')
text.write((P/'extend_walls.py').read_text())
bpy.ops.wm.save_as_mainfile(filepath=str(P/'extended-interior-walls.blend'),copy=True,compress=True)
result = report
