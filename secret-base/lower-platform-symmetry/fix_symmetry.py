"""Restore manufactured symmetry in the live lower workshop, in physical space.

Run once on before-symmetry.blend. The existing platform transform, parenting,
materials, bridge control drivers, room, terrain and camera are retained.
"""
import bpy
import math
import json
import hashlib
from pathlib import Path
from mathutils import Matrix, Vector

P = Path('/Users/danielku/mywebsite/secret-base/lower-platform-symmetry')
S = bpy.context.scene
assert not S.get('lower_platform_symmetry_fixed'), 'Symmetry correction already applied'
assert bpy.context.mode == 'OBJECT'
FRAME = Matrix.Translation((21.299999237, 0, 0)) @ Matrix.Rotation(-math.atan2(12, 19), 4, 'Z')
INV = FRAME.inverted()
lower = bpy.data.objects['Lower | plain octagon']
DECK = bpy.data.collections['157 | Lower deck and cliff supports']
DETAIL = bpy.data.collections['161 | Reference aligned service pad and brackets']
BRIDGE = bpy.data.collections['158 | Connected bridge and railings']
F = max((INV @ lower.matrix_world @ v.co).z for v in lower.data.vertices)
source_floor = bpy.data.meshes.get(lower.get('symmetry_source_mesh','')) or lower.data
oldfoot = [Vector((INV @ lower.matrix_world @ v.co)[:2]) for v in list(source_floor.vertices)[:11]]
x0, x1 = 4.621191, max(p.x for p in oldfoot)
y0, y1 = min(p.y for p in oldfoot), max(p.y for p in oldfoot)
CX, CY = (x0+x1)/2, (y0+y1)/2
CUT = 1.25
poly = [(x0,y0+CUT),(x0+CUT,y0),(x1-CUT,y0),(x1,y0+CUT),
        (x1,y1-CUT),(x1-CUT,y1),(x0+CUT,y1),(x0,y1-CUT)]
steel = bpy.data.materials['Metal | dark structural steel']
alloy = bpy.data.materials['Metal | outer walkway alloy']
black = bpy.data.materials['Metal | unlit grate recess']
changed = set()

def fingerprint(o):
    h = hashlib.sha256()
    h.update(str(tuple(tuple(row) for row in o.matrix_world)).encode())
    h.update(str((o.hide_render,o.hide_viewport,o.hide_get())).encode())
    if o.type == 'MESH':
        h.update(str([tuple(v.co) for v in o.data.vertices]).encode())
        h.update(str([tuple(f.vertices) for f in o.data.polygons]).encode())
    return h.hexdigest()

before = {o.name:fingerprint(o) for o in bpy.data.objects}

def replace(o, verts, faces):
    old = o.data
    old.use_fake_user = True
    if 'symmetry_source_mesh' not in o:
        o['symmetry_source_mesh'] = old.name
    me = bpy.data.meshes.new(o.name + ' | physical symmetry')
    tolocal = o.matrix_world.inverted() @ FRAME
    me.from_pydata([tuple(tolocal @ Vector(v)) for v in verts], [], faces)
    for m in old.materials:
        me.materials.append(m)
    me.update()
    o.data = me
    changed.add(o.name)
    return o

def obj(name, template):
    o = bpy.data.objects.get(name)
    if o is None:
        o = template.copy()
        o.name = name
        template.users_collection[0].objects.link(o)
    return o

def hide(o):
    o.hide_set(True)
    o.hide_render = True
    changed.add(o.name)

def beam(o, a, b, width, depth):
    a,b = Vector(a),Vector(b)
    axis = (b-a).normalized()
    helper = Vector((0,0,1)) if abs(axis.z)<.95 else Vector((0,1,0))
    u = axis.cross(helper).normalized()*width/2
    v = axis.cross(u).normalized()*depth/2
    verts = [tuple(p+su*u+sv*v) for p in (a,b) for su,sv in [(-1,-1),(1,-1),(1,1),(-1,1)]]
    return replace(o,verts,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)])

