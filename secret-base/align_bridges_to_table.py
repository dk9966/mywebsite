"""Align the panel-facing bridge edges with the actual tabletop wing end caps.
Run after layout_three_islands.py. Re-runnable; geometry remains Blender-owned.
"""
import bpy, bmesh, math
from mathutils import Matrix, Vector
scene=bpy.context.scene
project=bpy.data.objects['island_pillar_project'];origin=project.matrix_world.translation.copy()
CA=math.radians(56);PHI=math.radians(38);WIDTH=.923;RP=2.712;F=6.871178627
# Measure the saved table, which has been slid forward from its code default.
desk=bpy.data.objects['deck_desk_b'];points=[]
for v in desk.data.vertices:
    p=desk.matrix_world@v.co-origin
    u=p.x*math.cos(CA)+p.y*math.sin(CA)
    if abs(p.z-7.3552)<.0002 and u<1.87:points.append(p)
assert points, 'Tabletop end caps not found'
portals=[]
for role,g in [('experience',-1),('about',1)]:
    n=Vector((math.cos(CA+g*PHI),math.sin(CA+g*PHI),0))
    t=Vector((-g*n.y,g*n.x,0))
    edge=max(p.dot(t) for p in points)
    offset=edge+WIDTH/2
    # Seat the entire entrance inside the circular deck, including its outside corner.
    start=math.sqrt(RP*RP-(offset+WIDTH/2)**2)
    shift=start-abs(float(scene['experience_bridge_specs']['project_end_y']))
    destination=origin+n*(8.190556526184082+shift)+t*offset
    host=bpy.data.objects['island_pillar_'+role]
    delta=CA+g*PHI+math.pi/2-(host.matrix_world.to_euler().z-project.matrix_world.to_euler().z)
    T=Matrix.Translation(destination)@Matrix.Rotation(delta,4,'Z')@Matrix.Translation(-host.matrix_world.translation)
    objects=set([host,*host.children_recursive,*bpy.data.collections['bridge_project_'+role].objects])
    worlds={o:o.matrix_world.copy() for o in objects}
    def depth(o):
        d=0
        while o.parent:d+=1;o=o.parent
        return d
    for o in sorted(objects,key=depth):
        o.matrix_world=T@worlds[o];bpy.context.view_layer.update()
    heading=bpy.data.objects.get('station_heading_'+role)
    if heading:
        heading.matrix_world=Matrix.Translation(heading.matrix_world.translation)@Vector((-math.cos(CA),-math.sin(CA),0)).to_track_quat('Z','Y').to_matrix().to_4x4()
    host['bridge_table_edge_offset']=edge
    host['bridge_center_offset']=offset
    portals.append((n,t,offset))

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
scene['table_aligned_bridges']=True
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
result={'table_edge_offsets':{r:float(bpy.data.objects['island_pillar_'+r]['bridge_table_edge_offset']) for r in ['experience','about']},'positions':{r:list(bpy.data.objects['island_pillar_'+r].matrix_world.translation) for r in ['experience','about']}}
