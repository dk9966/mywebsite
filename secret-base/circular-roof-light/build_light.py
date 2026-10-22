"""Four wall-to-crown roof planes and a centered, adjustable circular practical.

Run in the inspected live scene after saving before-circular-roof-light.blend.
The height control uses native Geometry Nodes and simple drivers, without handlers.
"""
import bpy
import bmesh
import math
import json
from pathlib import Path
from mathutils import Matrix, Vector

P = Path('/Users/danielku/mywebsite/secret-base/circular-roof-light')
S = bpy.context.scene
COLLECTION = '165 | Circular workshop light and four roof slopes'
assert bpy.context.mode == 'OBJECT'
assert bpy.data.collections.get(COLLECTION) is None
lower = bpy.data.objects['Lower | plain octagon']
ctrl = bpy.data.objects['SCENE SLIDERS']
control = ctrl.modifiers['Scene Sliders']
C = bpy.data.collections.new(COLLECTION)
S.collection.children.link(C)

# Derive the center from the real eight-sided slab, not its displaced origin.
foot = [lower.matrix_world @ v.co for v in list(lower.data.vertices)[8:]]
center = sum(foot, Vector()) / 8
roof_caps = [o for cn in ['162 | Octagon aligned workshop walls',
                        '163 | Opposite interior workshop walls']
             for o in bpy.data.collections[cn].objects if 'roof cassette' in o.name]
wall_z = max((o.matrix_world @ v.co).z for o in roof_caps for v in o.data.vertices)
RISE = 1.15
RADIUS = 1.46
origin = Vector((center.x, center.y, wall_z))
root = bpy.data.objects.new('Lower | circular roof assembly', None)
C.objects.link(root)
root.parent = lower
root.matrix_world = Matrix.Translation(origin)
root.empty_display_size = .13
root['description'] = 'Four planar roof slopes from the wall caps to a circular crown centered on the slab.'
root['wall_top_world_z'] = wall_z
root['light_radius_m'] = RADIUS

control_name = 'Light height above walls (m)'
socket = control.node_group.interface.new_socket(name=control_name, in_out='INPUT', socket_type='NodeSocketFloat')
socket.default_value = RISE
socket.min_value = .35
socket.max_value = 2.10
socket.description = 'Height of the circular crown above the wall caps. All four roof slopes stay connected to the walls.'
control[socket.identifier] = RISE
control_path = 'modifiers["Scene Sliders"]["' + socket.identifier + '"]'
root['height_control'] = control_name

def drive(owner, path, expression='h', index=None):
    fc = owner.driver_add(path) if index is None else owner.driver_add(path, index)
    d = fc.driver
    d.type = 'SCRIPTED'
    d.expression = expression
    v = d.variables.new()
    v.name = 'h'
    v.type = 'SINGLE_PROP'
    v.targets[0].id = ctrl
    v.targets[0].data_path = control_path

