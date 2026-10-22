"""Replace camera-warped wall bays with upright, octagon-aligned architecture.

Run in the live Blender file. The previous walls and original mesh datablocks
are retained, and before-wall-alignment.blend contains the complete prior scene.
"""
import bpy, bmesh, math, json
from pathlib import Path
from mathutils import Vector, Matrix

P = Path('/Users/danielku/mywebsite/secret-base/octagon-wall-alignment')
S = bpy.context.scene
lower = bpy.data.objects['Lower | plain octagon']
FRAME = Matrix.Translation((21.299999237, 0, 0)) @ Matrix.Rotation(-math.atan2(12, 19), 4, 'Z')
INV = FRAME.inverted()
F = 6.824491024
H = 2.03
UP = Vector((0, 0, 1))
COLNAME = '162 | Octagon aligned workshop walls'
if bpy.data.collections.get(COLNAME) and len(bpy.data.collections[COLNAME].objects):
    raise RuntimeError('Walls already installed; restore the checkpoint before rebuilding.')
C = bpy.data.collections.get(COLNAME)
if not C:
    C = bpy.data.collections.new(COLNAME)
    S.collection.children.link(C)
old = bpy.data.collections['160 | Reference aligned workshop architecture']
for o in old.objects:
    if not any(t in o.name for t in ('hood', 'overhead', 'broad soft fill')):
        o.hide_render = True
        o.hide_set(True)

steel = bpy.data.materials['Metal | dark structural steel']
alloy = bpy.data.materials['Metal | outer walkway alloy']
black = bpy.data.materials['Metal | unlit grate recess']
wall = bpy.data.materials['Lower | aligned blue graphite panels']
trim = bpy.data.materials['Lower | aligned architectural trim']
white = bpy.data.materials['Lower | cool white practical diffuser']
roof = bpy.data.materials['Lower | matte roof cassette']
made = []

def mesh(name, verts, faces, material, bevel=0):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.materials.append(material)
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(me); bm.free(); me.update()
    o = bpy.data.objects.new(name, me); C.objects.link(o)
    o.parent = lower; o.matrix_world = FRAME
    if bevel:
        m = o.modifiers.new('Fabricated edge radius', 'BEVEL')
        m.width = bevel; m.segments = 2
        o.modifiers.new('Fabricated surface normals', 'WEIGHTED_NORMAL')
    made.append(o)
    return o

def beam(name, a, b, width, depth, material=steel, bevel=.003):
    a, b = Vector(a), Vector(b)
    axis = (b-a).normalized()
    helper = UP if abs(axis.z) < .9 else Vector((0, 1, 0))
    u = axis.cross(helper).normalized()*width/2
    v = axis.cross(u).normalized()*depth/2
    verts = [tuple(p+su*u+sv*v) for p in (a, b)
             for su, sv in [(-1,-1),(1,-1),(1,1),(-1,1)]]
    return mesh(name, verts, [(0,3,2,1),(4,5,6,7),(0,1,5,4),
                             (1,2,6,5),(2,3,7,6),(3,0,4,7)], material, bevel)

def plate(name, points, normal, depth, material, bevel=.003):
    n = len(points)
    verts = [tuple(p-normal*d) for d in (0, depth) for p in points]
    return mesh(name, verts, [tuple(range(n)), tuple(reversed(range(n,2*n)))]+
                [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)], material, bevel)

# The surviving front long edge defines the architectural axes. Two equally
# sized rear bays share exactly the same plane; only the octagon corner turns.
assert len(lower.data.vertices) == 16, 'Expected the current symmetric eight-sided slab.'
foot = [INV @ lower.matrix_world @ v.co for v in list(lower.data.vertices)[8:]]
ex = (foot[2]-foot[1]).normalized(); ex.z = 0; ex.normalize()
ey = Vector((-ex.y, ex.x, 0))
a = foot[6].copy()
b = foot[5].copy()
c = foot[4].copy()
points = [a, a.lerp(b,.5), b, c]
for p in points: p.z = F
segments = [(points[i],points[i+1]) for i in range(3)]
normals = [Vector(((q-p).y,-(q-p).x,0)).normalized() for p,q in segments]

