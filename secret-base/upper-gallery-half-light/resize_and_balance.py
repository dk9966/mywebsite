"""Halve the upper luminaire and balance the two wall returns in the live scene."""
import bpy, bmesh, array, hashlib, json
from pathlib import Path
from mathutils import Vector, Matrix

P = Path(__file__).resolve().parent
S = bpy.context.scene
assert bpy.context.mode == 'OBJECT'
deck = bpy.data.objects['Upper | beveled square gallery']
ctrl = bpy.data.objects['UPPER PLATFORM SLIDERS']
mod = ctrl.modifiers['Upper Platform Sliders']
root = bpy.data.objects['Upper light | adjustable fixture']
ROOF = bpy.data.collections['174 | Upper gallery connected roof']
WALLS = bpy.data.collections['173 | Upper gallery wall panels and bent ribs']
RAILS = bpy.data.collections['173 | Upper gallery exposed edge railings']
H, A = float(deck['deck_height_m']), float(deck['side_m']) / 2
UP = Vector((0, 0, 1))
names = {'b':'Upper corner bevel (m)', 'w':'Upper light width (m)',
         'd':'Upper light depth (m)', 'h':'Upper light height (m)',
         'c':'Upper light corner bevel (m)'}
sockets = {k:next(i for i in mod.node_group.interface.items_tree if i.name == n)
           for k,n in names.items()}
original = {k:float(mod[s.identifier]) for k,s in sockets.items()}
assert original['w'] > 3, 'This one-time update has already been applied.'
original_view = []
for area in bpy.context.screen.areas:
    if area.type == 'VIEW_3D':
        r = area.spaces.active.region_3d
        original_view.append({'location':list(r.view_location), 'rotation':list(r.view_rotation),
                              'distance':r.view_distance, 'perspective':r.view_perspective})
(P/'view-before.json').write_text(json.dumps(original_view))

def signature(o, evaluated=False):
    e = o.evaluated_get(bpy.context.evaluated_depsgraph_get()) if evaluated else o
    h = hashlib.sha256(repr(([list(r) for r in e.matrix_world],o.hide_render,
        o.hide_get(), o.parent.name if o.parent else None,
        sorted(c.name for c in o.users_collection))).encode())
    if e.type == 'MESH':
        data = e.data
        coords = array.array('f',[0]) * (3*len(data.vertices))
        data.vertices.foreach_get('co',coords); h.update(coords.tobytes())
        h.update(repr([tuple(p.vertices) for p in data.polygons]).encode())
        if not evaluated and data.shape_keys:
            for key in data.shape_keys.key_blocks:
                key.data.foreach_get('co',coords);h.update(coords.tobytes())
                h.update(repr((key.name,key.value,key.mute)).encode())
    return h.hexdigest()

def affected(o):
    return (o == ctrl or o.name.startswith(('Upper light |','Upper roof |',
            'Upper wall | bay 05 ', 'Upper wall | rib 06 ',
            'Upper exposed rail | span 00 ', 'Upper exposed rail | span 04 ',
            'Upper exposed rail | front wall terminal')))

protected = {o.name:signature(o) for o in S.objects if not affected(o)}
retained_walls = {o.name:signature(o,True) for o in WALLS.objects if not affected(o)}
(P/'protected-before.json').write_text(json.dumps(protected))
(P/'wall-positions-before.json').write_text(json.dumps(retained_walls))

# Keep the original outer left return as a recoverable, disabled collection.
archive = bpy.data.collections.new('Archive | upper gallery outer left return before balance')
S.collection.children.link(archive)
archive.hide_render = archive.hide_viewport = True
archived = []
def archive_object(o):
    for c in list(o.users_collection): c.objects.unlink(o)
    archive.objects.link(o); archived.append(o.name)

for o in list(WALLS.objects):
    if o.name.startswith(('Upper wall | bay 05 ', 'Upper wall | rib 06 ')):
        archive_object(o)

# Reflect the retained left return through the deck's local centerline.
mirrored = []
mirror = Matrix.Diagonal((1,-1,1,1))
for o in list(WALLS.objects):
    if o.name.startswith(('Upper wall | bay 04 ', 'Upper wall | rib 05 ')):
        n = o.copy(); n.data = o.data.copy()
        n.name = o.name.replace('bay 04 ', 'bay 06 ').replace('rib 05 ', 'rib 07 ')
        WALLS.objects.link(n)
        n.data.transform(mirror, shape_keys=True)
        n.data.flip_normals(); n.data.update()
        n['mirrored_from'] = o.name
        if 'wall_bay' in n: n['wall_bay'] = 6
        mirrored.append((o.name,n.name))

