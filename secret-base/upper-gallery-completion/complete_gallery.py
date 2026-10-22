"""Complete the upper gallery in the live scene; keep native slider drivers."""
import bpy, bmesh, math, json, hashlib
from pathlib import Path
from mathutils import Vector, Matrix

P = Path(__file__).resolve().parent
S = bpy.context.scene
deck = bpy.data.objects['Upper | beveled square gallery']
ctrl = bpy.data.objects['UPPER PLATFORM SLIDERS']
mod = ctrl.modifiers['Upper Platform Sliders']
root = bpy.data.objects['Upper light | adjustable fixture']
F = deck.matrix_world.copy()
H, A = float(deck['deck_height_m']), float(deck['side_m']) / 2
UP = Vector((0, 0, 1))
names = {'b':'Upper corner bevel (m)', 'w':'Upper light width (m)',
         'd':'Upper light depth (m)', 'h':'Upper light height (m)',
         'c':'Upper light corner bevel (m)'}
ids = {k:next(i.identifier for i in mod.node_group.interface.items_tree if i.name == n)
       for k,n in names.items()}
before_values = {k:float(mod[i]) for k,i in ids.items()}
if (P/'build-report.json').exists():
    before_values = json.loads((P/'build-report.json').read_text())['original_controls']

def signature(o):
    h = hashlib.sha256(repr(([list(r) for r in o.matrix_world], o.hide_render,
                              o.parent.name if o.parent else None)).encode())
    if o.type == 'MESH':
        h.update(repr([tuple(v.co) for v in o.data.vertices]).encode())
        if o.data.shape_keys:
            for key in o.data.shape_keys.key_blocks:
                h.update(repr((key.name, key.value, [tuple(v.co) for v in key.data])).encode())
    return h.hexdigest()

def is_target(o):
    return o.name.startswith(('Upper wall | rib ', 'Upper light |', 'Upper roof |')) or o == ctrl

before = {o.name:signature(o) for o in S.objects if not is_target(o)}
(P/'protected-before.json').write_text(json.dumps(before))
mod[ids['w']] = 3.70
mod[ids['d']] = 2.25
ctrl.update_tag(); S.frame_set(S.frame_current); bpy.context.view_layer.update()
base = {k:float(mod[i]) for k,i in ids.items()}
WALLS = bpy.data.collections['173 | Upper gallery wall panels and bent ribs']
ARCH = bpy.data.collections['173 | Upper gallery architecture']
ROOF = bpy.data.collections.get('174 | Upper gallery connected roof')
if ROOF is None:
    ROOF = bpy.data.collections.new('174 | Upper gallery connected roof')
    ARCH.children.link(ROOF)
STEEL = bpy.data.materials['Metal | dark structural steel']
TRIM = bpy.data.materials['Bridge | blue gunmetal panel frames']
EDGE = bpy.data.materials['Metal | machined edge highlights']
PANEL = bpy.data.materials['Lower | aligned blue graphite panels']
DARK = bpy.data.materials['Left bay | deep channel inset']
AMBER = bpy.data.materials['Left bay | warm amber lenses']
FACES = [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
made = []
geometries = {}

def driver(key, var):
    fc = key.driver_add('value'); d = fc.driver; d.type = 'SCRIPTED'
    d.expression = var + '-' + repr(base[var])
    v = d.variables.new(); v.name = var; v.type = 'SINGLE_PROP'
    v.targets[0].id = ctrl
    v.targets[0].data_path = 'modifiers["'+mod.name+'"]["'+ids[var]+'"]'

def mesh(name, geometry, material, collection=WALLS, variables=('b',), bevel=.004):
    vs, fs = geometry(base)
    me = bpy.data.meshes.new(name + ' | uniform geometry')
    me.from_pydata(vs, [], fs); me.materials.append(material); me.update()
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces)); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.get(name)
    if o is None:
        o = bpy.data.objects.new(name, me); collection.objects.link(o)
    else:
        old = o.data
        old.use_fake_user = True
        o.data = me
        for m in list(o.modifiers): o.modifiers.remove(m)
    o.parent = deck; o.matrix_parent_inverse = Matrix.Identity(4); o.matrix_basis = Matrix.Identity(4)
    for var in variables:
        alt = dict(base); alt[var] += 1
        avs, _ = geometry(alt)
        if max((Vector(a)-Vector(b)).length for a,b in zip(vs, avs)) < 1e-7: continue
        if not me.shape_keys: o.shape_key_add(name='Basis')
        key = o.shape_key_add(name='Follow '+var); key.slider_min = -10; key.slider_max = 10
        for dst,v in zip(key.data, avs): dst.co = v
        driver(key, var)
    if bevel:
        m=o.modifiers.new('Machined edge radius','BEVEL'); m.width=bevel; m.segments=2
        o.modifiers.new('Weighted steel normals','WEIGHTED_NORMAL')
    o['upper_gallery_completion'] = True
    made.append(o); geometries[name] = geometry
    return o