# The same height field moves the fixture rigidly, while only lifting the
# crown ends of the roof plates and ribs. Wall anchors always have weight 0.
g = bpy.data.node_groups.new('Lower | roof crown height deformation', 'GeometryNodeTree')
g.interface.new_socket(name='Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
g.interface.new_socket(name='Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
hs = g.interface.new_socket(name='Crown height', in_out='INPUT', socket_type='NodeSocketFloat')
hs.default_value = RISE
nodes, links = g.nodes, g.links
gi = nodes.new('NodeGroupInput')
go = nodes.new('NodeGroupOutput')
attr = nodes.new('GeometryNodeInputNamedAttribute')
attr.data_type = 'FLOAT'
attr.inputs['Name'].default_value = 'crown_height_weight'
delta = nodes.new('ShaderNodeMath')
delta.operation = 'SUBTRACT'
delta.inputs[1].default_value = RISE
links.new(gi.outputs['Crown height'], delta.inputs[0])
mul = nodes.new('ShaderNodeMath')
mul.operation = 'MULTIPLY'
links.new(delta.outputs[0], mul.inputs[0])
links.new(attr.outputs['Attribute'], mul.inputs[1])
vec = nodes.new('ShaderNodeCombineXYZ')
links.new(mul.outputs[0], vec.inputs['Z'])
sp = nodes.new('GeometryNodeSetPosition')
links.new(gi.outputs['Geometry'], sp.inputs['Geometry'])
links.new(vec.outputs[0], sp.inputs['Offset'])
links.new(sp.outputs[0], go.inputs['Geometry'])

def material(name, color, metal, rough, emission=0):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    p = m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value = (*color, 1)
    p.inputs['Metallic'].default_value = metal
    p.inputs['Roughness'].default_value = rough
    if emission:
        p.inputs['Emission Color'].default_value = (*color, 1)
        p.inputs['Emission Strength'].default_value = emission
    return m

roofmat = material('Lower | crown sloped graphite roof', (.042,.052,.061), .55, .43)
body = material('Lower | circular light blackened housing', (.018,.023,.030), .7, .36)
edge = material('Lower | circular light machined rim', (.071,.085,.101), .8, .32)
black = material('Lower | circular light recessed slots', (.006,.009,.013), .25, .51)
white = material('Lower | circular light cool white lenses', (.73,.88,1.0), .05, .24, 5.0)
made = []

def mesh(name, verts, faces, mat, weights=None, bevel=0):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.materials.append(mat)
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(me)
    bm.free()
    a = me.attributes.new('crown_height_weight', 'FLOAT', 'POINT')
    for v, w in zip(a.data, weights if weights is not None else [1.] * len(verts)):
        v.value = w
    o = bpy.data.objects.new(name, me)
    C.objects.link(o)
    o.parent = root
    mod = o.modifiers.new('Follow circular light height', 'NODES')
    mod.node_group = g
    mod[hs.identifier] = RISE
    drive(mod, '["' + hs.identifier + '"]')
    if bevel:
        b = o.modifiers.new('Fabricated edge radius', 'BEVEL')
        b.width = bevel
        b.segments = 3
        o.modifiers.new('Weighted metal normals', 'WEIGHTED_NORMAL')
    made.append(o)
    return o

def beam(name, a, b, width, depth, mat, wa=0, wb=1):
    a, b = Vector(a), Vector(b)
    axis = (b-a).normalized()
    u = axis.cross(Vector((0,0,1))).normalized() * width/2
    v = axis.cross(u).normalized() * depth/2
    pts = [p + u*x + v*y for p in (a,b) for x,y in [(-1,-1),(1,-1),(1,1),(-1,1)]]
    return mesh(name, pts, [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)], mat, [wa]*4+[wb]*4, .004)

def lathe(name, profile, mat, segments=160, start=0, sweep=math.tau, bevel=0):
    closed = abs(sweep-math.tau) < 1e-6
    count = segments if closed else segments+1
    verts = [(r*math.cos(start+sweep*i/segments), r*math.sin(start+sweep*i/segments), z)
             for r,z in profile for i in range(count)]
    faces = []
    for j in range(len(profile)):
        k = (j+1) % len(profile)
        for i in range(segments):
            ii = (i+1) % count
            faces.append((j*count+i,j*count+ii,k*count+ii,k*count+i))
    if not closed:
        faces.extend([tuple(j*count for j in reversed(range(len(profile)))),
                      tuple(j*count+count-1 for j in range(len(profile)))])
    o = mesh(name, verts, faces, mat, bevel=bevel)
    return o

def disk(name, radius, z0, z1, mat):
    n = 160
    verts = [(radius*math.cos(i*math.tau/n),radius*math.sin(i*math.tau/n),z)
             for z in (z0,z1) for i in range(n)]
    faces = [tuple(reversed(range(n))),tuple(range(n,2*n))]
    faces.extend((i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n))
    return mesh(name,verts,faces,mat,bevel=.009)

# The six small wall bays form four physical planes. Use full plane edges;
# coplanar bay dividers do not create additional roof slopes.
outline = [foot[i]-origin for i in (6,5,4,3,2)]
for p in outline:
    p.z = 0
# Uniform homothety preserves planarity of all four trapezoids and shared seams.
# Crown ends enter the housing slightly, so the circular lip hides the joins.
inner = [Vector((p.x*.29,p.y*.29,RISE-.025)) for p in outline]
labels = ['rear wall', 'rear corner', 'right wall', 'front return']
for i, label in enumerate(labels):
    a,b,c,d = outline[i],outline[i+1],inner[i+1],inner[i]
    top = [a,b,c,d]
    verts = top+[p-Vector((0,0,.075)) for p in top]
    o = mesh('Lower | roof slope %d - %s' % (i+1,label),verts,
             [(0,1,2,3),(7,6,5,4),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)],
             roofmat,[0,0,1,1,0,0,1,1],.008)
    o['roof_section'] = i+1
    o['wall_footprint_vertices'] = [6-i,5-i]
    o['wall_anchors_local'] = [list(a),list(b)]
    o['crown_anchors_local'] = [list(d),list(c)]
    # A quiet inset standing seam across the middle gives the large metal
    # planes scale, without dividing them into additional roof sections.
    aa = a.lerp(b,.5)+Vector((0,0,.013))
    bb = d.lerp(c,.5)+Vector((0,0,.013))
    beam('Lower | roof panel seam %d' % (i+1),aa,bb,.016,.010,body)
for i, (a,b) in enumerate(zip(outline,inner)):
    beam('Lower | roof joint rib %d' % (i+1),a+Vector((0,0,-.005)),b+Vector((0,0,-.005)),.075,.085,body)