# Physical footprint is half as wide and deep. Corner cutback scales with it.
for k in ('w','d','c'):
    sockets[k].min_value = min(sockets[k].min_value, original[k]/2)
    mod[sockets[k].identifier] = original[k]/2
ctrl.update_tag(); S.frame_set(S.frame_current); bpy.context.view_layer.update()
base = {k:float(mod[s.identifier]) for k,s in sockets.items()}

PANEL = bpy.data.materials['Lower | aligned blue graphite panels']
TRIM = bpy.data.materials['Bridge | blue gunmetal panel frames']
STEEL = bpy.data.materials['Metal | dark structural steel']
EDGE = bpy.data.materials['Metal | machined edge highlights']
FACES = [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
updated = []

def mesh(name, geometry, material, collection, variables=('b',), bevel=.003):
    vs, fs = geometry(base)
    me = bpy.data.meshes.new(name+' | balanced geometry')
    me.from_pydata(vs,[],fs); me.materials.append(material); me.update()
    bm=bmesh.new();bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
    o=bpy.data.objects.get(name)
    if o is None:
        o=bpy.data.objects.new(name,me);collection.objects.link(o)
    else:
        o.data.use_fake_user=True; o.data=me
        for m in list(o.modifiers):o.modifiers.remove(m)
    o.parent=deck; o.matrix_parent_inverse=Matrix.Identity(4);o.matrix_basis=Matrix.Identity(4)
    for var in variables:
        alt=dict(base);alt[var]+=.01
        avs,_=geometry(alt)
        if max((Vector(a)-Vector(b)).length for a,b in zip(vs,avs))<1e-8:continue
        if not me.shape_keys:o.shape_key_add(name='Basis')
        key=o.shape_key_add(name='Follow '+var);key.slider_min=-10;key.slider_max=10
        for dst,a,b in zip(key.data,vs,avs):dst.co=Vector(a)+(Vector(b)-Vector(a))*100
        d=key.driver_add('value').driver;d.type='SCRIPTED';d.expression=var+'-'+repr(base[var])
        v=d.variables.new();v.name=var;v.type='SINGLE_PROP';v.targets[0].id=ctrl
        v.targets[0].data_path='modifiers["'+mod.name+'"]["'+sockets[var].identifier+'"]'
    if bevel:
        m=o.modifiers.new('Machined edge radius','BEVEL');m.width=bevel;m.segments=2
        o.modifiers.new('Weighted steel normals','WEIGHTED_NORMAL')
    o['upper_gallery_balanced_return']=True
    updated.append(o.name)
    return o

def wallpath(p,inset=0):
    a=A-.10-inset;c=p['b']-.03
    end=(a-c-1.25)/2
    return [Vector((end,-a,0)),Vector((a-c,-a,0)),Vector((a,-a+c,0)),
            Vector((a,0,0)),Vector((a,a-c,0)),Vector((a-c,a,0)),Vector((end,a,0))]

def inner(p):
    x,y=float(root.location.x),float(root.location.y)
    a,b,c=p['w']/2,p['d']/2,p['c']
    return [Vector(v) for v in [(x-a+c,y-b,0),(x+a-c,y-b,0),
            (x+a,y-b+c,0),(x+a,y,0),(x+a,y+b-c,0),(x+a-c,y+b,0),(x-a+c,y+b,0)]]

def roofgeo(p):
    outer=[q+UP*(H+2.115) for q in wallpath(p,.57)]
    ins=[q+UP*(H+p['h']+.105) for q in inner(p)]
    normals=[Vector(v).normalized() for v in [(0,-1,0),(1,-1,0),(1,-1,0),
                                             (1,0,0),(1,1,0),(1,1,0),(0,1,0)]]
    for j in range(7):ins[j]-=normals[j]*.012
    lower=outer+ins;vs=lower+[q+UP*.035 for q in lower];fs=[]
    for j in range(6):
        for a,b,c in [(j,j+1,8+j),(j,8+j,7+j)]:fs += [(c,b,a),(a+14,b+14,c+14)]
        fs += [(j,j+14,j+15,j+1),(8+j,22+j,21+j,7+j)]
    return vs,fs+[(0,7,21,14),(6,20,27,13)]

def beam(a,b,width,depth):
    t=(b-a).cross(UP).normalized();n=(b-a).normalized().cross(t).normalized()
    return [p+t*x*width/2+n*y*depth/2 for p in (a,b)
            for x,y in [(-1,-1),(1,-1),(1,1),(-1,1)]],FACES

mesh('Upper roof | continuous fitted crown panels',roofgeo,PANEL,ROOF,('b','w','d','h','c'),0)
for j in range(7):
    def joint(p,j=j):
        return beam(wallpath(p,.57)[j]+UP*(H+2.15),inner(p)[j]+UP*(H+p['h']+.147),.045,.04)
    mesh('Upper roof | panel joint %02d'%j,joint,TRIM,ROOF,('b','w','d','h','c'))
for j in (0,6):
    def fascia(p,j=j):
        return beam(wallpath(p,.57)[j]+UP*(H+2.12),inner(p)[j]+UP*(H+p['h']+.10),.06,.07)
    mesh('Upper roof | finished terminal fascia %02d'%j,fascia,TRIM,ROOF,('b','w','d','h','c'))

# Continue the exposed perimeter to the two new wall terminals.
def railpath(p):
    a=A-.075;c=p['b']-.025;end=(A-.10-(p['b']-.03)-1.25)/2-.10
    return [Vector(v) for v in [(end,a,0),(-a+c,a,0),(-a,a-c,0),
                                (-a,-a+c,0),(-a+c,-a,0),(end,-a,0)]]

def box(q,w,d,h):
    return [q+Vector((x*w/2,y*d/2,z*h/2)) for z in [-1,1]
            for x,y in [(-1,-1),(1,-1),(1,1),(-1,1)]],FACES

for edge in (0,4):
    for z in (.190,.345):
        mesh('Upper exposed rail | span %02d bar %.3f'%(edge,z),
             lambda p,e=edge,z=z:beam(railpath(p)[e]+UP*(H+z),railpath(p)[e+1]+UP*(H+z),.025,.018),
             STEEL,RAILS,bevel=.0015)
    for o in list(RAILS.objects):
        if o.name.startswith('Upper exposed rail | span %02d '%edge) and any(s in o.name for s in [' post ',' foot ']):
            if int(o.name.rsplit(' ',1)[-1]) >= 3:archive_object(o)
    for j in range(3):
        for label,z,w,d,h,mat in [('post',.177,.028,.028,.354,STEEL),('foot',.008,.052,.052,.024,EDGE)]:
            mesh('Upper exposed rail | span %02d %s %02d'%(edge,label,j),
                lambda p,e=edge,j=j,z=z,w=w,d=d,h=h:box(railpath(p)[e].lerp(railpath(p)[e+1],j/3)+UP*(H+z),w,d,h),
                mat,RAILS,bevel=.0015)
mesh('Upper exposed rail | front wall terminal',lambda p:box(railpath(p)[-1]+UP*(H+.177),.028,.028,.354),STEEL,RAILS,bevel=.0015)

ROOF['construction']='Continuous crown shell; one parallel wall return on each side; follows half-size adjustable luminaire.'
ctrl['How to resize light']='Modifiers > Upper Platform Sliders > Upper light width / depth. Roof follows while walls stay fixed.'
ctrl.update_tag();S.frame_set(S.frame_current);bpy.context.view_layer.update()
changed=[n for n,h in protected.items() if signature(bpy.data.objects[n])!=h]
wall_changed=[n for n,h in retained_walls.items() if signature(bpy.data.objects[n],True)!=h]
assert not changed,changed
assert not wall_changed,wall_changed
report={'before':original,'after':base,'protected_objects_unchanged':len(protected),
        'retained_wall_objects_unchanged':len(retained_walls),'mirrored':mirrored,
        'archived':archived,'updated':updated}
(P/'build-report.json').write_text(json.dumps(report,indent=2))
t=bpy.data.texts.get('upper_gallery_half_light.py') or bpy.data.texts.new('upper_gallery_half_light.py')
t.clear();t.write(Path(__file__).read_text())
bpy.ops.wm.save_as_mainfile(filepath=str(P/'half-light-candidate.blend'),copy=True)
result={k:v for k,v in report.items() if k not in ('mirrored','archived','updated')}
