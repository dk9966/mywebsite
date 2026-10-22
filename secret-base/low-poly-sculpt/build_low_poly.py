"""Create a directly editable, triangulated terrain copy of the live scene."""
import bpy, bmesh, math, json, hashlib, array
from pathlib import Path
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P/'source-live-snapshot.blend'))
S=bpy.context.scene
if bpy.context.object and bpy.context.object.mode!='OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')
bpy.context.preferences.filepaths.save_version=0
names={
    '150 | continuous cave with oblique carved rooms':14000,
    'Central rock mound | continuous cross-column extrusions':4500,
}
def signature(o):
    h=hashlib.sha256(repr([list(r) for r in o.matrix_world]).encode())
    if o.type=='MESH':
        a=array.array('f',[0.0])*(len(o.data.vertices)*3)
        o.data.vertices.foreach_get('co',a);h.update(a.tobytes())
        h.update(str(len(o.data.polygons)).encode())
    return h.hexdigest()
untouched={o.name:signature(o) for o in S.objects if o.name not in names}
report={'source':str(P/'source-live-snapshot.blend'),'terrain':{},'platforms_unchanged':False}
source_trees={}
for name,target in names.items():
    ob=S.objects[name]
    dg=bpy.context.evaluated_depsgraph_get()
    # Bake the visible result first, so sculpting acts on the actual silhouette.
    me=bpy.data.meshes.new_from_object(ob.evaluated_get(dg),depsgraph=dg)
    for mod in list(ob.modifiers):ob.modifiers.remove(mod)
    ob.data=me
    before=len(me.polygons)
    bm=bmesh.new();bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00001)
    bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=.000001)
    bmesh.ops.triangulate(bm,faces=list(bm.faces),quad_method='BEAUTY',ngon_method='BEAUTY')
    bm.to_mesh(me);bm.free();me.update()
    src=BVHTree.FromPolygons([ob.matrix_world@v.co for v in me.vertices],[tuple(f.vertices) for f in me.polygons])
    source_trees[name]=src
    tri_before=len(me.polygons)
    bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
    mod=ob.modifiers.new('Low polygon terrain','DECIMATE');mod.decimate_type='COLLAPSE'
    mod.ratio=min(1.,target/tri_before);mod.use_collapse_triangulate=True
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bm=bmesh.new();bm.from_mesh(ob.data)
    bmesh.ops.triangulate(bm,faces=list(bm.faces),quad_method='BEAUTY',ngon_method='BEAUTY')
    bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=.000001)
    seen=set();parts=[]
    for v in bm.verts:
        if v in seen:continue
        todo=[v];seen.add(v);count=0
        while todo:
            v=todo.pop();count+=1
            for e in v.link_edges:
                other=e.other_vert(v)
                if other not in seen:seen.add(other);todo.append(other)
        parts.append(count)
    bad=sum(len(e.link_faces)>2 or not e.link_faces for e in bm.edges)
    boundary=sum(e.is_boundary for e in bm.edges)
    bm.to_mesh(ob.data);bm.free();ob.data.update()
    for f in ob.data.polygons:f.use_smooth=False
    ob.data.name='Sculpt | '+('continuous cave triangles' if '150' in name else 'central pillar triangles')
    ob.data.remesh_voxel_size=.15
    ob.data.use_remesh_preserve_volume=True
    ob.use_mesh_mirror_x=False;ob.use_mesh_mirror_y=False;ob.use_mesh_mirror_z=False
    ob['sculpt_copy']='Applied low-poly triangles. Platform and prop geometry preserved from the live snapshot.'
    ob['original_evaluated_triangles']=tri_before
    ob['low_poly_triangles']=len(ob.data.polygons)
    report['terrain'][name]={'original_faces':before,'original_triangles':tri_before,'triangles':len(ob.data.polygons),'vertices':len(ob.data.vertices),'components':parts,'invalid_edges':bad,'boundary_edges':boundary,'all_triangles':all(len(f.vertices)==3 for f in ob.data.polygons),'modifiers':len(ob.modifiers)}
    print('SIMPLIFIED',name,json.dumps(report['terrain'][name]),flush=True)

# Check against the known fitted walkable envelopes, and compare support-contact
# distances against the captured geometry rather than assuming an ideal wall.
fit=json.loads((P.parent/'right-bays-user-fit/coherent-bays-checks.json').read_text())
FRAME=Matrix.Translation((21.299999237,0,0))@Matrix.Rotation(-math.atan2(12,19),4,'Z')
INV=FRAME.inverted();R=Matrix.Rotation(math.radians(fit['yaw_degrees']),4,'Z');origin=Vector((*fit['origin'],0))
wall=S.objects['150 | continuous cave with oblique carved rooms']
tree=BVHTree.FromPolygons([INV@(wall.matrix_world@v.co) for v in wall.data.vertices],[tuple(f.vertices) for f in wall.data.polygons])
new_world=BVHTree.FromPolygons([wall.matrix_world@v.co for v in wall.data.vertices],[tuple(f.vertices) for f in wall.data.polygons])
def inside(x,y,poly):
    yes=False
    for p,q in zip(poly,poly[1:]+poly[:1]):
        if (p[1]>y)!=(q[1]>y) and x<(q[0]-p[0])*(y-p[1])/(q[1]-p[1])+p[0]:yes=not yes
    return yes