def strip(o, points, width, depth):
    ps = [Vector(p) for p in points]
    verts = []
    for i,p in enumerate(ps):
        before = (p-ps[i-1]).normalized() if i else (ps[1]-p).normalized()
        after = (ps[i+1]-p).normalized() if i<len(ps)-1 else before
        n1,n2 = Vector((-before.y,before.x,0)).normalized(),Vector((-after.y,after.x,0)).normalized()
        n = (n1+n2).normalized()
        n *= width/2/max(.3,n.dot(n1))
        verts += [tuple(p+sg*n+Vector((0,0,z))) for sg,z in [(-1,-depth/2),(1,-depth/2),(1,depth/2),(-1,depth/2)]]
    faces = [(0,3,2,1)]
    for i in range(len(ps)-1):
        faces += [(4*i+j,4*i+(j+1)%4,4*(i+1)+(j+1)%4,4*(i+1)+j) for j in range(4)]
    faces.append(tuple(range(4*(len(ps)-1),4*len(ps))))
    return replace(o,verts,faces)

# Eight straight sides: equal corner cuts and exact opposing edge pairs.
verts = [(x,y,z) for z in (F-.205,F) for x,y in poly]
replace(lower,verts,[tuple(reversed(range(8))),tuple(range(8,16))]+
        [(i,(i+1)%8,(i+1)%8+8,i+8) for i in range(8)])
lower['shape'] = 'Symmetric clipped rectangle: eight sides, four equal corner cuts'
lower['side_width_m'] = x1-x0
lower['depth_m'] = y1-y0
lower['corner_cut_m'] = CUT
lower['symmetry_center_in_room'] = [CX,CY]
lower['editing_note'] = 'Physical symmetry; do not project or warp this manufactured floor to reference pixels.'
lower['reference_detail'] = 'Eight-sided symmetric deck with concentric circular service pad.'

# Retain the existing ring hierarchy/materials, replacing pixel-fit ellipses.
R = 1.90
rings = [
    ('turntable surface',0,1,.010),('brass registration band',.995,1.023,.022),
    ('inner metal rim',1.027,1.058,.019),('outer recessed channel',1.058,1.083,.016),
    ('broad perimeter apron',1.086,1.225,.012),('outer circle groove',1.225,1.239,.016),
    ('outer circle glint',1.239,1.250,.018),('perimeter groove',1.287,1.300,.012),
    ('center disc rim',.452,.469,.024),('center disc reveal',.469,.481,.023)]
N = 192
def circle(r,t,z):
    return (CX+r*math.cos(t),CY+r*math.sin(t),z)
for name,ri,ro,dz in rings:
    o = bpy.data.objects['Lower | fitted '+name]
    if ri == 0:
        vs = [(CX,CY,F+dz)]+[circle(ro*R,i*math.tau/N,F+dz) for i in range(N)]
        fs = [(0,i+1,(i+1)%N+1) for i in range(N)]
    else:
        vs = [circle(r*R,i*math.tau/N,F+dz) for r in (ri,ro) for i in range(N)]
        fs = [(i,N+i,N+(i+1)%N,(i+1)%N) for i in range(N)]
    replace(o,vs,fs)
    o['true_circle_radii_m'] = [ri*R,ro*R]
    o['circle_center_in_room'] = [CX,CY]
for prefix,count in [('Lower | fitted radial turntable seam',12),('Lower | registration band fastener',16)]:
    objects = sorted((o for o in DETAIL.objects if o.name.startswith(prefix)),key=lambda o:o.name)
    assert len(objects) == count
    for i,o in enumerate(objects):
        t = i*math.tau/count
        if count == 12:
            a,b = circle(.485*R,t,F+.024),circle(.99*R,t,F+.024)
            beam(o,a,b,.006,.004)
        else:
            a,b = circle(1.011*R-.01,t,F+.026),circle(1.011*R+.01,t,F+.026)
            beam(o,a,b,.018,.005)

# Replace all warped rim pieces with the same eight-sided perimeter.
for prefix,width,depth,dz in [('Lower | load bearing perimeter fascia',.13,.32,-.16),
                             ('Lower | edge highlight',.04,.025,-.062)]:
    objects = sorted((o for o in DECK.objects if o.name.startswith(prefix)),key=lambda o:o.name)
    for i,o in enumerate(objects):
        if i<8:
            beam(o,(*poly[i],F+dz),(*poly[(i+1)%8],F+dz),width,depth)
        else:
            hide(o)
