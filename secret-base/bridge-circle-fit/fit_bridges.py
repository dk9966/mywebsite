"""Trim three existing bridges to the evaluated circular rim, non-destructively.

Run in the live scene. Existing meshes, railing assemblies, and slider drivers
are preserved. A hidden cutter inherits the rim's exact width control.
"""
import bpy, math, json, hashlib, array
from pathlib import Path
from mathutils import Vector

P=Path(__file__).resolve().parent
S=bpy.context.scene
DG=bpy.context.evaluated_depsgraph_get()
RIM=bpy.data.objects['Metal | upper rolled rim']
C=bpy.data.objects['Rig | middle radius'].matrix_world.translation.copy();C.z=0
UP=Vector((0,0,1))
GN=next(m for m in RIM.modifiers if m.type=='NODES')
SCALE=(RIM.matrix_world.to_3x3()@Vector((1,0,0))).length
BASE_R=max(math.hypot(v.co.x,v.co.y) for v in RIM.data.vertices)
R=max(math.hypot(*(RIM.evaluated_get(DG).matrix_world@v.co-C)[:2]) for v in RIM.evaluated_get(DG).data.vertices)
assert 3.70<R<3.75, ('Inspect the current circle before changing these bridge ends',R)
assert '174 | Flush circular bridge joints' not in bpy.data.collections,'Already fitted'


def points(o):
    e=o.evaluated_get(bpy.context.evaluated_depsgraph_get())
    return [e.matrix_world@v.co for v in e.data.vertices]


def signature(o):
    h=hashlib.sha256(repr([list(row) for row in o.matrix_world]).encode())
    if o.type=='MESH':
        co=array.array('f',[0])*(len(o.data.vertices)*3)
        o.data.vertices.foreach_get('co',co);h.update(co.tobytes())
        h.update(repr([tuple(f.vertices) for f in o.data.polygons]).encode())
    h.update(repr([m.name if m else None for m in o.data.materials] if o.type=='MESH' else []).encode())
    return h.hexdigest()

before={o.name:signature(o) for o in S.objects}
source_collections=['158 | Connected bridge and railings','166 | Left bridge and right-turn steel stairs','170 | Rear-left connected platform']
thresholds=['Bridge | curved circle threshold','Rear left | curved flush center threshold']
targets=[]
for name in source_collections:
    for o in bpy.data.collections[name].objects:
        if not o.visible_get() or o.type!='MESH' or o.name in thresholds:continue
        if any(t in o.name for t in ('upright','shoe','post','foot','rail','curb')):continue
        ps=points(o)
        if ps and min(math.hypot(p.x-C.x,p.y-C.y) for p in ps)<R+.045 and max(p.z for p in ps)<6.94:
            targets.append(o)
assert len(targets)==25,(len(targets),[o.name for o in targets])
COL=bpy.data.collections.new('174 | Flush circular bridge joints');S.collection.children.link(COL)
ARCH=bpy.data.collections.new('Archive | overlapping bridge thresholds');S.collection.children.link(ARCH)
ARCH.hide_viewport=ARCH.hide_render=True
for name in thresholds:
    o=bpy.data.objects[name]
    ARCH.objects.link(o)
    for col in list(o.users_collection):
        if col!=ARCH:col.objects.unlink(o)

# The rim is a 192-sided machined ring. Copy its original outer polygon, then
# use its existing radial-width modifier and driver. This tracks the exact edge
# at every slider setting, without freezing any of the bridge geometry.
angles=sorted(set(round(math.atan2(v.co.y,v.co.x),6) for v in RIM.data.vertices if abs(math.hypot(v.co.x,v.co.y)-BASE_R)<1e-5))
assert len(angles)==192
clearance=.0012
base_cut_r=BASE_R+clearance/SCALE
vertices=[(base_cut_r*math.cos(a),base_cut_r*math.sin(a),z) for z in (4.5,7.0) for a in angles]
n=len(angles)
faces=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
me=bpy.data.meshes.new('Bridge circle | full circular clearance volume');me.from_pydata(vertices,[],faces);me.update()
cut=RIM.copy();cut.data=me;cut.name='Bridge circle | hidden rim-following cut';COL.objects.link(cut)
for m in list(cut.modifiers):
    if m.type!='NODES':cut.modifiers.remove(m)
