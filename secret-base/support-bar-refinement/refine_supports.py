"""Refine the live workshop supports and the stepped wall-light surround.

Existing parts are retained hidden; all new geometry follows the live walls.
"""
import bpy, bmesh, hashlib, json
from pathlib import Path
from mathutils import Vector

P = Path('/Users/danielku/mywebsite/secret-base/support-bar-refinement')
S = bpy.context.scene
assert bpy.context.mode == 'OBJECT'
assert not bpy.data.collections.get('164 | Symmetric supports and light ledges')
C = bpy.data.collections.new('164 | Symmetric supports and light ledges')
S.collection.children.link(C)
lower = bpy.data.objects['Lower | plain octagon']
source_cols = [bpy.data.collections[n] for n in (
    '162 | Octagon aligned workshop walls', '163 | Opposite interior workshop walls')]
source_objects = [o for c in source_cols for o in c.objects]
piers = [o for o in source_objects if 'upright pier' in o.name]
walls = [o for o in source_objects if 'wall_section' in o]
assert len(piers) == 7 and len(walls) == 6

def signature(o):
    return hashlib.sha256(repr((list(map(list,o.matrix_world)),
        [tuple(v.co) for v in o.data.vertices],
        [tuple(f.vertices) for f in o.data.polygons])).encode()).hexdigest()

protected = {o.name:signature(o) for o in S.objects if o.type == 'MESH'}
made, hidden, symmetry_checks, ledge_checks = [], [], [], []

def material(name, color, metallic=.55, rough=.43):
    m=bpy.data.materials.new(name); m.use_nodes=True
    m.diffuse_color=(*color,1)
    bsdf=m.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value=(*color,1)
    bsdf.inputs['Metallic'].default_value=metallic
    bsdf.inputs['Roughness'].default_value=rough
    return m

trim=material('Lower | neutral gray channel supports',(.095,.108,.117))
recess=material('Lower | dark recessed support channels',(.029,.034,.040),.45,.5)
cap=material('Lower | flat dark gray wall projections',(.061,.069,.078),.45,.48)
shelf=material('Lower | gray lamp ledges',(.13,.145,.155),.50,.4)
white=bpy.data.materials['Lower | cool white practical diffuser']
steel=bpy.data.materials['Metal | dark structural steel']

def mesh(name, verts, faces, materials, bevel=.003):
    me=bpy.data.meshes.new(name)
    # Parent-local geometry keeps every part attached to the platform controls.
    inv=lower.matrix_world.inverted()
    me.from_pydata([inv@Vector(v) for v in verts],[],faces)
    for ma in materials: me.materials.append(ma)
    bm=bmesh.new();bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bm.to_mesh(me);bm.free();me.update()
    o=bpy.data.objects.new(name,me);C.objects.link(o);o.parent=lower
    if bevel:
        mod=o.modifiers.new('Small machined edge bevel','BEVEL')
        mod.width=bevel;mod.segments=2
        o.modifiers.new('Weighted face normals','WEIGHTED_NORMAL')
    made.append(o)
    return o

def box(name, center, t, n, u, width, depth, height, ma, bevel=.003):
    verts=[center+t*x*width/2+n*y*depth/2+u*z*height/2
           for z in (-1,1) for x,y in [(-1,-1),(1,-1),(1,1),(-1,1)]]
    return mesh(name,verts,[(0,3,2,1),(4,5,6,7),(0,1,5,4),
                          (1,2,6,5),(2,3,7,6),(3,0,4,7)],[ma],bevel)

def center(o):
    return sum((o.matrix_world@v.co for v in o.data.vertices),Vector())/len(o.data.vertices)

def hide(o):
    o.hide_set(True);o.hide_render=True;hidden.append(o.name)

