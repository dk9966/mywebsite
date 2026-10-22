"""Upper gallery: clipped rectangular luminaire and terrain-backed wall lining.

Run in the live scene once. All adjustments use native shape keys/drivers.
"""
import bpy, bmesh, math, json, hashlib
from pathlib import Path
from mathutils import Vector

P = Path(__file__).resolve().parent
S = bpy.context.scene
UP = Vector((0, 0, 1))
deck = bpy.data.objects['Upper | beveled square gallery']
terrain = bpy.data.objects['150 | continuous cave with oblique carved rooms']
ctrl = bpy.data.objects['SCENE SLIDERS']
controls = ctrl.modifiers['Scene Sliders']
F = deck.matrix_world.copy()
H = float(deck['deck_height_m'])
A = float(deck['side_m']) / 2
assert bpy.context.mode == 'OBJECT'
assert not bpy.data.collections.get('173 | Upper gallery architecture')

def signature(o):
    h = hashlib.sha256(repr(([list(r) for r in o.matrix_world], o.hide_render, o.hide_get(), o.parent.name if o.parent else None)).encode())
    if o.type == 'MESH':
        h.update(repr([tuple(v.co) for v in o.data.vertices]).encode())
        h.update(repr([m.name if m else None for m in o.data.materials]).encode())
    return h.hexdigest()

before = {o.name: signature(o) for o in S.objects}
(P / 'before-hashes.json').write_text(json.dumps(before))
COL = bpy.data.collections.new('173 | Upper gallery architecture')
S.collection.children.link(COL)
WALLS = bpy.data.collections.new('173 | Upper gallery wall panels and bent ribs')
RAILS = bpy.data.collections.new('173 | Upper gallery exposed edge railings')
LIGHT = bpy.data.collections.new('173 | Adjustable beveled rectangular light')
for collection in [WALLS, RAILS, LIGHT]:
    COL.children.link(collection)

STEEL = bpy.data.materials['Metal | dark structural steel']
PANEL = bpy.data.materials['Lower | aligned blue graphite panels']
TRIM = bpy.data.materials['Bridge | blue gunmetal panel frames']
EDGE = bpy.data.materials['Metal | machined edge highlights']
DARK = bpy.data.materials['Left bay | deep channel inset']
WHITE = bpy.data.materials['Lower | cool white practical diffuser']
AMBER = bpy.data.materials['Left bay | warm amber lenses']

paths = {}
defaults = {'b': .30, 'w': 3.70, 'd': 2.25, 'c': .60, 'h': 2.25}
for socket in controls.node_group.interface.items_tree:
    if socket.name == 'Upper corner bevel (m)':
        paths['b'] = 'modifiers["Scene Sliders"]["' + socket.identifier + '"]'
for name, var, lo, hi, desc in [
    ('Upper light width (m)', 'w', 2.4, 4.5, 'Outside width of the clipped rectangular housing. The diffuser and actual light follow.'),
    ('Upper light depth (m)', 'd', 1.4, 3.1, 'Outside depth of the clipped rectangular housing.'),
    ('Upper light height (m)', 'h', 1.8, 2.8, 'Height of the underside above the upper gallery floor. The nearby cave ceiling follows upward.'),
    ('Upper light corner bevel (m)', 'c', .30, .65, 'Cutback along each corner; 0.60 m gives prominent diagonal corners.'),
]:
    socket = controls.node_group.interface.new_socket(name=name, in_out='INPUT', socket_type='NodeSocketFloat')
    socket.default_value = defaults[var]
    socket.min_value, socket.max_value = lo, hi
    socket.description = desc
    controls[socket.identifier] = defaults[var]
    paths[var] = 'modifiers["Scene Sliders"]["' + socket.identifier + '"]'

def driver(owner, path, var, expression, index=None):
    fc = owner.driver_add(path) if index is None else owner.driver_add(path, index)
    d = fc.driver
    d.type = 'SCRIPTED'
    d.expression = expression
    v = d.variables.new()
    v.name, v.type = var, 'SINGLE_PROP'
    v.targets[0].id = ctrl
    v.targets[0].data_path = paths[var]
    return fc