for o in list(DECK.objects)+list(DETAIL.objects):
    if any(o.name.startswith(p) for p in ['Lower | fitted deep front fascia','Lower | structural floor plate seam','Lower | fitted outer deck seam']):
        hide(o)

# Symmetric outer floor joints stop at the circular perimeter and deck rim.
seam_template = bpy.data.objects['Lower | fitted outer deck seam']
for i,(x,y) in enumerate(poly):
    direction = Vector((x-CX,y-CY)).normalized()
    a = (CX+direction.x*R*1.31,CY+direction.y*R*1.31,F+.014)
    b = (x-direction.x*.12,y-direction.y*.12,F+.014)
    o = obj('Lower | symmetric outer deck seam %02d'%i,seam_template)
    o.hide_render = False
    o.hide_set(False)
    beam(o,a,b,.008,.003)

# Bridge and perimeter guardrails are managed by the concurrent bridge task.

# Move only the upper ends of the visible front foundation brackets with
# their fascia; keep the embedded lower anchors in the existing cliff.
for o in DETAIL.objects:
    if not o.name.startswith('Lower | reference large diagonal bracket'):continue
    ps = [INV @ o.matrix_world @ v.co for v in o.data.vertices]
    a,b = sum(ps[:4],Vector())/4,sum(ps[4:],Vector())/4
    for p in (a,b):
        if p.z<F-.65:continue
        j = min(range(3),key=lambda j:(p.xy-(oldfoot[j]+oldfoot[j+1])/2).length)
        d = oldfoot[j+1]-oldfoot[j]
        t = max(0,min(1,(p.xy-oldfoot[j]).dot(d)/d.length_squared))
        q = Vector(poly[j]).lerp(Vector(poly[j+1]),t)
        p.x,p.y = q.x,q.y
    beam(o,a,b,.12,.15)

S['lower_platform_symmetry_fixed'] = True
S['lower_platform_reference'] = 'Workshop architecture retained; deck and service circles corrected in physical space.'
bpy.context.view_layer.update()
unexpected = [o.name for o in bpy.data.objects if o.name in before and o.name not in changed and fingerprint(o)!=before[o.name]]
assert not unexpected, unexpected
# Validate the actual stored world geometry, not just generator constants.
stored = [INV @ lower.matrix_world @ v.co for v in list(lower.data.vertices)[8:]]
mirror_error = max(min((Vector((2*CX-p.x,p.y,p.z))-q).length for q in stored) for p in stored)
mirror_error = max(mirror_error,max(min((Vector((p.x,2*CY-p.y,p.z))-q).length for q in stored) for p in stored))
assert len(stored)==8 and mirror_error<1e-4
circle_error = 0
for name,ri,ro,dz in rings:
    o = bpy.data.objects['Lower | fitted '+name]
    ps = [INV @ o.matrix_world @ v.co for v in o.data.vertices]
    for i,p in enumerate(ps):
        r = (0 if i==0 else ro*R) if ri==0 else (ri if i<N else ro)*R
        circle_error = max(circle_error,abs(math.hypot(p.x-CX,p.y-CY)-r))
assert circle_error<1e-4
assert R*1.30 < min((x1-x0)/2,(y1-y0)/2)
report = {'active_file':bpy.data.filepath,'outline_corners':len(stored),
          'center_room':[CX,CY],'dimensions':[x1-x0,y1-y0],'corner_cut':CUT,
          'maximum_mirror_error_m':mirror_error,'maximum_circle_radius_error_m':circle_error,
          'concentric_components':len(rings),'radial_seams':12,'fasteners':16,
          'unrelated_objects_changed':unexpected,
          'changed_objects':sorted(changed),'floor_height':F}
P.joinpath('verification.json').write_text(json.dumps(report,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath,compress=True)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'symmetric-lower-platform.blend'),copy=True,compress=True)
result = {k:v for k,v in report.items() if k!='changed_objects'}
