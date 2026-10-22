"""Shorter shelves, longer mirrored braces, deeper channels and undershelf lights.

Run on the inspected live refinement. Preserve source meshes and parent transforms.
"""
import bpy, bmesh, hashlib, json
from mathutils import Vector
from pathlib import Path

P=Path('/Users/danielku/mywebsite/secret-base/support-bar-refinement')
S=bpy.context.scene
C=bpy.data.collections['164 | Symmetric supports and light ledges']
assert bpy.context.mode=='OBJECT'
assert not C.get('undershelf_revision')

def signature(o):
    return hashlib.sha256(repr(([list(r) for r in o.matrix_world],
        [tuple(v.co) for v in o.data.vertices],
        [tuple(f.vertices) for f in o.data.polygons])).encode()).hexdigest()

protected={o.name:signature(o) for o in S.objects
           if o.type=='MESH' and o.name not in C.objects}

def verts(o):return [o.matrix_world@v.co for v in o.data.vertices]
def center(o):return sum(verts(o),Vector())/len(o.data.vertices)

def edit(o,points):
    old=o.data;old.use_fake_user=True
    o['before_undershelf_mesh']=old.name
    o.data=old.copy();o.data.name=o.name+' | deeper channel revision'
    inv=o.matrix_world.inverted()
    for v,p in zip(o.data.vertices,points):v.co=inv@p
    o.data.update()

def box(o,origin,t,n,u,width,depth,height):
    edit(o,[origin+t*x*width/2+n*y*depth/2+u*z*height/2
            for z in (-1,1) for x,y in [(-1,-1),(1,-1),(1,1),(-1,1)]])

supports=[]
for o in sorted((o for o in C.objects if 'symmetric channeled support' in o.name),key=lambda o:o.name):
    old=bpy.data.objects[o['source_pier']]
    name=old.name
    edge_name=name.replace('upright pier','pier edge')
    n=(center(bpy.data.objects[edge_name])-center(old)).normalized()
    vs=verts(old);bottom=sum(vs[:4],Vector())/4;top=sum(vs[4:],Vector())/4
    u=(top-bottom).normalized();h=(top-bottom).length
    n=(n-u*n.dot(u)).normalized();t=n.cross(u).normalized()
    base=bottom-n*.045
    # Extend both angled ends equally and bring the raised side rails farther
    # forward than the gray ledges, keeping the original wall/floor anchors.
    stations=[(.015,.295,.110),(.450,.105,.088),
              (h-.450,.105,.088),(h-.015,.295,.110)]
    points=[]
    for z,depth,half in stations:
        inner=half*.60
        profile=[(-half,-.075),(half,-.075),(half,.065),(inner,.065),
                 (inner,-.025),(-inner,-.025),(-inner,.065),(-half,.065)]
        points.extend(base+u*z+t*x+n*(depth+y) for x,y in profile)
    edit(o,points)
    o['channel_depth']=.090;o['channel_width_at_shaft']=.1056
    o['top_bottom_mirrored']=True
    idx=o.name.rsplit(' ',1)[1]
    shoes=sorted([q for q in C.objects if q.name.startswith('Lower | support '+idx+' anchor shoe')],key=lambda q:center(q).dot(u))
    for shoe,z in zip(shoes,[.024,h-.024]):
        box(shoe,base+u*z+n*.15,t,n,u,.24,.435,.045)
    err=max(min((base+u*(h-(v-base).dot(u))+t*(v-base).dot(t)+n*(v-base).dot(n)-w).length
                for w in points) for v in points)
    supports.append({'name':o.name,'mirror_error':err,'channel_depth':.090,
                     'shaft_channel_width':.1056,'shaft_front':.170,
                     'angled_tip_front':.360,'angled_end_vertical_length':.435})

walls=[o for cn in ['162 | Octagon aligned workshop walls','163 | Opposite interior workshop walls']
       for o in bpy.data.collections[cn].objects if 'wall_section' in o]