# A shallow circular disc with a stepped metal casing and recessed underside.
# Only the separated rim lenses emit, following the reference's dark face.
disk('Lower | circular light upper cover',RADIUS-.045,RISE-.045,RISE+.022,roofmat)
lathe('Lower | circular light stepped rim',
      [(1.28,RISE-.055),(1.28,RISE-.205),(1.34,RISE-.245),(1.425,RISE-.245),
       (1.46,RISE-.205),(1.46,RISE-.075),(1.425,RISE-.020),(1.395,RISE+.010)],body,bevel=.005)
disk('Lower | circular light recessed underside',1.29,RISE-.194,RISE-.172,black)
lathe('Lower | circular light upper lip',[(1.405,RISE-.015),(1.448,RISE-.015),
      (1.448,RISE+.012),(1.405,RISE+.012)],edge,bevel=.003)
lathe('Lower | circular light bottom lip',[(1.315,RISE-.249),(1.417,RISE-.249),
      (1.433,RISE-.226),(1.315,RISE-.226)],edge,bevel=.003)
lathe('Lower | circular light inner reveal',[(1.15,RISE-.200),(1.22,RISE-.200),
      (1.22,RISE-.191),(1.15,RISE-.191)],body,bevel=.002)

for i in range(12):
    angle = i*math.tau/12
    span = math.radians(16)
    lathe('Lower | circular light pocket %02d' % (i+1),
          [(1.451,RISE-.210),(1.469,RISE-.210),(1.469,RISE-.133),(1.451,RISE-.133)],
          black,12,angle-span*.60,span*1.20,.003)
    lathe('Lower | circular white rim segment %02d' % (i+1),
          [(1.466,RISE-.196),(1.473,RISE-.196),(1.473,RISE-.154),(1.466,RISE-.154)],
          white,12,angle-span/2,span,.002)
    # Diffuser continuation under the lip casts light down into the workshop.
    lathe('Lower | circular underside lens %02d' % (i+1),
          [(1.325,RISE-.255),(1.40,RISE-.255),(1.40,RISE-.248),(1.325,RISE-.248)],
          white,12,angle-span/2,span,.001)
    # Fine dark breaks and screws in the upper casing, between the lenses.
    theta = angle+math.pi/12
    a = Vector((1.305*math.cos(theta),1.305*math.sin(theta),RISE+.026))
    b = Vector((1.415*math.cos(theta),1.415*math.sin(theta),RISE+.026))
    beam('Lower | circular cover seam %02d' % (i+1),a,b,.008,.007,black,1,1)

# An actual area source underneath the fixture gives a broad downward pool.
ld = bpy.data.lights.new('Lower | circular crown downlight','AREA')
ld.energy = 220
ld.shape = 'DISK'
ld.size = 2.50
ld.color = (.68,.83,1.0)
lo = bpy.data.objects.new(ld.name,ld)
C.objects.link(lo)
lo.parent = root
lo.location = (0,0,RISE-.27)
drive(lo,'location','h-0.27',2)

# Keep superseded objects recoverable, including their original mesh data.
hidden = []
for o in bpy.data.collections['160 | Reference aligned workshop architecture'].objects:
    if any(t in o.name for t in ('overhead hood','hood armor','overhead inset','fitted overhead pool')):
        o['replaced_by_circular_crown'] = True
        o.hide_set(True)
        o.hide_render = True
        hidden.append(o.name)

ctrl['How to use'] = 'Scene Sliders includes Light height above walls (m). The light stays centered and all four roof slopes keep their wall anchors.'
bpy.ops.object.select_all(action='DESELECT')
ctrl.select_set(True)
bpy.context.view_layer.objects.active = ctrl
bpy.context.view_layer.update()
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type == 'PROPERTIES':
            area.spaces.active.pin_id = ctrl
            area.spaces.active.use_pin_id = True
            try:
                area.spaces.active.context = 'MODIFIER'
            except TypeError:
                pass
ctrl.update_tag()
S.frame_set(S.frame_current)
bpy.context.view_layer.update()
readme = bpy.data.texts.new('READ ME - Circular roof light')
readme.write('SCENE SLIDERS > Modifiers > Scene Sliders > Light height above walls (m). Default 1.15 m; range 0.35 to 2.10 m. Changes the light height and all four roof planes together, with fixed wall anchors. The light is centered on the actual lower slab footprint, rather than its object origin. The old hood is hidden and preserved. Geometry Nodes and simple native drivers work without Python autorun.')
text = bpy.data.texts.new('build_circular_roof_light.py')
text.write(Path(__file__).read_text())
report = {'center_xy':list(center)[:2], 'wall_top_z':wall_z,
          'default_height_above_walls_m':RISE,'fixture_radius_m':RADIUS,
          'roof_slopes':4,'rim_light_segments':12,'new_meshes':len(made),
          'superseded_hidden':hidden,'control_socket':socket.identifier,
          'wall_anchors':[list(p+origin) for p in outline]}
(P/'build-report.json').write_text(json.dumps(report,indent=2))
result = report