def box(c,t,n,w,d,h):
    return ([c+t*x*w/2+n*y*d/2+UP*z*h/2 for z in [-1,1]
             for x,y in [(-1,-1),(1,-1),(1,1),(-1,1)]], FACES)

def beam(a,b,width,depth):
    axis=(b-a).normalized(); t=axis.cross(UP).normalized(); n=axis.cross(t).normalized()
    return ([p+t*x*width/2+n*y*depth/2 for p in [a,b]
             for x,y in [(-1,-1),(1,-1),(1,1),(-1,1)]],FACES)

def wallpath(p, inset=0):
    a=A-.10-inset; c=p['b']-.03
    q=[Vector((a-c,-a,0)),Vector((a,-a+c,0)),Vector((a,0,0)),
       Vector((a,a-c,0)),Vector((a-c,a,0))]
    end=Vector((-1.25,a,0))
    return q+[q[4].lerp(end,.5),end]

def support(p,i):
    q=wallpath(p)
    if i in (0,1):
        t=(q[1]-q[0]).normalized(); v=q[i]+t*(.02 if i==0 else -.16)
    elif i==2:
        t=Vector((0,1,0)); v=q[2]
    elif i in (3,4):
        t=(q[4]-q[3]).normalized(); v=q[i]+t*(.16 if i==3 else -.16)
    else:
        t=Vector((-1,0,0)); v=q[5] if i==5 else q[6]
    n=Vector((t.y,-t.x,0))
    return v,t,n

WIDTH=.22
GAP=.104
stations=[(.057,0),(.22,0),(1.36,0),(2.02,.45),(2.15,.59)]
def ribgeo(p,i):
    q,t,n=support(p,i); factor=abs(n.x)+abs(n.y)
    profile=[(-WIDTH/2,-.028),(WIDTH/2,-.028),(WIDTH/2,-.24),
             (GAP/2,-.24),(GAP/2,-.087),(-GAP/2,-.087),
             (-GAP/2,-.24),(-WIDTH/2,-.24)]
    vs=[q+UP*(H+z)-n*ins*factor+t*x+n*y for z,ins in stations for x,y in profile]
    fs=[tuple(reversed(range(8))),tuple(range(32,40))]
    fs += [(k*8+j,k*8+(j+1)%8,(k+1)*8+(j+1)%8,(k+1)*8+j) for k in range(4) for j in range(8)]
    return vs,fs

for i in range(7):
    prefix='Upper wall | rib %02d '%i
    obj=mesh(prefix+'bent channel',lambda p,i=i:ribgeo(p,i),TRIM,bevel=.004)
    obj['support_index_left_to_right']=7-i
    obj['wall_number_left_to_right']={6:1,5:1,4:2,3:2,2:3,1:4,0:4}[i]
    obj['channel_gap_m']=GAP; obj['channel_width_m']=WIDTH
    obj['support_profile']='Identical 220 mm bent channels; 104 mm clear recess; normal aligned to assigned wall face'
    def part(p,i,z,offset,w,d,h):
        q,t,n=support(p,i)
        return box(q+UP*(H+z)+n*offset,t,n,w,d,h)
    mesh(prefix+'floor anchor',lambda p,i=i:part(p,i,.029,-.126,.36,.46,.058),EDGE,bevel=.005)
    mesh(prefix+'seated base socket',lambda p,i=i:part(p,i,.113,-.132,.268,.272,.122),TRIM,bevel=.009)
    mesh(prefix+'locator housing',lambda p,i=i:part(p,i,.194,-.244,.114,.073,.112),STEEL,bevel=.007)
    mesh(prefix+'locator gasket',lambda p,i=i:part(p,i,.194,-.282,.084,.012,.079),DARK,bevel=.004)
    mesh(prefix+'amber locator',lambda p,i=i:part(p,i,.194,-.289,.059,.012,.052),AMBER,bevel=.004)
    for z in [.32,1.16]:
        for side in [-1,1]:
            def bolt(p,i=i,z=z,side=side):
                q,t,n=support(p,i); c=q+UP*(H+z)+t*side*.082-n*.244
                vs=[c+n*d+t*math.cos(k*math.tau/6)*.011+UP*math.sin(k*math.tau/6)*.011
                    for d in [-.008,.008] for k in range(6)]
                return vs,[tuple(reversed(range(6))),tuple(range(6,12))]+[(k,(k+1)%6,(k+1)%6+6,k+6) for k in range(6)]
            mesh(prefix+'flange bolt %.2f %d'%(z,side),bolt,EDGE,bevel=.001)
    for side in [-1,1]:
        def anchor(p,i=i,side=side):
            q,t,n=support(p,i)
            return box(q+t*side*.139-n*.28+UP*(H+.064),t,n,.028,.034,.017)
        mesh(prefix+'foot fastener %d'%side,anchor,STEEL,bevel=.003)