cut.hide_render=True;cut.display_type='WIRE';cut.hide_set(True)
cut['purpose']='Editable difference volume, follows the same radius driver as the circular rim.'
for o in targets:
    m=o.modifiers.new('Flush cut against circular platform','BOOLEAN');m.operation='DIFFERENCE';m.solver='EXACT';m.object=cut
    if 'grating' in o.name:m.use_self=True
    o['circle_fit']='Curved cut outside the circular rim with 1.2 mm fitting clearance'

# A narrow, closed curved frame finishes the cut bars. Its inner edge follows
# the very same faceted outline as the ring, so it neither buries in the rim
# nor bridges across it with a straight chord.
inv=RIM.matrix_world.inverted()
material=bpy.data.materials['Bridge | blue gunmetal panel frames']
M=RIM.matrix_world.to_3x3();base_rotation=math.atan2(M[1][0],M[0][0])
width_value=float(GN['Socket_2']);radius_param=float(GN['Socket_5'])
radial_shift=radius_param*(width_value-1)

def polygon_radius(angle,base_radius):
    # Boundary along a ray for the un-beveled, uniformly spaced rim polygon.
    a0=angles[0];step=math.tau/n
    mid=a0+(math.floor((angle-a0)/step)+.5)*step
    return base_radius*math.cos(step/2)/math.cos(angle-mid)

records=[]
configs=[('front',Vector((.43392,-.90095,0)),.7025,'Bridge | steel edge cap 0'),
         ('stairs',Vector((-.97625,-.21665,0)),.67,'Left stairs | upper bridge bay 01 frame'),
         ('rear',Vector((-.284576833,.958653212,0)),.6175,'Rear left | bridge edge cap')]
for label,d,half,reference in configs:
    d.normalize();mid=math.atan2(d.y,d.x)-base_rotation
    extent=math.asin(half/(R+clearance+.028))
    aa=[mid-extent,mid+extent]
    for a in angles:
        a=mid+(a-mid+math.pi)%math.tau-math.pi
        if aa[0]<a<aa[1]:aa.append(a)
    # Intermediate points keep the front bridge's mild descent continuous.
    aa+= [mid-extent+2*extent*i/48 for i in range(1,48)]
    aa=sorted(set(aa));vs=[];fs=[]
    for a in aa:
        ri=polygon_radius(a,BASE_R+clearance/SCALE)
        ro=ri+.028/SCALE
        # Place vertices before the inherited rim-width offset is evaluated.
        for r in (ri,ro):
            current_radius=SCALE*(r+radial_shift)
            s=current_radius*math.cos(a-mid)
            z=6.871178627
            if label=='front':
                T=math.sqrt(3.620207**2-.67**2)
                z+= (6.824491024-6.871178627)*min(1,max(0,(s-T)/1.12))
            elif label=='stairs':z=6.87
            vs.extend([(r*math.cos(a),r*math.sin(a),z-.046),(r*math.cos(a),r*math.sin(a),z)])
    for i in range(len(aa)-1):
        k=4*i;l=k+4
        fs.extend([(k+1,k+3,l+3,l+1),(k,l,l+2,k+2),(k,k+1,l+1,l),(k+2,l+2,l+3,k+3)])
    fs.extend([(0,2,3,1),(len(vs)-4,len(vs)-3,len(vs)-1,len(vs)-2)])
    mesh=bpy.data.meshes.new('Bridge circle | '+label+' curved end frame');mesh.from_pydata(vs,[],fs);mesh.update()
    import bmesh
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
    o=RIM.copy();o.data=mesh;o.name='Bridge circle | '+label+' flush curved end frame';COL.objects.link(o)
    o.data.materials.clear();o.data.materials.append(material)
    for m in list(o.modifiers):
        if m.type!='NODES':o.modifiers.remove(m)
    bevel=o.modifiers.new('Fine cut edge','BEVEL');bevel.width=.00045/SCALE;bevel.segments=2
    o.modifiers.new('Fabricated normals','WEIGHTED_NORMAL')
    records.append(o.name)

bpy.context.view_layer.update();S.frame_set(S.frame_current)
assert all(signature(bpy.data.objects[name])==sig for name,sig in before.items()),'Original geometry changed'
report={'radius_m':R,'clearance_m':clearance,'rim_segments':n,'trimmed_objects':[o.name for o in targets],'end_frames':records,'archived_thresholds':thresholds,'original_objects_preserved':len(before),'file':bpy.data.filepath}
(P/'fit-report.json').write_text(json.dumps(report,indent=2))
S['bridge_circle_joint_revision']='Three bridge decks cut to the circular rim with fitted curved steel end frames.'
result=report