intrusions=[]
clearance_lifts={}
for label,b in fit['bay_info'].items():
    xs=[min(p[0] for p in b['poly'])+.17+.22*i for i in range(36)]
    ys=[min(p[1] for p in b['poly'])+.17+.22*i for i in range(24)]
    for x in xs:
        for y in ys:
            if inside(x,y,b['poly']):
                p=origin+R@Vector((x+b['offset_x'],y+b['offset_y'],b['z']+.09))
                hit=tree.ray_cast(p,Vector((0,0,1)),1.75)
                if hit[0] is not None:
                    # Prevent simplification from lowering a recess lip into
                    # the head-clearance envelope at the edge of the deck.
                    for vi in wall.data.polygons[hit[2]].vertices:
                        q=INV@(wall.matrix_world@wall.data.vertices[vi].co)
                        if b['z']+1.5<q.z<b['z']+1.91:
                            clearance_lifts[vi]=max(clearance_lifts.get(vi,q.z),b['z']+1.91)
if clearance_lifts:
    local=wall.matrix_world.inverted()@FRAME
    for vi,z in clearance_lifts.items():
        q=INV@(wall.matrix_world@wall.data.vertices[vi].co);q.z=z;wall.data.vertices[vi].co=local@q
    wall.data.update()
    tree=BVHTree.FromPolygons([INV@(wall.matrix_world@v.co) for v in wall.data.vertices],[tuple(f.vertices) for f in wall.data.polygons])
    new_world=BVHTree.FromPolygons([wall.matrix_world@v.co for v in wall.data.vertices],[tuple(f.vertices) for f in wall.data.polygons])
for label,b in fit['bay_info'].items():
    for i in range(36):
        x=min(p[0] for p in b['poly'])+.17+.22*i
        for j in range(24):
            y=min(p[1] for p in b['poly'])+.17+.22*j
            if inside(x,y,b['poly']):
                p=origin+R@Vector((x+b['offset_x'],y+b['offset_y'],b['z']+.09))
                hit=tree.ray_cast(p,Vector((0,0,1)),1.75)
                if hit[0] is not None:intrusions.append([label,x,y,list(hit[0])])
report['recess_clearance_vertices_adjusted']=len(clearance_lifts)
grounding=[];b=fit['bay_info']['lower']
for x,y in [(0,-1.),(0,.25),(-3.8,.2),(1.7,.2)]:
    p=origin+R@Vector((x+b['offset_x'],y+b['offset_y'],b['z']-.015))
    hit=tree.ray_cast(p,Vector((0,0,-1)),.32)
    grounding.append({'xy':[x,y],'rock_below':hit[0] is not None})
shoes=[]
for ob in S.objects:
    if 'rock bolting shoe' in ob.name:
        p=ob.matrix_world.translation
        old=source_trees[wall.name].find_nearest(p)[3];new=new_world.find_nearest(p)[3]
        shoes.append({'name':ob.name,'old_distance':old,'new_distance':new,'added_gap':new-old})
report.update(platforms_unchanged=all(signature(S.objects[n])==h for n,h in untouched.items()),standing_rock_intrusions=intrusions,rock_seating=grounding,anchor_contacts=shoes)
report['passed']=report['platforms_unchanged'] and not intrusions and all(x['rock_below'] for x in grounding) and all(x['added_gap']<.06 for x in shoes) and all(t['all_triangles'] and t['invalid_edges']==0 and len(t['components'])==1 for t in report['terrain'].values())
(P/'checks.json').write_text(json.dumps(report,indent=2))
assert report['passed'],json.dumps(report)

# The output opens with the wall active in a clear solid view, ready for Sculpt.
bpy.ops.object.select_all(action='DESELECT');wall.select_set(True);bpy.context.view_layer.objects.active=wall
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            sp=area.spaces.active;sp.shading.type='SOLID';sp.shading.light='STUDIO';sp.shading.color_type='MATERIAL'
            sp.shading.show_cavity=True;sp.shading.cavity_type='BOTH';sp.overlay.show_wireframes=False
S.name='Cave | low-poly triangle terrain for sculpting'
S.camera=S.objects['150 | main cave camera']
S.render.resolution_x=1600;S.render.resolution_y=896;S.render.resolution_percentage=100
S.render.engine='CYCLES';S.cycles.samples=32;S.cycles.use_denoising=True
try:
    prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='METAL';prefs.get_devices()
    for d in prefs.devices:d.use=d.type=='METAL'
    S.cycles.device='GPU'
except Exception:S.cycles.device='CPU'
txt=bpy.data.texts.new('LOW_POLY_SCULPT_README');txt.write('Terrain only is simplified and triangulated. Both terrain meshes have applied geometry and no modifiers. The cave wall is one connected open interior surface. The middle rock stays a separate closed mesh. All platforms and props are retained from the live source snapshot. Select either terrain object and enter Sculpt Mode. X/Y/Z sculpt symmetry is disabled. Original terrain is preserved in source-live-snapshot.blend beside this file.')
bpy.ops.wm.save_as_mainfile(filepath=str(P/'cave-low-poly-sculpt.blend'),compress=True)
for cam,suffix in [('150 | main cave camera','overview'),('150 | same azimuth detail','detail')]:
    S.camera=S.objects[cam];S.render.filepath=str(P/('low-poly-'+suffix+'.png'));bpy.ops.render.render(write_still=True)
print('DONE',str(P/'cave-low-poly-sculpt.blend'),flush=True)
