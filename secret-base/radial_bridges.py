"""Make each bridge radial at its existing Projects rim entrance; remove baked titles."""
import bpy, bmesh, math
from mathutils import Matrix, Vector
scene=bpy.context.scene
project=bpy.data.objects['island_pillar_project'];origin=project.matrix_world.translation.copy()
WIDTH=.923;RP=2.712;F=6.871178627
portals=[]
for role in ['experience','about']:
    host=bpy.data.objects['island_pillar_'+role]
    threshold=bpy.data.objects['bridge_threshold_project' if role=='experience' else 'bridge_about_threshold_project']
    entrance=sum((threshold.matrix_world@Vector(p) for p in threshold.bound_box),Vector())/8
    n=entrance-origin;n.z=0;n.normalize()
    t=Vector((-n.y,n.x,0))
    destination=origin+n*8.190556526184082
    delta=math.atan2(n.y,n.x)+math.pi/2-host.matrix_world.to_euler().z
    T=Matrix.Translation(destination)@Matrix.Rotation(delta,4,'Z')@Matrix.Translation(-host.matrix_world.translation)
    objects=set([host,*host.children_recursive,*bpy.data.collections['bridge_project_'+role].objects])
    worlds={o:o.matrix_world.copy() for o in objects}
    def depth(o):
        d=0
        while o.parent:d+=1;o=o.parent
        return d
    for o in sorted(objects,key=depth):
        o.matrix_world=T@worlds[o];bpy.context.view_layer.update()
    host['bridge_center_offset']=0
    if 'bridge_table_edge_offset' in host:del host['bridge_table_edge_offset']
    portals.append((n,t,0))
for role in ['experience','about']:
    heading=bpy.data.objects.get('station_heading_'+role)
    if heading:bpy.data.objects.remove(heading,do_unlink=True)
def in_portal(p):
    p=p-origin
    return any(p.dot(n)>1.6 and abs(p.dot(t)-offset)<WIDTH/2+.035 for n,t,offset in portals)
# Restore the authored perimeter posts/bulbs from the pre-layout backup.
# Loading just these objects does not link any backup islands into the scene.
names=['deck_railing_b','deck_lantern_posts_b','deck_lantern_glass_b']
names += [o.name for o in bpy.data.collections['deck_project'].objects if o.type=='LIGHT' and o.name.startswith('deckLight_lantern_')]
with bpy.data.libraries.load(str(__import__('pathlib').Path(bpy.data.filepath).parent/'base.before-three-islands.blend'),link=False) as (src,dst):dst.objects=list(names)
backup=dict(zip(names,dst.objects))
def components(ob):
    bm=bmesh.new();bm.from_mesh(ob.data);unseen=set(bm.verts);parts=[]
    while unseen:
        v=unseen.pop();part={v};todo=[v]
        while todo:
            for e in todo.pop().link_edges:
                for q in e.verts:
                    if q in unseen:unseen.remove(q);part.add(q);todo.append(q)
        parts.append(part)
    return bm,parts

def original_parts(name,posts_only=False):
    src=backup[name];bm,parts=components(src);vs=[];fs=[]
    for part in parts:
        if posts_only and len(part)>24:continue
        coords={v:src.matrix_world@v.co for v in part}
        if any(in_portal(p) for p in coords.values()):continue
        indices={v:len(vs)+i for i,v in enumerate(part)}
        vs.extend(tuple(coords[v]) for v in part)
        fs.extend(tuple(indices[v] for v in f.verts) for f in {f for v in part for f in v.link_faces})
    bm.free();return vs,fs

def replace(name,vs,fs):
    ob=bpy.data.objects[name];me=bpy.data.meshes.new(name+'_table_aligned')
    me.from_pydata(vs,[],fs);me.update()
    for mat in ob.data.materials:me.materials.append(mat)
    bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
    ob.data=me;ob.matrix_world=Matrix.Identity(4)

def arcs(vs,fs,r0,r1,z0,z1):
    N=720
    for i in range(N):
        a=math.tau*i/N;b=math.tau*(i+1)/N;mid=(a+b)/2
        if in_portal(origin+Vector((RP*math.cos(mid),RP*math.sin(mid),0))):continue
        j=len(vs)
        for angle in (a,b):
            for r,z in [(r0,z0),(r1,z0),(r1,z1),(r0,z1)]:vs.append((origin.x+r*math.cos(angle),origin.y+r*math.sin(angle),z))
        fs.extend(tuple(j+k for k in face) for face in [(0,1,2,3),(7,6,5,4),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)])
vs,fs=original_parts('deck_railing_b',True)
for z0,z1 in [(F+.28282,F+.30052),(F+.41542,F+.43312)]:arcs(vs,fs,RP-.019,RP+.019,z0,z1)
replace('deck_railing_b',vs,fs)
vs=[];fs=[];arcs(vs,fs,RP-.07,RP+.08,F-.016,F+.065);replace('deck_parapet_b',vs,fs)
for name in ['deck_lantern_posts_b','deck_lantern_glass_b']:replace(name,*original_parts(name))
# Restore lamp positions from the same saved source as the perimeter bulbs.
for name, src in backup.items():
    if src.type == 'LIGHT': bpy.data.objects[name].matrix_world = src.matrix_world.copy()
project['station_rim_rotation']=0
scene['table_aligned_bridges']=False
scene['radial_bridges']=True
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
result={'radial_bridges':True,'baked_headings':False}
