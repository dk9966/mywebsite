"""Fit the existing editable cave to the rear wall contours of both rooms."""
import bpy, bmesh, json, math
from pathlib import Path
from mathutils import Vector

P = Path(__file__).resolve().parent
w = bpy.data.objects['150 | continuous cave with oblique carved rooms']
deck = bpy.data.objects['Upper | beveled square gallery']
baseline = bpy.data.meshes['Cave | before snug platform backs']
M = deck.matrix_world.inverted() @ w.matrix_world
MI = M.inverted()
if bpy.context.mode != 'OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')
w.data = baseline.copy()
w.data.name = 'Cave | close continuous platform backs'

def smooth(t):
    t = max(0., min(1., t))
    return t*t*(3.-2.*t)

def contour(p, room):
    if room == 'upper':
        cx, cy = 0., 0.
        inset = max(0., min(.55, (p.z-12.934)*.667))
        planes = [(1.,0.,3.1045-inset), (0.,1.,3.1045-inset),
                  (1.,1.,4.589-2.*inset), (1.,-1.,4.589-2.*inset)]
        amin, amax = -64., 113.
        height = smooth((p.z-11.35)/.28)*smooth((13.0-p.z)/.25)
    else:
        cx, cy = -.53755, -2.46715
        planes = [(1.,0.,3.1901), (0.,1.,.9585),
                  (1.,1.,3.9033), (1.,-1.,8.8376)]
        amin, amax = -56., 125.
        height = smooth((p.z-6.58)/.26)*smooth((8.85-p.z)/.20)
    dx, dy = p.x-cx, p.y-cy
    radius = math.hypot(dx,dy)
    if radius < 1e-6:
        return p.copy(), 0.
    dx /= radius; dy /= radius
    angle = math.degrees(math.atan2(dy,dx))
    angular = smooth((angle-amin)/9.)*smooth((amax-angle)/9.)
    options = [(c-a*cx-b*cy)/(a*dx+b*dy) for a,b,c in planes if a*dx+b*dy > 1e-6]
    if not options or height*angular <= 0.:
        return p.copy(), 0.
    target = min(options)
    distance = radius-target
    weight = height*angular*smooth((3.8-distance)/1.1)*smooth((distance+.65)/.30)
    return Vector((cx+target*dx, cy+target*dy, p.z)), weight

bm = bmesh.new(); bm.from_mesh(w.data); bm.verts.ensure_lookup_table()
original = [M@v.co for v in bm.verts]
weights = []
rooms = []
for p in original:
    upper = contour(p,'upper'); lower = contour(p,'lower')
    room = 'upper' if upper[1] > lower[1] else 'lower'
    q, a = upper if room == 'upper' else lower
    weights.append(a); rooms.append(room)
for v,p,a,room in zip(bm.verts,original,weights,rooms):
    q,_ = contour(p,room)
    v.co = MI @ p.lerp(q,a)

# Remove redundant interior edges only on the now-flat concealed back panels.
before_faces = len(bm.faces)
planes = [('lower',1,0,3.1901), ('lower',0,1,.9585),
          ('lower',1,1,3.9033), ('lower',1,-1,8.8376),
          ('upper',1,0,3.1045), ('upper',0,1,3.1045),
          ('upper',1,1,4.589), ('upper',1,-1,4.589)]
for room,a,b,c in planes:
    lo,hi = (6.84,8.65) if room=='lower' else (11.63,12.75)
    faces = []
    for f in bm.faces:
        points = [M@v.co for v in f.verts]
        if all(lo<p.z<hi and abs(a*p.x+b*p.y-c)<.00002 for p in points):
            faces.append(f)
    if faces:
        bmesh.ops.dissolve_faces(bm,faces=faces,use_verts=True)
bmesh.ops.triangulate(bm,faces=[f for f in bm.faces if len(f.verts)>3])
bm.normal_update(); bm.to_mesh(w.data); bm.free(); w.data.update()
bpy.context.view_layer.update()
w['platform_back_fit'] = 'Editable continuous rock pulled close behind both platform walls; backup in platform-back-fit.'
result = {'moved_vertices':sum(a>.001 for a in weights),
          'upper_vertices':sum(a>.001 and r=='upper' for a,r in zip(weights,rooms)),
          'lower_vertices':sum(a>.001 and r=='lower' for a,r in zip(weights,rooms)),
          'faces':len(w.data.polygons), 'redundant_triangles_removed':before_faces-len(w.data.polygons)}
(P/'fit-report.json').write_text(json.dumps(result,indent=2))
