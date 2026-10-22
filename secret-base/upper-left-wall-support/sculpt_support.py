"""Pull the existing cliff inward beneath the rear-left stair platform."""
import bpy
import bmesh
import math
import json
import hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

OUT = Path(__file__).resolve().parent
wall = bpy.data.objects['150 | continuous cave with oblique carved rooms']
assert bpy.context.mode == 'OBJECT'
assert wall.data.shape_keys is None
axis_u = Vector((.764548, .644567, 0)).normalized()
axis_v = Vector((-axis_u.y, axis_u.x, 0))
origin = Vector((-11.321278, 9.82563, 0))

def to_uv(p):
    d = p-origin
    return Vector((d.dot(axis_u), d.dot(axis_v), p.z))

def from_uv(p):
    return origin+axis_u*p.x+axis_v*p.y+Vector((0,0,p.z))

def fingerprint(obj):
    h = hashlib.sha256()
    h.update(str([list(row) for row in obj.matrix_world]).encode())
    if obj.type == 'MESH':
        h.update(str([tuple(v.co) for v in obj.data.vertices]).encode())
        h.update(str([tuple(p.vertices) for p in obj.data.polygons]).encode())
    return h.hexdigest()

protected = {o.name: fingerprint(o) for o in bpy.context.scene.objects if o != wall}
(OUT/'protected-before.json').write_text(json.dumps(protected, indent=2))
source = wall.data
source.use_fake_user = True
wall['before_upper_left_support_mesh'] = source.name
mesh = source.copy()
mesh.name = 'Cave | continuous wall with upper-left stair foundation'
wall.data = mesh
bm = bmesh.new()
bm.from_mesh(mesh)
for v in bm.verts:
    v.co = to_uv(v.co)

# Add resolution only in the pulled section and its transition to the cliff.
for _ in range(4):
    edges = [e for e in bm.edges if e.calc_length() > .70
             and all(-6 < v.co.x < 6 and -9 < v.co.y < 5
                     and -7 < v.co.z < 9.0 for v in e.verts)]
    if not edges:
        break
    bmesh.ops.subdivide_edges(bm, edges=edges, cuts=1, use_grid_fill=True)

# The two thin bearing shelves must meet the slab undersides precisely.
# Explicit contour rows avoid stretched triangles crossing the stair treads.
for height in [6.76, 6.80, 7.15, 7.65, 8.10, 8.42, 8.46, 8.68]:
    faces = [f for f in bm.faces
             if min(v.co.z for v in f.verts) < height < max(v.co.z for v in f.verts)
             and all(-5.9 < v.co.x < 5.9 and -9 < v.co.y < 5 for v in f.verts)]
    edges = {e for f in faces for e in f.edges}
    verts = {v for f in faces for v in f.verts}
    if faces:
        bmesh.ops.bisect_plane(bm, geom=list(verts)+list(edges)+faces,
                              dist=1e-6, plane_co=(0,0,height),
                              plane_no=(0,0,1), clear_inner=False, clear_outer=False)
for v in bm.verts:
    v.co = from_uv(v.co)
bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
bm.to_mesh(mesh)
bm.free()
mesh.update()
wall.shape_key_add(name='Basis')
key = wall.shape_key_add(name='Upper-left | broad inward rock support')

def smooth(t):
    t = max(0., min(1., t))
    return t*t*(3-2*t)

# Cross-section of the cliff in the direction of the broad stairs.
# The near-vertical lower face flares outward into the natural cliff below.
profile = [(-7,-3.0), (-4,-4.25), (0,-5.20), (3.5,-5.95),
           (5.7,-6.12), (6.76,-6.16), (6.80,-4.779),
           (7.15,-4.144), (7.65,-3.236), (8.10,-2.419),
           (8.42,-1.837), (8.46,1.85), (8.68,2.05), (9.0,2.15)]

def surface(z):
    for (z0,v0),(z1,v1) in zip(profile,profile[1:]):
        if z0 <= z <= z1:
            return v0+(v1-v0)*(z-z0)/(z1-z0)
    return profile[0][1] if z < profile[0][0] else profile[-1][1]

changed = 0
max_pull = 0.
for i,vert in enumerate(mesh.vertices):
    p = to_uv(vert.co)
    u,v,z = p
    if not (-6 < u < 6 and -9 < v < 5 and -7 < z < 8.68):
        continue
    width = smooth((5.6-abs(u))/3.1)
    height = smooth((z+7)/3.5)*smooth((8.68-z)/.22)
    rear = smooth((5-v)/2)
    blend = width*height*rear
    rough = (.16*math.sin(u*1.63+z*.85)
             + .10*math.cos(u*2.3-z*.47))*smooth((6.76-z)/1.15)
    target = surface(z)+rough
    pull = min(0., target-v)*blend
    if abs(pull) > 1e-7:
        p.y += pull
        key.data[i].co = from_uv(p)
        changed += 1
        max_pull = max(max_pull, -pull)
key.value = 1.
wall.active_shape_key_index = 1
wall['upper_left_foundation'] = 'Existing continuous cave wall pulled inward beneath broad stairs and both landings; tapered faceted cliff; reversible shape key.'
mesh.update()
bpy.context.view_layer.update()
assert all(fingerprint(bpy.data.objects[name]) == value for name,value in protected.items())
result = {'changed_vertices':changed, 'maximum_inward_pull':max_pull,
          'vertices':len(mesh.vertices), 'faces':len(mesh.polygons),
          'protected_objects_unchanged':len(protected), 'shape_key':key.name,
          'source_mesh':source.name}
(OUT/'sculpt-report.json').write_text(json.dumps(result, indent=2))
