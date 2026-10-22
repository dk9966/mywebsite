"""Pull the existing right reveal and lower shoulder forward, reversibly."""
import bpy, json, hashlib, math
from pathlib import Path
from mathutils import Vector

P = Path(__file__).resolve().parent
w = bpy.data.objects['150 | continuous cave with oblique carved rooms']
deck = bpy.data.objects['Upper | beveled square gallery']
KEY = 'Upper right | pulled forward continuous rock'
MOD = 'Upper right | continuous forward rock fit'
assert bpy.context.mode == 'OBJECT'

def fingerprint(o):
    h = hashlib.sha256(repr(([list(r) for r in o.matrix_world], o.hide_render, o.hide_get(), o.parent.name if o.parent else None)).encode())
    if o.type == 'MESH':
        h.update(repr([tuple(v.co) for v in o.data.vertices]).encode())
    return h.hexdigest()

if not (P / 'protected-before.json').exists():
    (P / 'protected-before.json').write_text(json.dumps({o.name: fingerprint(o) for o in bpy.context.scene.objects if o != w}))
if 'forward_rock_source_mesh' not in w:
    w.data.use_fake_user = True
    w['forward_rock_source_mesh'] = w.data.name
    w.data = w.data.copy()
    w.data.name = 'Cave | forward fitted upper reveal and shoulder'

key = w.data.shape_keys.key_blocks.get(KEY)
if key:
    key.value = 0
    bpy.context.view_layer.update()
oldmod=w.modifiers.get(MOD)
if oldmod:
    oldmod.show_viewport=False
    bpy.context.view_layer.update()
mx = deck.matrix_world.inverted() @ w.matrix_world
imx = mx.inverted().to_3x3()
ev = w.evaluated_get(bpy.context.evaluated_depsgraph_get())
assert len(ev.data.vertices) == len(w.data.vertices)
coords = [mx @ v.co for v in ev.data.vertices]
basis = w.data.shape_keys.key_blocks[0]
if not key:
    key = w.shape_key_add(name=KEY, from_mix=False)
key.relative_key = basis

def smooth(t):
    t = max(0., min(1., t))
    return t*t*(3.-2.*t)

def side_target(y,z):
    relief=.14*math.sin(z*1.9+y*.8)+.11*math.sin(y*2.0-z*.9)
    target=-.40+.22*(z-12.0)+relief+2.15*smooth((y+3.80)/.80)
    return max(target,4.74+y) if y>-3.06 else target

changed = []
new = []
weights = []
for i,p in enumerate(coords):
    x,y,z = p
    # Broad pull across the recessed right-hand reveal. It stays outside
    # the metal gallery edge and fades into the untouched surrounding cliff.
    side = smooth((-2.82-y)/.18) * smooth((y+6.4)/1.05)
    high = smooth((z-9.25)/.95) * smooth((14.75-z)/1.60)
    depth = smooth((x+2.8)/1.2)*smooth((6.3-x)/2.0)
    target = side_target(y,z)
    upper_pull = (x-target) * side * high * depth
    # Thicken the adjoining slope below the deck without moving its bearing
    # edge or the lower roof-contact anchors.
    band = smooth((z-9.15)/.65) * smooth((11.39-z)/.60)
    span = smooth((y+5.7)/1.15) * smooth((2.1-y)/1.5)
    front = smooth((x+3.5)/1.0)*smooth((3.0-x)/1.6)
    shoulder_target = -1.25 + .8*smooth((10.3-z)/.9)
    lower_pull = max(0., x-shoulder_target) * band * span * front
    amount = max(upper_pull, lower_pull) if z<11.39 else upper_pull
    new.append(p-Vector((amount,0,0)))
    weights.append(max(side*high*depth,band*span*front))

# Relax the existing folded reveal in depth, retaining the rock outline,
# platform contact heights, and native topology.
neighbors = [[] for p in coords]
for edge in w.data.edges:
    a,b = edge.vertices
    neighbors[a].append(b)
    neighbors[b].append(a)
active=[i for i,weight in enumerate(weights) if weight>.001 and neighbors[i]]
for step in range(30):
    updates=[]
    for i in active:
        p=new[i]
        average = sum((new[j] for j in neighbors[i]),Vector())/len(neighbors[i])
        delta=(average-p)*.48*weights[i]
        # Blend the squeezed fold rows into a broad natural face.
        updates.append((i,delta))
    for i,delta in updates:
        new[i] += delta
for i,q in enumerate(new):
    x,y,z=coords[i]
    side=smooth((-2.82-y)/.18)*smooth((y+6.4)/1.05)
    high=smooth((z-10.65)/.70)*smooth((14.75-z)/1.60)
    depth=smooth((x+2.8)/1.2)*smooth((6.3-x)/2.0)
    target=side_target(q.y,q.z)
    wt=side*high*depth
    q.x=q.x*(1-wt)+target*wt
candidate=[(i,(q-p).length) for i,(p,q) in enumerate(zip(coords,new)) if (q-p).length>1e-6]
assert max(distance for i,distance in candidate)<3.1, 'Reject oversized displacement'
assert all(-3.51<=coords[i].x<=6.31 and -6.41<=coords[i].y<=2.11 and 9.14<=coords[i].z<=14.76 for i,distance in candidate), 'Reject edit outside marked rock region'
attr=w.data.attributes.get('upper_forward_rock_delta') or w.data.attributes.new('upper_forward_rock_delta','FLOAT_VECTOR','POINT')
for i,p in enumerate(coords):
    delta = imx @ (new[i]-p)
    key.data[i].co = basis.data[i].co + delta
    attr.data[i].vector=delta
    if delta.length > 1e-6:
        changed.append((i, delta.length))

key.value = 0.
# Apply the stored local sculpt after the pre-existing height/contact fields;
# otherwise those fields re-project the moved vertices into thin folds.
if oldmod:
    mod=oldmod
else:
    group=bpy.data.node_groups.new(MOD,'GeometryNodeTree')
    group.interface.new_socket(name='Geometry',in_out='INPUT',socket_type='NodeSocketGeometry')
    group.interface.new_socket(name='Geometry',in_out='OUTPUT',socket_type='NodeSocketGeometry')
    amount=group.interface.new_socket(name='Forward fit',in_out='INPUT',socket_type='NodeSocketFloat')
    amount.default_value=1.;amount.min_value=0.;amount.max_value=1.
    n,l=group.nodes,group.links
    gi=n.new('NodeGroupInput');go=n.new('NodeGroupOutput')
    at=n.new('GeometryNodeInputNamedAttribute');at.data_type='FLOAT_VECTOR';at.inputs['Name'].default_value='upper_forward_rock_delta'
    sc=n.new('ShaderNodeVectorMath');sc.operation='SCALE'
    l.new(at.outputs['Attribute'],sc.inputs[0]);l.new(gi.outputs['Forward fit'],sc.inputs['Scale'])
    sp=n.new('GeometryNodeSetPosition')
    l.new(gi.outputs['Geometry'],sp.inputs['Geometry']);l.new(sc.outputs['Vector'],sp.inputs['Offset']);l.new(sp.outputs[0],go.inputs['Geometry'])
    mod=w.modifiers.new(MOD,'NODES');mod.node_group=group;mod[amount.identifier]=1.
mod.show_viewport=True
mod.show_render=True
w.data.update()
bpy.context.view_layer.update()
report = {'shape_key': KEY, 'changed_vertices': len(changed), 'max_displacement_m': max(v for i,v in changed), 'local_subdivision': bool(w.get('forward_patch_subdivided'))}
(P / 'edit-report.json').write_text(json.dumps(report, indent=2))
result = report
