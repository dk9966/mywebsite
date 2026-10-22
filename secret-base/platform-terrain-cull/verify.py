import bpy, bmesh, json, statistics, hashlib, array
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

P=Path(__file__).resolve().parent
w=bpy.data.objects['150 | continuous cave with oblique carved rooms']
d=bpy.data.objects['Upper | beveled square gallery']
m=w.modifiers['Platform surrounds | broad stone triangles']
new_mods=[w.modifiers.get(name) for name in ['Platform backing | snug hidden stone',
          'Platform surrounds | broad stone triangles','Roof surround | remove remaining dense strip',
          'Coarse rock | circular light clearance','Coarse rock | weld coincident backing vertices']]
new_mods=[mod for mod in new_mods if mod]
def enabled(value):
    for mod in new_mods:mod.show_viewport=value
ctrl=bpy.data.objects['SCENE SLIDERS'];cm=ctrl.modifiers['Scene Sliders']
sockets={i.name:i.identifier for i in cm.node_group.interface.items_tree if i.item_type=='SOCKET' and i.in_out=='INPUT'}
hk=sockets['Light height above walls (m)'];rk=sockets['Light radius (m)']
initial=(cm[hk],cm[rk])
M=d.matrix_world.inverted()@w.matrix_world

def refresh(controls=False):
    if controls: ctrl.update_tag()
    bpy.context.view_layer.update()

def clearances():
    dg=bpy.context.evaluated_depsgraph_get();e=w.evaluated_get(dg)
    mx=e.matrix_world.inverted()@d.matrix_world;H=d['deck_height_m']
    walk=[]
    for i in range(25):
        for j in range(25):
            x=-2.8+5.6*i/24;y=-2.8+5.6*j/24
            if abs(x)+abs(y)>4.32:continue
            origin=mx@Vector((x,y,H+.035))
            hit,p,normal,face=e.ray_cast(origin,Vector((0,0,1)),distance=1.7)
            if hit:
                # A snug backing behind the sloped metal walls is intentional.
                # Count only rock encountered before the opaque architecture.
                target=bpy.data.objects.get('Platform backing | live fitting surfaces')
                if target:
                    te=target.evaluated_get(dg)
                    blocked,q,nn,ff=te.ray_cast(origin,Vector((0,0,1)),distance=1.7)
                    if blocked and p.z>=q.z-.015:continue
                walk.append((i,j))
    root=bpy.data.objects['Lower | circular roof assembly']
    cover=bpy.data.objects['Lower | circular light upper cover'].evaluated_get(dg)
    vs=[cover.matrix_world@v.co for v in cover.data.vertices]
    top=max(p.z for p in vs);center=e.matrix_world.inverted()@root.matrix_world.translation
    rad=max((Vector((p.x,p.y))-root.matrix_world.translation.xy).length for p in vs)
    light=[]
    for i in range(17):
        for j in range(17):
            x=rad*(i-8)/8*.94;y=rad*(j-8)/8*.94
            if x*x+y*y>rad*rad*.94**2:continue
            if e.ray_cast(Vector((center.x+x,center.y+y,top-.22)),Vector((0,0,1)),distance=.225)[0]:light.append((i,j))
    return {'walk':walk,'light':light}

checks=[]
try:
    for height,radius in [initial,(.35,.85),(1.49,1.46),(2.1,2.1)]:
        cm[hk]=height;cm[rk]=radius;enabled(False);refresh(True);before=clearances()
        enabled(True);refresh();after=clearances()
        checks.append({'height':height,'radius':radius,'new_walk_intrusions':len(set(after['walk'])-set(before['walk'])),
                       'new_light_intrusions':len(set(after['light'])-set(before['light'])),
                       'baseline_walk_intrusions':len(before['walk']),'baseline_light_intrusions':len(before['light'])})
finally:
    cm[hk],cm[rk]=initial;enabled(True);refresh(True)

enabled(False);refresh();source=w.evaluated_get(bpy.context.evaluated_depsgraph_get())
before=[v.co.copy() for v in source.data.vertices]
region=lambda p: -3<p.x<7 and -6.5<p.y<4.5 and 6<p.z<15.5
src_ids={i for i,p in enumerate(before) if region(M@p)}
local_before=sum(all(i in src_ids for i in f.vertices) for f in source.data.polygons)
group=w.vertex_groups[m.vertex_group].index
outside=[v.co.copy() for v in source.data.vertices if not any(g.group==group and g.weight>0 for g in v.groups)]
src_tris=sum(len(p.vertices)-2 for p in source.data.polygons)
enabled(True);refresh();e=w.evaluated_get(bpy.context.evaluated_depsgraph_get())
ps=[v.co.copy() for v in e.data.vertices]
ids={i for i,p in enumerate(ps) if region(M@p)}
local_after=sum(all(i in ids for i in f.vertices) for f in e.data.polygons)
lengths=[(ps[a]-ps[b]).length for a,b in [ed.vertices for ed in e.data.edges] if a in ids and b in ids]
tree=BVHTree.FromPolygons(ps,[list(f.vertices) for f in e.data.polygons])
dist=sorted(tree.find_nearest(before[i])[3] for i in sorted(src_ids)[::5])
kd=KDTree(len(ps))
for i,p in enumerate(ps):kd.insert(p,i)
kd.balance()
outside_max=max(kd.find(p)[2] for p in outside)
bm=bmesh.new();bm.from_mesh(e.data);left=set(bm.verts);components=0
while left:
    components+=1;stack=[left.pop()]
    while stack:
        v=stack.pop()
        for ed in v.link_edges:
            other=ed.other_vert(v)
            if other in left:left.remove(other);stack.append(other)

def fingerprint(o):
    h=hashlib.sha256(repr(([list(r) for r in o.matrix_world],o.hide_render,o.hide_get(),o.data.name if o.data else None)).encode())
    if o.type=='MESH':
        a=array.array('f',[0.])* (len(o.data.vertices)*3);o.data.vertices.foreach_get('co',a);h.update(a.tobytes())
    return h.hexdigest()
protected=json.loads((P/'protected-before.json').read_text())
changed=[name for name,h in protected.items() if name not in bpy.data.objects or fingerprint(bpy.data.objects[name])!=h]
result={'source_triangles':src_tris,'evaluated_triangles':sum(len(f.vertices)-2 for f in e.data.polygons),
        'local_triangles_before':local_before,'local_triangles_after':local_after,'local_median_edge_m':statistics.median(lengths),
        'surface_deviation_p95_m':dist[int(len(dist)*.95)],'surface_deviation_max_m':max(dist),
        'outside_unchanged_vertices':len(outside),'outside_max_displacement_m':outside_max,
        'connected_components':components,'loose_edges':sum(not ed.link_faces for ed in bm.edges),
        'nonmanifold_junctions':sum(len(ed.link_faces)>2 for ed in bm.edges),
        'degenerate_faces':sum(f.calc_area()<1e-10 for f in bm.faces),
        'control_checks':checks,'restored_controls':initial,'protected_objects':len(protected),'changed_unrelated_objects':changed,
        'source_shape_keys':len(w.data.shape_keys.key_blocks),'viewport_render_consistent':all(md.show_viewport==md.show_render for md in w.modifiers)}
bm.free();(P/'verification.json').write_text(json.dumps(result,indent=2))
assert components==1 and result['loose_edges']==0 and result['nonmanifold_junctions']==0
assert result['degenerate_faces']==0
assert outside_max<1e-5
assert not any(c['new_walk_intrusions'] or c['new_light_intrusions'] for c in checks)