root = bpy.data.objects.new('Upper light | adjustable fixture', None)
LIGHT.objects.link(root)
root.parent = deck
root.location = (-.35, -.10, H + defaults['h'])
driver(root, 'location', 'h', str(H) + '+h', 2)
root['controls'] = 'SCENE SLIDERS > Scene Sliders > Upper light width / depth / height / corner bevel'
root['height_reference'] = 'Underside above upper gallery floor'

FACES = [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
made = []

def mesh(name, geometry, mat, collection=WALLS, variables=('b',), bevel=.004, parent=None):
    vs, fs = geometry(defaults)
    vs = [Vector(v) for v in vs]
    me = bpy.data.meshes.new(name)
    me.from_pydata(vs, [], fs)
    me.materials.append(mat)
    me.update()
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.get(name)
    if o is None:
        o = bpy.data.objects.new(name, me)
        collection.objects.link(o)
    else:
        o.data = me
    o.parent = parent or deck
    if parent is None:
        o.matrix_world = F
    for var in variables:
        alt = dict(defaults); alt[var] += 1
        altvs, _ = geometry(alt)
        if max((Vector(v)-p).length for v,p in zip(altvs,vs)) < 1e-7:
            continue
        if not me.shape_keys:
            o.shape_key_add(name='Basis')
        key = o.shape_key_add(name='Follow ' + var)
        key.slider_min, key.slider_max = -4, 4
        for dst, v in zip(key.data, altvs):
            dst.co = v
        driver(key, 'value', var, var + '-' + str(defaults[var]))
    if bevel:
        mod = o.modifiers.get('Machined edge radius') or o.modifiers.new('Machined edge radius', 'BEVEL')
        mod.width, mod.segments = bevel, 2
        if not o.modifiers.get('Weighted steel normals'):o.modifiers.new('Weighted steel normals', 'WEIGHTED_NORMAL')
    o['upper_gallery_architecture'] = True
    made.append(o)
    return o

def boxgeo(center, t, n, width, depth, height):
    center,t,n = map(Vector,(center,t,n))
    return ([center+t*x*width/2+n*y*depth/2+UP*z*height/2
             for z in [-1,1] for x,y in [(-1,-1),(1,-1),(1,1),(-1,1)]], FACES)

def beamgeo(a,b,width,depth):
    a,b = Vector(a),Vector(b)
    axis = (b-a).normalized()
    t = axis.cross(UP if abs(axis.z)<.95 else Vector((0,1,0))).normalized()
    n = axis.cross(t).normalized()
    return ([p+t*x*width/2+n*y*depth/2 for p in [a,b]
             for x,y in [(-1,-1),(1,-1),(1,1),(-1,1)]],FACES)

def outline(a,b):
    return [Vector((x,y,0)) for x,y in [(-a+b,-a),(a-b,-a),(a,-a+b),(a,a-b),(a-b,a),(-a+b,a),(-a,a-b),(-a,-a+b)]]

# Wall footprint follows the existing platform bevel, including the diagonal turns.
# The rear wall stops at x=-1.25 where the cliff recedes from the platform edge.
def wallpath(p, inset=0):
    poly = outline(A-.10-inset, p['b']-.03)
    end = Vector((-1.25,A-.10-inset,0))
    return [poly[1], poly[2], poly[2].lerp(poly[3],.5), poly[3], poly[4], poly[4].lerp(end,.5), end]

stations = [(0.035,-.07),(.20,0), (1.36,0), (2.02,.45), (2.15,.59)]
def point(p, i, z, inset=0):
    q = wallpath(p,inset)[i].copy(); q.z = H+z
    return q

def normal(p,i):
    return (wallpath(p,0)[i]-wallpath(p,.1)[i]).normalized()

for i in range(7):
    # Narrow corner junctions keep the short diagonals legible.
    width = .10 if i in (1,4) else .205
    def rib(p, i=i, width=width):
        n=normal(p,i);t=Vector((-n.y,n.x,0))
        profile=[(-width/2,-.03),(width/2,-.03),(width/2,-.235),
                 (width*.24,-.235),(width*.24,-.085),(-width*.24,-.085),
                 (-width*.24,-.235),(-width/2,-.235)]
        vs=[point(p,i,z,ins)+t*x+n*y for z,ins in stations for x,y in profile]
        fs=[tuple(reversed(range(8))),tuple(range(32,40))]
        fs += [(k*8+j,k*8+(j+1)%8,(k+1)*8+(j+1)%8,(k+1)*8+j) for k in range(4) for j in range(8)]
        return vs,fs
    o=mesh('Upper wall | rib %02d bent channel'%i,rib,TRIM,bevel=.006)
    o['support_profile']='Continuous upright with a broad 45 degree upper bend and recessed central channel'
    o['support_index']=i
    def foot(p,i=i,width=width):
        n=normal(p,i);t=Vector((-n.y,n.x,0))
        return boxgeo(point(p,i,.031)-n*.13,t,n,width+.12,.43,.062)
    mesh('Upper wall | rib %02d floor anchor'%i,foot,EDGE,bevel=.006)
    for z in [.32,1.16]:
        for side in [-1,1]:
            def screw(p,i=i,z=z,side=side,width=width):
                n=normal(p,i);t=Vector((-n.y,n.x,0));center=point(p,i,z)+t*side*width*.36-n*.24
                vs=[center+n*d+t*math.cos(k*math.tau/6)*.013+UP*math.sin(k*math.tau/6)*.013 for d in [-.008,.008] for k in range(6)]
                return vs,[tuple(reversed(range(6))),tuple(range(6,12))]+[(k,(k+1)%6,(k+1)%6+6,k+6) for k in range(6)]
            mesh('Upper wall | rib %02d flange bolt %.2f %d'%(i,z,side),screw,EDGE,bevel=.001)
    if i not in (1,4):
        def marker(p,i=i):
            n=normal(p,i);t=Vector((-n.y,n.x,0))
            return boxgeo(point(p,i,.16)-n*.245,t,n,.055,.015,.053)
        mesh('Upper wall | rib %02d amber locator'%i,marker,AMBER,bevel=.003)

# Solid lining consists of separated lower, upper and inclined panel courses.
# Each panel is a closed prism, with clean visible seams and a recessed finish.
panel_stations=[(.045,0),(.68,0),(1.34,0),(2.005,.439),(2.13,.57)]
for bay in range(6):
    for row in range(4):
        z0,in0=panel_stations[row]; z1,in1=panel_stations[row+1]
        def panelgeo(p,bay=bay,z0=z0,z1=z1,in0=in0,in1=in1):
            a0,b0=point(p,bay,z0,in0),point(p,bay+1,z0,in0)
            a1,b1=point(p,bay,z1,in1),point(p,bay+1,z1,in1)
            t=(b0-a0).normalized();n=Vector((t.y,-t.x,0))
            # Clockwise wall route runs from front-right to back-left: outside is right.
            q=[a0+t*.013+UP*.007,b0-t*.013+UP*.007,b1-t*.013-UP*.007,a1+t*.013-UP*.007]
            vs=[v+n*d for d in [-.033,.062] for v in q]
            return vs,FACES
        obj=mesh('Upper wall | bay %02d panel course %02d'%(bay,row),panelgeo,PANEL,bevel=.004)
        obj['wall_bay']=bay
    for z,ins,label in [(.075,0,'floor skirting'),(2.13,.57,'angled crown header')]:
        mesh('Upper wall | bay %02d %s'%(bay,label),
             lambda p,bay=bay,z=z,ins=ins:beamgeo(point(p,bay,z,ins),point(p,bay+1,z,ins),.13,.075),TRIM,bevel=.004)
    if bay in (1,2,4,5):
        def vent(p,bay=bay):
            a,b=point(p,bay,1.10),point(p,bay+1,1.10)
            t=(b-a).normalized();n=Vector((t.y,-t.x,0));v,f=[],[]
            for j in range(4):
                vs,fs=boxgeo(a.lerp(b,.5)-n*.042+UP*j*.04,t,n,min(.56,(b-a).length*.48),.017,.009)
                k=len(v);v+=vs;f += [tuple(k+x for x in face) for face in fs]
            return v,f
        mesh('Upper wall | bay %02d recessed ventilation slots'%bay,vent,DARK,bevel=.001)

# Preserve the old railing as an archive, and make one continuous exposed run.
archive=bpy.data.collections.new('Archive | upper gallery all-edge railings')
S.collection.children.link(archive)
archived=[]
for o in list(bpy.data.collections['171 | Upper right square gallery'].objects):
    if any(word in o.name for word in ['continuous guardrail','railing upright','railing bolted shoe']):
        for c in list(o.users_collection):c.objects.unlink(o)
        archive.objects.link(o);archived.append(o.name)
archive.hide_render=archive.hide_viewport=True

def railpath(p):
    poly=outline(A-.075,p['b']-.025)
    # Terminate on the inner face of the support at the back and front ends.
    return [Vector((-1.35,A-.075,0)),poly[5],poly[6],poly[7],poly[0],poly[1]+Vector((-.11,0,0))]

for edge in range(5):
    for z in [.19,.345]:
        mesh('Upper exposed rail | span %02d bar %.3f'%(edge,z),
             lambda p,e=edge,z=z:beamgeo(railpath(p)[e]+UP*(H+z),railpath(p)[e+1]+UP*(H+z),.025,.018),
             STEEL,RAILS,bevel=.0015)
    # Count at the longest permitted edge length, ensuring safe spacing as bevel changes.
    num=max(1,math.ceil((railpath(defaults)[edge+1]-railpath(defaults)[edge]).length/.64))
    for j in range(num):
        t=j/num
        def post(p,e=edge,t=t):
            q=railpath(p)[e].lerp(railpath(p)[e+1],t)
            return boxgeo(q+UP*(H+.177),(1,0,0),(0,1,0),.028,.028,.354)
        def shoe(p,e=edge,t=t):
            q=railpath(p)[e].lerp(railpath(p)[e+1],t)
            return boxgeo(q+UP*(H+.008),(1,0,0),(0,1,0),.052,.052,.024)
        mesh('Upper exposed rail | span %02d post %02d'%(edge,j),post,STEEL,RAILS,bevel=.0015)
        mesh('Upper exposed rail | span %02d foot %02d'%(edge,j),shoe,EDGE,RAILS,bevel=.0015)
# Last terminal is supported by the architecture; add a small joining socket.
mesh('Upper exposed rail | front wall terminal',
     lambda p:boxgeo(railpath(p)[-1]+UP*(H+.177),(1,0,0),(0,1,0),.028,.028,.354),STEEL,RAILS,bevel=.0015)

# The rectangular housing and its strips are analytic in width, depth and cutback.
def lightpoly(p,inset=0):
    a,b=p['w']/2-inset,p['d']/2-inset
    c=p['c']-(2-math.sqrt(2))*inset
    return [Vector((x,y,0)) for x,y in [(-a+c,-b),(a-c,-b),(a,-b+c),(a,b-c),(a-c,b),(-a+c,b),(-a,b-c),(-a,-b+c)]]

def lightmesh(name,geo,mat,bevel=.004):
    return mesh('Upper light | '+name,geo,mat,LIGHT,('w','d','c'),bevel,root)

def ringgeo(p,outer,inner,z0,z1):
    vs=[v+UP*z for z in [z0,z1] for inset in [outer,inner] for v in lightpoly(p,inset)]
    fs=[]
    for i in range(8):
        j=(i+1)%8
        fs += [(i,j,16+j,16+i),(8+j,8+i,24+i,24+j),
               (j,i,8+i,8+j),(16+i,16+j,24+j,24+i)]
    return vs,fs

lightmesh('broad chamfered housing',lambda p:ringgeo(p,0,.19,.018,.16),TRIM,.008)
lightmesh('machined outer lip',lambda p:ringgeo(p,-.025,.015,.014,.049),EDGE,.003)
lightmesh('recessed diffuser gasket',lambda p:ringgeo(p,.036,.146,.002,.026),DARK,.002)
def centergeo(p):
    vs=[v+UP*z for z in [.075,.14] for v in lightpoly(p,.18)]
    return vs,[tuple(reversed(range(8))),tuple(range(8,16))]+[(i,(i+1)%8,(i+1)%8+8,i+8) for i in range(8)]
lightmesh('dark inset center plate',centergeo,STEEL,.008)
for i in range(8):
    def strip(p,i=i):
        poly=lightpoly(p,.09);a,b=poly[i],poly[(i+1)%8]
        t=(b-a).normalized();gap=min(.095,(b-a).length*.12)
        return beamgeo(a+t*gap+UP*.002,b-t*gap+UP*.002,.067,.020)
    lightmesh('cool white perimeter diffuser %02d'%i,strip,WHITE,.003)
for x in [-1,1]:
    def spine(p,x=x):
        q=x*(p['w']/2-.82)
        return beamgeo((q,-p['d']/2+.35,.151),(q,p['d']/2-.35,.151),.032,.027)
    lightmesh('upper stiffening rib %d'%x,spine,STEEL,.003)

ld=bpy.data.lights.new('Upper light | rectangular downlight','AREA')
lo=bpy.data.objects.new(ld.name,ld);LIGHT.objects.link(lo);lo.parent=root
lo.location=(0,0,-.035);ld.shape='RECTANGLE';ld.energy=230;ld.color=(.72,.86,1.)
driver(ld,'size','w','w-0.30');driver(ld,'size_y','d','d-0.30')

# Local, reversible headroom adjustment. Raise the existing upper roof only;
# preserve floor contact and the surrounding gallery's lower walls.
topology_mods=[m for m in terrain.modifiers if m.type=='DECIMATE' or m.name=='Between platforms | soften shallow rock facets']
states=[m.show_viewport for m in topology_mods]
try:
    for m in topology_mods:m.show_viewport=False
    bpy.context.view_layer.update()
    ev=terrain.evaluated_get(bpy.context.evaluated_depsgraph_get())
    assert len(ev.data.vertices)==len(terrain.data.vertices)
    evaluated_points=[v.co.copy() for v in ev.data.vertices]
finally:
    for m,state in zip(topology_mods,states):m.show_viewport=state
    bpy.context.view_layer.update()
mx=F.inverted()@terrain.matrix_world;im=mx.inverted().to_3x3()
def smooth(t):
    t=max(0,min(1,t));return t*t*(3-2*t)
base=terrain.data.shape_keys.key_blocks['Basis']
room=terrain.shape_key_add(name='Upper gallery | lining and fixture headroom')
follow=terrain.shape_key_add(name='Upper gallery | adjustable light ceiling clearance')
changed=0;max_lift=0
for i,v in enumerate(evaluated_points):
    p=mx@v;z=p.z-H
    xy=smooth((4.05-max(abs(p.x+.15),abs(p.y)))/.90)
    weight=xy*smooth((z-1.32)/.62)*(1-smooth((z-3.7)/1.4))
    lift=.70*weight
    room.data[i].co=base.data[i].co+im@Vector((0,0,lift))
    follow.data[i].co=base.data[i].co+im@Vector((0,0,weight))
    changed+=lift>1e-6;max_lift=max(max_lift,lift)
room.value=1
follow.slider_min=0;follow.slider_max=2
driver(follow,'value','h','max(0,h-2.25)')

ctrl['Upper gallery light controls']='Upper light width, depth, height and corner bevel (m). Native drivers; works after reopening without autorun.'
COL['layout']='Wall lining: right side, right-hand corners, and rear edge x >= -1.25. Railings: only remaining exposed perimeter.'
COL['reference']='Broad clipped rectangular overhead light; repeated bent channel wall frames with panels between.'
ctrl.update_tag();S.frame_set(S.frame_current);bpy.context.view_layer.update()
protected_changes=[n for n,h in before.items() if n not in archived and n!=terrain.name and signature(bpy.data.objects[n])!=h]
assert not protected_changes, protected_changes
report={'objects_added':len(made)+2,'archived_railings':archived,'wall_bays':6,'wall_ribs':7,
        'light_defaults':defaults,'control_paths':paths,'local_roof_vertices_lifted':changed,
        'maximum_roof_lift_m':max_lift,'protected_objects_unchanged':len(before)-len(archived),
        'frame':[list(r) for r in F],'deck_height':H}
(P/'build-report.json').write_text(json.dumps(report,indent=2))
txt=bpy.data.texts.new('upper_gallery_architecture.py');txt.write(Path(__file__).read_text())
bpy.ops.wm.save_as_mainfile(filepath=str(P/'architecture-candidate.blend'),copy=True)
result={k:v for k,v in report.items() if k not in ['archived_railings','frame']}
