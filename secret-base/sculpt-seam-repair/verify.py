import bpy, bmesh, json, math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

P=Path(__file__).resolve().parent
w=bpy.data.objects['150 | continuous cave with oblique carved rooms']
deck=bpy.data.objects['Upper | beveled square gallery']
repairs=[m for m in w.modifiers if m.name.startswith(('Seam repair |','Surround repair |'))]
states=[m.show_viewport for m in repairs]
ctrl=bpy.data.objects['SCENE SLIDERS'];cm=ctrl.modifiers['Scene Sliders']
sockets={i.name:i.identifier for i in cm.node_group.interface.items_tree if i.item_type=='SOCKET' and i.in_out=='INPUT'}
hk=sockets['Light height above walls (m)'];rk=sockets['Light radius (m)']
initial=(cm[hk],cm[rk])
def enable(value):
    for m,state in zip(repairs,states):m.show_viewport=value and state
    ctrl.update_tag();bpy.context.view_layer.update()
def clearances():
    dg=bpy.context.evaluated_depsgraph_get();e=w.evaluated_get(dg)
    tree=BVHTree.FromPolygons([v.co for v in e.data.vertices],[p.vertices[:] for p in e.data.polygons])
    mx=e.matrix_world.inverted()@deck.matrix_world
    target=bpy.data.objects['Platform backing | live fitting surfaces'].evaluated_get(dg)
    targettree=BVHTree.FromPolygons([v.co for v in target.data.vertices],[p.vertices[:] for p in target.data.polygons])
    walk=[]
    for i in range(25):
        for j in range(25):
            x=-2.8+5.6*i/24;y=-2.8+5.6*j/24
            if abs(x)+abs(y)>4.32:continue
            origin=mx@Vector((x,y,deck['deck_height_m']+.035))
            p,n,f,dist=tree.ray_cast(origin,Vector((0,0,1)),1.7)
            if p is not None:
                q,nn,ff,dd=targettree.ray_cast(origin,Vector((0,0,1)),1.7)
                if q is None or p.z<q.z-.015:walk.append((i,j))
    root=bpy.data.objects['Lower | circular roof assembly']
    cover=bpy.data.objects['Lower | circular light upper cover'].evaluated_get(dg)
    vs=[cover.matrix_world@v.co for v in cover.data.vertices]
    top=max(p.z for p in vs);center=e.matrix_world.inverted()@root.matrix_world.translation
    radius=max((p.xy-root.matrix_world.translation.xy).length for p in vs)
    light=[];coverage=[];light_details=[]
    for i in range(17):
        for j in range(17):
            x=radius*(i-8)/8*.9;y=radius*(j-8)/8*.9
            if x*x+y*y>radius*radius*.9**2:continue
            origin=Vector((center.x+x,center.y+y,top-.20))
            p,n,f,dist=tree.ray_cast(origin,Vector((0,0,1)),.20)
            if p is not None:
                light.append((i,j))
                light_details.append({'sample':(i,j),'face':f,'z':p.z,'points':[list(e.matrix_world@e.data.vertices[k].co) for k in e.data.polygons[f].vertices]})
            p,n,f,dist=tree.ray_cast(Vector((origin.x,origin.y,top+.005)),Vector((0,0,1)),2.0)
            if p is not None:coverage.append(p.z-top)
    return {'walk':walk,'light':light,'light_details':light_details,'covered_light_samples':len(coverage),'coverage_distance_min':min(coverage) if coverage else None}
checks=[]
try:
    for height,radius in globals().get('test_controls',[initial,(.35,.85),(1.49,1.46)]):
        cm[hk]=height;cm[rk]=radius
        enable(False);before=clearances()
        enable(True);after=clearances()
        checks.append({'height':height,'radius':radius,'new_walk_intrusions':len(set(after['walk'])-set(before['walk'])),
                       'new_light_intrusions':len(set(after['light'])-set(before['light'])),
                       'new_walk_samples':sorted(set(after['walk'])-set(before['walk'])),
                       'new_light_details':[d for d in after['light_details'] if d['sample'] not in before['light']],
                       'light_coverage_samples':after['covered_light_samples'],
                       'light_min_gap':after['coverage_distance_min']})
finally:
    cm[hk],cm[rk]=initial;enable(True)

enable(False)
e=w.evaluated_get(bpy.context.evaluated_depsgraph_get())
before=[v.co.copy() for v in e.data.vertices]
faces=[tuple(f.vertices) for f in e.data.polygons]
enable(True)
e=w.evaluated_get(bpy.context.evaluated_depsgraph_get())
after=[v.co.copy() for v in e.data.vertices]
assert len(before)==len(after)
assert faces==[tuple(f.vertices) for f in e.data.polygons]
bm=bmesh.new();bm.from_mesh(e.data)
left=set(bm.verts);components=0
while left:
    components+=1;stack=[left.pop()]
    while stack:
        v=stack.pop()
        for edge in v.link_edges:
            q=edge.other_vert(v)
            if q in left:left.remove(q);stack.append(q)
deltas=[(a-b).length for a,b in zip(after,before)]
result={'changed_evaluated_vertices':sum(d>1e-6 for d in deltas),
        'unchanged_evaluated_vertices':sum(d<=1e-6 for d in deltas),
        'max_change_m':max(deltas),'triangles':len(faces),'connected_components':components,
        'boundary_edges':sum(e.is_boundary for e in bm.edges),
        'loose_edges':sum(not e.link_faces for e in bm.edges),
        'nonmanifold_junctions':sum(len(e.link_faces)>2 for e in bm.edges),
        'degenerate_faces':sum(f.calc_area()<1e-10 for f in bm.faces),
        'shape_keys_retained':len(w.data.shape_keys.key_blocks),
        'control_checks':checks,'controls_restored':initial,
        'viewport_render_consistent':all(m.show_viewport==m.show_render for m in w.modifiers)}
bm.free()
(P/'verification.json').write_text(json.dumps(result,indent=2))
assert components==1 and not result['loose_edges'] and not result['nonmanifold_junctions'] and not result['degenerate_faces']
assert not any(c['new_walk_intrusions'] or c['new_light_intrusions'] for c in checks)
