import bpy,bmesh,json,hashlib,array,statistics
from pathlib import Path
from mathutils import Vector
from mathutils.kdtree import KDTree
P=Path(__file__).resolve().parent
w=bpy.data.objects['Candidate | direct terrain cleanup']
base=bpy.data.meshes[w['baseline_mesh']]
deck=bpy.data.objects['Upper | beveled square gallery'];M=deck.matrix_world.inverted()@w.matrix_world
def audit(mesh):
    bm=bmesh.new();bm.from_mesh(mesh)
    left=set(bm.verts);components=0
    while left:
        components+=1;stack=[left.pop()]
        while stack:
            v=stack.pop()
            for ed in v.link_edges:
                q=ed.other_vert(v)
                if q in left:left.remove(q);stack.append(q)
    local=[f for f in bm.faces if -7<(M@f.calc_center_median()).x<6 and -10<(M@f.calc_center_median()).y<4 and 4<(M@f.calc_center_median()).z<16]
    r={'vertices':len(bm.verts),'triangles':len(bm.faces),'components':components,
       'boundary_edges':sum(e.is_boundary for e in bm.edges),'loose_edges':sum(not e.link_faces for e in bm.edges),
       'nonmanifold_junctions':sum(len(e.link_faces)>2 for e in bm.edges),'degenerate_faces':sum(f.calc_area()<1e-10 for f in bm.faces),
       'region_triangles':len(local),'region_tiny_faces':sum(f.calc_area()<.06 for f in local)}
    bm.free();return r
before=audit(base);after=audit(w.data)
kd=KDTree(len(w.data.vertices))
for v in w.data.vertices:kd.insert(v.co,v.index)
kd.balance()
unchanged=sum(kd.find(v.co)[2]<1e-6 for v in base.vertices)
def fingerprint(o):
    h=hashlib.sha256(repr((o.type,[list(r) for r in o.matrix_world],o.hide_render,o.hide_get(),o.data.name if o.data else None)).encode())
    if o.type=='MESH':
        a=array.array('f',[0.]*(len(o.data.vertices)*3));o.data.vertices.foreach_get('co',a);h.update(a.tobytes())
    return h.hexdigest()
saved=json.loads((P/'protected-before.json').read_text())
changed=[name for name,h in saved.items() if name not in bpy.data.objects or fingerprint(bpy.data.objects[name])!=h]
# Reuse the earlier read-only clearance sampler at the current fixture settings.
ns={'__file__':str(P.parent/'sculpt-seam-repair'/'verify.py')}
text=(P.parent/'sculpt-seam-repair'/'verify.py').read_text().split('checks=[]')[0]
exec(compile(text,ns['__file__'],'exec'),ns)
previous=ns['clearances']()
ns['w']=w
current=ns['clearances']()
result={'before':before,'after':after,'unchanged_baseline_vertices':unchanged,
        'original_objects_changed':changed,'original_objects_checked':len(saved),
        'new_upper_walk_intrusions':len(set(current['walk'])-set(previous['walk'])),
        'new_light_intrusions':len(set(current['light'])-set(previous['light'])),
        'light_min_gap':current['coverage_distance_min'],
        'candidate_modifiers':len(w.modifiers),'candidate_shape_keys':bool(w.data.shape_keys),
        'original_modifiers_preserved':len(bpy.data.objects[w['original_object']].modifiers)}
(P/'verification.json').write_text(json.dumps(result,indent=2))
assert not changed
assert after['components']==before['components']==1
assert after['boundary_edges']==before['boundary_edges']
assert not after['loose_edges'] and not after['nonmanifold_junctions'] and not after['degenerate_faces']
assert not result['new_upper_walk_intrusions'] and not result['new_light_intrusions']