ledges=[]
for i,wall in enumerate(walls):
    vs=verts(wall);a,b,c,d=vs[:4]
    t=(b-a).normalized();u=(d-a).normalized();n=(a-vs[4]).normalized()
    base=(a+b)/2-u*.035;prefix='Lower | '+wall['wall_section']
    ledge=bpy.data.objects[prefix+' gray light ledge']
    lamp=bpy.data.objects[prefix+' ledge lamp housing']
    lens=bpy.data.objects[prefix+' ledge light diffuser']
    oldwidth=max(v.dot(t) for v in verts(ledge))-min(v.dot(t) for v in verts(ledge))
    width=oldwidth-.14
    # The shelf now ends inside each support and projects only .125 from
    # the wall, behind the .170 front of the central support side rails.
    box(ledge,base+u*1.455+n*.0525,t,n,u,width,.145,.050)
    lampwidth=max(v.dot(t) for v in verts(lamp))-min(v.dot(t) for v in verts(lamp))
    lenswidth=max(v.dot(t) for v in verts(lens))-min(v.dot(t) for v in verts(lens))
    box(lamp,base+u*1.411+n*.075,t,n,u,lampwidth,.085,.038)
    box(lens,base+u*1.407+n*.120,t,n,u,lenswidth,.010,.022)
    # Keep the upper dark face a little behind the shelf as a readable step.
    upper=bpy.data.objects[prefix+' flat upper projection']
    upperwidth=max(v.dot(t) for v in verts(upper))-min(v.dot(t) for v in verts(upper))
    box(upper,base+u*1.7475+n*.0375,t,n,u,min(upperwidth,width),.105,.395)
    if wall.name.startswith('Lower | octagon'):
        suffix='' if i==0 else '.%03d'%i
        light=bpy.data.objects['Lower | octagon wall wash'+suffix]
    else:light=bpy.data.objects[wall.name+' wall wash']
    mx=light.matrix_world.copy();mx.translation=base+u*1.392+n*.145
    light.matrix_world=mx
    # Preserve the existing parent-space rotation; only the practical's
    # emission position needs to follow the undershelf diffuser.
    ledges.append({'bay':wall['wall_section'],'width_before':oldwidth,'width_after':width,
                   'ledge_front':.125,'support_front':.170,'ledge_bottom':1.430,
                   'lamp_top':1.430,'diffuser_top':1.418})

cap=bpy.data.materials['Lower | flat dark gray wall projections']
cap.diffuse_color=(.025,.029,.035,1)
bsdf=cap.node_tree.nodes.get('Principled BSDF')
bsdf.inputs['Base Color'].default_value=cap.diffuse_color
bsdf.inputs['Metallic'].default_value=.30
bsdf.inputs['Roughness'].default_value=.55
darkened_headers=[]
for cn in ['162 | Octagon aligned workshop walls','163 | Opposite interior workshop walls']:
    for o in bpy.data.collections[cn].objects:
        if 'roof fascia' in o.name or 'roof cassette' in o.name:
            o['before_dark_header_material']=o.data.materials[0].name
            # Object-linked override preserves the source mesh datablock.
            o.material_slots[0].link='OBJECT';o.material_slots[0].material=cap
            darkened_headers.append(o.name)

bpy.context.view_layer.update()
unchanged=all(signature(bpy.data.objects[n])==sig for n,sig in protected.items())
assert unchanged
assert all(s['mirror_error']<1e-5 for s in supports)
assert all(l['ledge_front']<l['support_front'] and l['diffuser_top']<l['ledge_bottom'] for l in ledges)
nonmanifold={}
for o in C.objects:
    bm=bmesh.new();bm.from_mesh(o.data)
    count=sum(not e.is_manifold for e in bm.edges);bm.free()
    if count:nonmanifold[o.name]=count
assert not nonmanifold
C['undershelf_revision']=True
report={'supports':supports,'ledges_and_lights':ledges,'darkened_headers':darkened_headers,
        'unrelated_meshes_and_transforms_preserved':unchanged,'non_manifold_edges':nonmanifold}
(P/'undershelf-verification.json').write_text(json.dumps(report,indent=2))
text=bpy.data.texts.new('adjust_ledges_and_channels.py');text.write(Path(__file__).read_text())
result=report
