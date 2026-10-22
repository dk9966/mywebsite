import bpy,bmesh,hashlib,array,json,math
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
P=Path('/Users/danielku/mywebsite/secret-base/lower-platform-detail')
F=6.824491024;MF=6.871178627
FRAME=Matrix.Translation((21.299999237,0,0))@Matrix.Rotation(-math.atan2(12,19),4,'Z');INV=FRAME.inverted()
def fp(o):
    h=hashlib.sha256(repr([list(r) for r in o.matrix_basis]).encode())
    if o.type=='MESH':
        a=array.array('f',[0.])*(len(o.data.vertices)*3);o.data.vertices.foreach_get('co',a);h.update(a.tobytes())
    return h.hexdigest()
def topo(o):
    bm=bmesh.new();bm.from_mesh(o.data)
    unseen=set(bm.verts);components=0
    while unseen:
        stack=[unseen.pop()];components+=1
        while stack:
            v=stack.pop()
            for e in v.link_edges:
                w=e.other_vert(v)
                if w in unseen:unseen.remove(w);stack.append(w)
    ans={'components':components,'boundary_edges':sum(e.is_boundary for e in bm.edges),'nonmanifold_junctions':sum(len(e.link_faces)>2 for e in bm.edges),'loose_edges':sum(not e.link_faces for e in bm.edges),'degenerate_faces':sum(f.calc_area()<1e-10 for f in bm.faces)}
    bm.free();return ans
bpy.ops.wm.open_mainfile(filepath=str(P/'before-detail.blend'))
old={o.name:fp(o) for o in bpy.context.scene.objects}
oldtop=topo(bpy.data.objects['150 | continuous cave with oblique carved rooms'])
bpy.ops.wm.open_mainfile(filepath=str(P/'detailed-workshop.blend'))
S=bpy.context.scene;dg=bpy.context.evaluated_depsgraph_get()
changed=[n for n,h in old.items() if n in S.objects and fp(S.objects[n])!=h]
assert set(changed)=={'Lower | plain octagon','150 | continuous cave with oblique carved rooms'},changed
terrain=S.objects['150 | continuous cave with oblique carved rooms'];newtop=topo(terrain)
assert newtop==oldtop,(oldtop,newtop)
def tree(obs):
    verts=[];faces=[]
    for o in obs:
        ev=o.evaluated_get(dg);me=ev.to_mesh();start=len(verts)
        verts += [INV@(ev.matrix_world@v.co) for v in me.vertices]
        faces += [tuple(start+i for i in f.vertices) for f in me.polygons]
        ev.to_mesh_clear()
    return BVHTree.FromPolygons(verts,faces)
terr=tree([terrain])
floor_samples=[(7.52,-3.52),(6.2,-4.3),(8.7,-4.7),(8.4,-2.3),(9.7,-3.4)]
intrusions=[]
for x,y in floor_samples:
    hit=terr.ray_cast(Vector((x,y,F+.03)),Vector((0,0,1)),1.2)
    if hit[0] is not None:intrusions.append([x,y,list(hit[0])])
assert not intrusions,intrusions
d=Vector((1,-.625,0)).normalized();n=Vector((-d.y,d.x,0))
rails=tree([o for o in bpy.data.collections['03 | Uniform slender steel railings'].objects if o.type=='MESH'])
obstacles=[]
for lateral in [-.50,0,.50]:
    for h in [.08,.19,.345]:
        origin=d*3.1+n*lateral+Vector((0,0,MF+h))
        if rails.ray_cast(origin,d,1.2)[0] is not None:obstacles.append([lateral,h])
assert not obstacles,obstacles
# Measure the bridge seam from evaluated geometry, rather than source values.
ev=S.objects['Bridge | mitered continuous walking deck'].evaluated_get(dg);me=ev.to_mesh()
ends=[INV@(ev.matrix_world@v.co) for v in me.vertices]
ev.to_mesh_clear()
endtop=max(p.z for p in ends if p.x>4.601191)
assert abs(endtop-F)<.0002,endtop
invalid=[o.name for o in S.objects if o.animation_data and any(not fc.driver.is_valid for fc in o.animation_data.drivers)]
assert not invalid,invalid
ctrl=S.objects['SCENE SLIDERS'];cm=ctrl.modifiers['Scene Sliders']
before=float(cm['Socket_3'])
sample=S.objects['Lower | continuous 0 rail 0.345']
def maxz(o):
    ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();z=max((ev.matrix_world@v.co).z for v in me.vertices);ev.to_mesh_clear();return z
z0=maxz(sample)
cm['Socket_3']=before*1.1;ctrl.update_tag();S.frame_set(S.frame_current);bpy.context.view_layer.update()
z1=maxz(sample)
assert z1-z0>.03,(z0,z1)
cm['Socket_3']=before;ctrl.update_tag();S.frame_set(S.frame_current);bpy.context.view_layer.update()
report={'passed':True,'changed_existing_meshes':changed,'unaffected_existing_objects':len(old)-len(changed),'terrain_before':oldtop,'terrain_after':newtop,'clear_floor_samples':len(floor_samples),'clear_bridge_gate_rays':9,'bridge_landing_height_error_m':abs(endtop-F),'invalid_drivers':invalid,'railing_control_measured_height_increase_m':z1-z0,'reference_furniture_added':False}
P.joinpath('verification.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