# Crown and luminaire rings share the exact roof boundary, including the four turns.
def inner(p):
    x,y=float(root.location.x),float(root.location.y)
    a,b,c=p['w']/2,p['d']/2,p['c']
    q=[Vector((x+a-c,y-b,0)),Vector((x+a,y-b+c,0)),
       Vector((x+a,y,0)),Vector((x+a,y+b-c,0)),Vector((x+a-c,y+b,0))]
    end=Vector((-1.25,y+b,0))
    return q+[q[4].lerp(end,.5),end]

def roofgeo(p):
    outer=[q+UP*(H+2.115) for q in wallpath(p,.57)]
    ins=[q+UP*(H+p['h']+.105) for q in inner(p)]
    # 12 mm insertion into the lamp's structural ring, beneath its top surface.
    normals=[Vector((1,-1,0)).normalized(),Vector((1,-1,0)).normalized(),
             Vector((1,0,0)),Vector((1,1,0)).normalized(),
             Vector((1,1,0)).normalized(),Vector((0,1,0)),Vector((0,1,0))]
    for j in range(7): ins[j]-=normals[j]*.012
    lower=outer+ins
    vs=lower+[q+UP*.035 for q in lower]
    fs=[]
    for j in range(6):
        # Split non-planar roof sections into triangles, with a watertight shared edge.
        for a,b,c in [(j,j+1,7+j+1),(j,7+j+1,7+j)]:
            fs += [(c,b,a),(a+14,b+14,c+14)]
        fs += [(j,j+14,j+15,j+1),(7+j+1,21+j+1,21+j,7+j)]
    fs += [(0,7,21,14),(6,20,27,13)]
    return vs,fs

mesh('Upper roof | continuous fitted crown panels',roofgeo,PANEL,ROOF,('b','w','d','h','c'),bevel=0)
for j in range(7):
    def roofrib(p,j=j):
        a=wallpath(p,.57)[j]+UP*(H+2.15)
        b=inner(p)[j]+UP*(H+p['h']+.147)
        return beam(a,b,.045,.04)
    mesh('Upper roof | panel joint %02d'%j,roofrib,TRIM,ROOF,('b','w','d','h','c'),bevel=.003)
for j in [0,6]:
    def fascia(p,j=j):
        a=wallpath(p,.57)[j]+UP*(H+2.12)
        b=inner(p)[j]+UP*(H+p['h']+.10)
        return beam(a,b,.06,.07)
    mesh('Upper roof | finished terminal fascia %02d'%j,fascia,TRIM,ROOF,('b','w','d','h','c'),bevel=.003)

ROOF['construction']='Continuous closed roof shell fitted from the four wall crowns into the enlarged light frame'
ROOF['native_controls']='Upper Platform Sliders: bevel, lamp width, depth, height and corner cutback'
ctrl.update_tag(); S.frame_set(S.frame_current); bpy.context.view_layer.update()
changed=[name for name,digest in before.items() if signature(bpy.data.objects[name])!=digest]
assert not changed,changed
report={'original_controls':before_values,'finished_controls':base,'support_count':7,
        'left_to_right_wall_mapping':[1,1,2,2,3,4,4], 'channel_width_m':WIDTH,
        'channel_gap_m':GAP,'all_base_plate_dimensions_m':[.36,.46,.058],
        'protected_objects_unchanged':len(before),'created_or_updated_objects':len(made)}
(P/'build-report.json').write_text(json.dumps(report,indent=2))
t=bpy.data.texts.get('complete_upper_gallery.py') or bpy.data.texts.new('complete_upper_gallery.py')
t.clear();t.write(Path(__file__).read_text())
bpy.ops.wm.save_as_mainfile(filepath=str(P/'completed-gallery.blend'),copy=True)
result=report
