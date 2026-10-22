"""Run against the live scene: deeper steel underframe and uniform slim posts."""
import bpy
import math
from pathlib import Path
from mathutils import Vector, Matrix

S = bpy.context.scene
P = Path('/Users/danielku/mywebsite/secret-base/platform-controls')
original = bpy.data.filepath
bpy.ops.wm.save_as_mainfile(filepath=str(P / 'before-middle-support.blend'), copy=True, compress=True)
rig = bpy.data.objects['Rig | middle radius']
selected = list(bpy.context.selected_objects)
active = bpy.context.view_layer.objects.active

# Narrow each post around its own center, preserving native slider modifiers.
posts = [o for o in S.objects if o.name.startswith('Metal | perimeter post')]
for o in posts:
    o.data = o.data.copy()
    center = Vector(tuple((min(v.co[i] for v in o.data.vertices) + max(v.co[i] for v in o.data.vertices)) / 2 for i in range(3)))
    for v in o.data.vertices:
        v.co.x = center.x + (v.co.x-center.x)*.52
        v.co.y = center.y + (v.co.y-center.y)*.52
    o.data.update()

# Exact inventory verified at railing height, parented to the middle-radius rig.
# Retain fixtures in a disabled archive so this visual removal is reversible.
removed = []
for base,count in [('Metal | warm lamp armor',7),('Metal | lamp cap',7),('Metal | inset amber diffuser',28),('Metal | amber floor pool',8)]:
    removed.extend(base + ('.%03d'%i if i else '') for i in range(count))
archive=bpy.data.collections.new('Archive | removed railing post fixtures')
S.collection.children.link(archive)
archive.hide_render=True
archive.hide_viewport=True
for name in removed:
    o=bpy.data.objects[name]
    assert o.parent==rig
    archive.objects.link(o)
    for c in list(o.users_collection):
        if c!=archive:c.objects.unlink(o)
    o.hide_render=True
    o.hide_viewport=True
bpy.data.collections['03 | Steel perimeter and warm inset lamps'].name = '03 | Uniform slender steel railings'

col = bpy.data.collections.new('07 | Middle platform steel underframe')
S.collection.children.link(col)
root = bpy.data.objects.new('Support | radius-following underframe', None)
col.objects.link(root)
root.parent = rig
root.matrix_parent_inverse = Matrix.Identity(4)
ctrl = bpy.data.objects['SCENE SLIDERS']
width = float(ctrl.modifiers['Scene Sliders']['Socket_7'])
for i in [0, 1]:
    d = root.driver_add('scale', i).driver
    d.expression = 'w/%.12f' % width
    v = d.variables.new(); v.name = 'w'; v.type = 'SINGLE_PROP'
    v.targets[0].id = ctrl
    v.targets[0].data_path = 'modifiers["Scene Sliders"]["Socket_7"]'
steel = bpy.data.materials['Metal | dark structural steel']
trim = bpy.data.materials['Metal | outer walkway alloy']

def finish(o, name, mat):
    o.name = 'Support | ' + name
    for c in list(o.users_collection): c.objects.unlink(o)
    col.objects.link(o)
    o.parent = root
    o.matrix_parent_inverse = Matrix.Identity(4)
    o.data.materials.append(mat)
    m=o.modifiers.new('Soft fabricated edges', 'BEVEL'); m.width=.009; m.segments=2
    o.modifiers.new('Weighted steel normals','WEIGHTED_NORMAL')
    return o

def beam(name, a, b, thickness=.10, depth=.14):
    a,b=Vector(a),Vector(b)
    bpy.ops.mesh.primitive_cube_add(size=1)
    o=bpy.context.object
    o.dimensions=(thickness,depth,(b-a).length)
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    finish(o,name,steel)
    o.location=(a+b)/2
    o.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler()
    return o

def ring(name, ri, ro, lo, hi, mat):
    N=96; verts=[]; faces=[]
    for z in [lo,hi]:
        for r in [ri,ro]:
            verts.extend((r*math.cos(i*math.tau/N),r*math.sin(i*math.tau/N),z) for i in range(N))
    for i in range(N):
        j=(i+1)%N
        faces.extend([(i,j,N+j,N+i),(2*N+i,3*N+i,3*N+j,2*N+j),(i,2*N+i,2*N+j,j),(N+i,N+j,3*N+j,3*N+i)])
    me=bpy.data.meshes.new(name); me.from_pydata(verts,[],faces);me.update()
    o=bpy.data.objects.new(name,me); col.objects.link(o);finish(o,name,mat)

def pt(r,t,z): return (r*math.cos(t),r*math.sin(t),z)

ring('upper load-bearing rim',3.49,3.64,6.36,6.51,steel)
ring('lower structural collar',3.08,3.25,5.53,5.72,trim)
ring('rock anchor collar',1.92,2.10,4.40,4.59,steel)
for i in range(16):
    t=i*math.tau/16
    beam('radial deck joist %02d'%i,pt(1.82,t,6.38),pt(3.58,t,6.38),.13,.19)
    beam('tapered perimeter upright %02d'%i,pt(3.57,t,6.43),pt(3.17,t,5.62),.11,.14)
    beam('rock-to-rim diagonal bracket %02d'%i,pt(2.00,t,4.49),pt(3.56,t,6.39),.14,.19)
    beam('circumferential diagonal brace %02d'%i,pt(3.17,t,5.63),pt(3.57,t+math.tau/16,6.41),.075,.09)

for o in list(bpy.context.selected_objects):o.select_set(False)
for o in selected:
    if o.name in S.objects:o.select_set(True)
if active and active.name in S.objects:bpy.context.view_layer.objects.active=active
bpy.context.view_layer.update()
assert len(posts)==30
assert all(bpy.data.objects[n].hide_render and bpy.data.objects[n].hide_viewport for n in removed)
assert all(not f.driver.is_valid is False for f in root.animation_data.drivers)
bpy.ops.wm.save_as_mainfile(filepath=original,compress=True)
result={'saved':original,'slim_posts':len(posts),'removed_lamp_parts':len(removed),'support_members':len(col.objects)-1,'backup':str(P/'before-middle-support.blend')}