for i,old in enumerate(piers):
    if old.name.startswith('Lower | octagon'):
        suffix=old.name.split('upright pier')[1]
        related=[bpy.data.objects['Lower | octagon '+n+suffix]
                 for n in ['pier edge','splayed pier foot','foot inset']]
    else:
        prefix=old.name.split('upright pier')[0]
        related=[bpy.data.objects[prefix+n] for n in ['pier edge','splayed pier foot','foot inset']]
    n=(center(related[0])-center(old)).normalized()
    vs=[old.matrix_world@v.co for v in old.data.vertices]
    bottom=sum(vs[:4],Vector())/4;top=sum(vs[4:],Vector())/4
    u=(top-bottom).normalized();h=(top-bottom).length
    n=(n-u*n.dot(u)).normalized();t=n.cross(u).normalized()
    base=bottom-n*.045
    # A continuous U section gives the middle an actual recessed channel.
    # The upper two stations mirror the lower two exactly across mid-height.
    stations=[(.025,.220,.110),(.350,.065,.088),
              (h-.350,.065,.088),(h-.025,.220,.110)]
    verts=[]
    for z,depth,half in stations:
        inner=half*.43
        profile=[(-half,-.075),(half,-.075),(half,.065),(inner,.065),
                 (inner,.014),(-inner,.014),(-inner,.065),(-half,.065)]
        verts.extend(base+u*z+t*x+n*(depth+y) for x,y in profile)
    faces=[tuple(reversed(range(8))),tuple(range(24,32))]
    for j in range(3):
        for k in range(8): faces.append((j*8+k,j*8+(k+1)%8,(j+1)*8+(k+1)%8,(j+1)*8+k))
    o=mesh('Lower | symmetric channeled support %02d'%(i+1),verts,faces,[trim,recess],.004)
    for j in range(3):
        for k in [3,4,5]:o.data.polygons[2+j*8+k].material_index=1
    o['channel_depth']=.051
    o['top_bottom_mirrored']=True
    o['source_pier']=old.name
    # Flush shoes terminate the mirrored braces against floor and lintel.
    for z in [.024,h-.024]:
        box('Lower | support %02d anchor shoe'%(i+1),base+u*z+n*.115,
            t,n,u,.24,.36,.045,trim)
    symmetry_error=max(min((base+u*(h-(v-base).dot(u))+
        t*(v-base).dot(t)+n*(v-base).dot(n)-w).length for w in verts) for v in verts)
    symmetry_checks.append({'support':o.name,'mirror_error':symmetry_error,
                            'channel_depth':.051})
    for ob in [old]+related:hide(ob)

for i,wall in enumerate(walls):
    vs=[wall.matrix_world@v.co for v in wall.data.vertices]
    a,b,c,d=vs[:4];t=(b-a).normalized();u=(d-a).normalized()
    n=(a-vs[4]).normalized();width=(b-a).length-.05
    base=(a+b)/2-u*.035
    label=wall['wall_section']
    if wall.name.startswith('Lower | octagon'):
        suffix='' if i==0 else '.%03d'%i
        names=['Lower | octagon '+q+suffix for q in ['strip light housing','white strip diffuser','wall wash']]
    else:
        names=[wall.name+' '+q for q in ['strip light housing','white strip diffuser','wall wash']]
    housing,lens,light=[bpy.data.objects[nm] for nm in names]
    lamp_width=max((v-w).length for v in [lens.matrix_world@q.co for q in lens.data.vertices]
                   for w in [lens.matrix_world@q.co for q in lens.data.vertices])
    prefix='Lower | '+label
    # Broad, flat upper face. The light sits on a separate lighter gray shelf.
    upper=box(prefix+' flat upper projection',base+u*1.7475+n*.0575,
              t,n,u,width,.145,.395,cap)
    ledge=box(prefix+' gray light ledge',base+u*1.455+n*.109,
              t,n,u,width,.248,.050,shelf)
    box(prefix+' ledge lamp housing',base+u*1.499+n*.184,
        t,n,u,lamp_width+.048,.093,.038,steel,.002)
    box(prefix+' ledge light diffuser',base+u*1.499+n*.234,
        t,n,u,lamp_width,.010,.022,white,.001)
    # Move the existing practical slightly forward so the new shelf does not
    # block its wall wash. Preserve its original light data and orientation.
    light_matrix=light.matrix_world.copy()
    light_matrix.translation += n*.16
    light.matrix_world=light_matrix
    hide(housing);hide(lens)
    ledge_checks.append({'bay':label,'upper_projection_bottom':1.55,
                         'lamp_center':1.499,'lamp_bottom':1.480,
                         'ledge_top':1.480,'ledge_front':.233,
                         'upper_projection_front':.130})

bpy.context.view_layer.update()
assert all(x['mirror_error']<1e-5 for x in symmetry_checks)
assert all(signature(bpy.data.objects[n])==sig for n,sig in protected.items())
non_manifold={}
for o in made:
    bm=bmesh.new();bm.from_mesh(o.data)
    count=sum(not e.is_manifold for e in bm.edges);bm.free()
    if count:non_manifold[o.name]=count
assert not non_manifold,non_manifold
report={'supports':symmetry_checks,'light_ledge_relationships':ledge_checks,
        'all_existing_meshes_preserved':True,'non_manifold_edges':non_manifold,
        'hidden_superseded_parts':hidden,'new_objects':len(made)}
(P/'verification.json').write_text(json.dumps(report,indent=2))
txt=bpy.data.texts.new('refine_supports.py');txt.write(Path(__file__).read_text())
result=report