for i, (p, q) in enumerate(segments):
    normal = normals[i]; tangent = (q-p).normalized(); length = (q-p).length
    label = ('rear bay 1', 'rear bay 2', 'angled corner bay')[i]
    lo = p+tangent*.08+UP*.035
    hi = q-tangent*.08+UP*(H-.075)
    corners = [lo, Vector((hi.x,hi.y,lo.z)), hi, Vector((lo.x,lo.y,hi.z))]
    panel = plate('Lower | octagon '+label, corners, normal, .12, trim)
    panel['wall_section'] = label
    panel['octagon_edge'] = 'rear long side' if i < 2 else 'angled corner'
    # Real, planar recessed metal tiles with narrow shadow gaps.
    for ix in range(2):
        for iy in range(4):
            x0 = .08+(length-.16)*ix/2+.005
            x1 = .08+(length-.16)*(ix+1)/2-.005
            z0 = .035+(H-.11)*iy/4+.006
            z1 = .035+(H-.11)*(iy+1)/4-.006
            vs = [p+tangent*x+UP*z+normal*.014
                  for x,z in [(x0,z0),(x1,z0),(x1,z1),(x0,z1)]]
            plate('Lower | octagon recessed panel',vs,normal,.018,wall,.0015)
    for z in (.035,H-.045):
        beam('Lower | octagon panel border',p+UP*z+normal*.028,
             q+UP*z+normal*.028,.055,.06,trim)
    beam('Lower | octagon roof fascia',p+UP*H+normal*.08,
         q+UP*H+normal*.08,.20,.15,steel,.005)
    plate('Lower | octagon roof cassette',
          [p+UP*(H+.06)+normal*.16,q+UP*(H+.06)+normal*.16,
           q+UP*(H+.06)-normal*.48,p+UP*(H+.06)-normal*.48],UP,.10,roof)
    beam('Lower | octagon roof edge',p+UP*(H+.07)+normal*.19,
         q+UP*(H+.07)+normal*.19,.025,.022,alloy,.002)
    if i < 3:
        center = (p+q)/2+UP*1.48+normal*.045
        half = min(.36,length*.23)
        la,lb = center-tangent*half,center+tangent*half
        beam('Lower | octagon strip light housing',la,lb,.065,.065,steel)
        beam('Lower | octagon white strip diffuser',la+normal*.038,
             lb+normal*.038,.025,.018,white,.001)
        ld = bpy.data.lights.new('Lower | octagon wall wash','AREA')
        ld.energy=28; ld.color=(.65,.82,1); ld.shape='RECTANGLE'
        ld.size=half*2; ld.size_y=.14
        light=bpy.data.objects.new(ld.name,ld); C.objects.link(light)
        light.location=FRAME@(center+normal*.17)
        target=FRAME@((p+q)/2+UP*.25+normal*.20)
        light.rotation_euler=(target-light.location).to_track_quat('-Z','Y').to_euler()
        mw=light.matrix_world.copy(); light.parent=lower; light.matrix_world=mw

for i,p in enumerate(points):
    normal = normals[0] if i==0 else normals[-1] if i==3 else (normals[i-1]+normals[i]).normalized()
    beam('Lower | octagon upright pier',p+normal*.045,p+UP*H+normal*.045,.14,.19,trim,.007)
    beam('Lower | octagon pier edge',p+normal*.15,p+UP*H+normal*.15,.022,.018,alloy)
    beam('Lower | octagon splayed pier foot',p+normal*.20+UP*.025,
         p+normal*.06+UP*.34,.22,.16,trim,.006)
    beam('Lower | octagon foot inset',p+normal*.29+UP*.04,
         p+normal*.14+UP*.29,.065,.023,black,.002)

# The slab and circular pad belong to the concurrent symmetry pass. Derive all
# wall geometry from their current edges without changing those source meshes.

bpy.context.view_layer.update()
report={'section_count_on_long_side':2,'section_count_on_angled_corner':1,
        'corner_turn_degrees':45,'wall_height':H,
        'wall_base_points_local':[list(p) for p in points],
        'front_edge_direction':list(ex),'new_meshes':len(made),
        'old_architecture_retained':True}
(P/'alignment.json').write_text(json.dumps(report,indent=2))
text=bpy.data.texts.new('align_octagon_walls.py'); text.write((P/'align_walls.py').read_text())
bpy.ops.wm.save_as_mainfile(filepath=str(P/'aligned-walls.blend'),copy=True,compress=True)
result=report
