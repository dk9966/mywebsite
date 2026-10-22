import bpy,bmesh,json,math,statistics
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

P=Path(__file__).resolve().parent
w=bpy.data.objects['Candidate | direct terrain cleanup']
source=bpy.data.objects[w['original_object']]
base=bpy.data.meshes[w['baseline_mesh']]
deck=bpy.data.objects['Upper | beveled square gallery']
M=deck.matrix_world.inverted()@w.matrix_world
if bpy.context.mode!='OBJECT':bpy.ops.object.mode_set(mode='OBJECT')
w.data=base.copy();w.data.name='Candidate | culled and relaxed terrain'
dg=bpy.context.evaluated_depsgraph_get()
arch=bpy.data.objects['Platform backing | live fitting surfaces'].evaluated_get(dg)
contact=BVHTree.FromPolygons([v.co for v in arch.data.vertices],[p.vertices[:] for p in arch.data.polygons])

def ss(t):
    t=max(0.,min(1.,t));return t*t*(3-2*t)
def band(x,lo,hi,fade):return ss((x-lo)/fade)*ss((hi-x)/fade)
def weight(p):
    side=band(p.x,-4.8,5.8,1.)*band(p.y,-7.5,-2.65,.85)*band(p.z,8.,15.5,.8)
    seam=band(p.x,-7.,5.5,.9)*band(p.y,-10.,-3.,.8)*band(p.z,7.6,11.4,.65)
    lower=band(p.x,-4.8,5.8,.9)*band(p.y,-6.,3.5,.8)*band(p.z,4.5,8.5,.7)
    return max(side,seam,lower)

bm=bmesh.new();bm.from_mesh(w.data);bm.verts.ensure_lookup_table()
initial=[v.co.copy() for v in bm.verts]
weights=[]
for v in bm.verts:
    a=weight(M@v.co)
    if v.is_boundary:a=0.
    if a:
        near=contact.find_nearest(v.co)
        if near[0] is not None:a*=ss((near[3]-.045)/.18)
    weights.append(a)
neighbors=[[ed.other_vert(v).index for ed in v.link_edges] for v in bm.verts]
active=[i for i,a in enumerate(weights) if a>.001 and neighbors[i]]
# Direct local Taubin relaxation removes folded spikes without a live modifier.
for step in range(16):
    for factor in (.48,-.50):
        updates=[]
        for i in active:
            v=bm.verts[i];avg=sum((bm.verts[j].co for j in neighbors[i]),Vector())/len(neighbors[i])
            delta=(avg-v.co)*factor*weights[i]
            if delta.length>.14:delta*=.14/delta.length
            updates.append((v,v.co+delta))
        for v,p in updates:v.co=p
bm.normal_update();bm.to_mesh(w.data);bm.free();w.data.update()

selected_before=[o for o in bpy.context.selected_objects]
active_before=bpy.context.view_layer.objects.active
hidden=w.hide_get()
passes=[]
regions=[('upper shoulder',lambda p:-3.8<p.x<5 and -6.5<p.y<-2.60 and 9.6<p.z<14.7,.42),
         ('lower roof seam',lambda p:-7<p.x<5.2 and -10<p.y<-3 and 7.7<p.z<11.5,.36),
         ('lower platform surrounds',lambda p:-4.5<p.x<5.8 and -6<p.y<3.3 and 4.8<p.z<8.4,.55)]
try:
    for o in bpy.context.selected_objects:o.select_set(False)
    w.hide_set(False);w.select_set(True);bpy.context.view_layer.objects.active=w
    for name,inside,ratio in regions:
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='DESELECT')
        bm=bmesh.from_edit_mesh(w.data)
        for f in bm.faces:
            if all(inside(M@v.co) for v in f.verts):f.select_set(True)
        bm.select_flush(True)
        count=sum(f.select for f in bm.faces);before=len(bm.faces)
        bmesh.update_edit_mesh(w.data)
        bpy.ops.mesh.decimate(ratio=ratio,use_vertex_group=False,use_symmetry=False)
        bm=bmesh.from_edit_mesh(w.data)
        passes.append({'region':name,'selected_faces':count,'removed_faces':before-len(bm.faces)})
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.mode_set(mode='OBJECT')
finally:
    if bpy.context.mode!='OBJECT':bpy.ops.object.mode_set(mode='OBJECT')
    w.hide_set(hidden);w.select_set(False)
    for o in selected_before:o.select_set(True)
    bpy.context.view_layer.objects.active=active_before

bm=bmesh.new();bm.from_mesh(w.data)
bmesh.ops.dissolve_degenerate(bm,dist=.00001,edges=list(bm.edges))
bmesh.ops.triangulate(bm,faces=[f for f in bm.faces if len(f.verts)>3],quad_method='BEAUTY',ngon_method='BEAUTY')
for f in bm.faces:
    if weight(M@f.calc_center_median())>.001:f.smooth=False
bm.normal_update();bm.to_mesh(w.data);bm.free();w.data.update()
result={'before_triangles':len(base.polygons),'after_triangles':len(w.data.polygons),'passes':passes,'modifiers':len(w.modifiers),'shape_keys':bool(w.data.shape_keys)}
(P/'cleanup-report.json').write_text(json.dumps(result,indent=2))
