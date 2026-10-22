"""Check the evaluated lamp, mirrored return, ceiling, and unchanged wall positions."""
import bpy, bmesh, json, array, hashlib
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent
report=json.loads((P/'build-report.json').read_text())
S=bpy.context.scene;ctrl=bpy.data.objects['UPPER PLATFORM SLIDERS'];mod=ctrl.modifiers['Upper Platform Sliders']
ids={i.name:i.identifier for i in mod.node_group.interface.items_tree if i.item_type=='SOCKET'}
settings={name:float(mod[ids[name]]) for name in ['Upper light width (m)','Upper light depth (m)']}
roof=bpy.data.objects['Upper roof | continuous fitted crown panels']

def coords(o):
    return [v.co.copy() for v in o.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices]

def wall_signature(o):
    e=o.evaluated_get(bpy.context.evaluated_depsgraph_get())
    h=hashlib.sha256(repr(([list(r) for r in e.matrix_world],o.hide_render,o.hide_get(),
                          o.parent.name if o.parent else None,sorted(c.name for c in o.users_collection))).encode())
    data=e.data;co=array.array('f',[0])*(3*len(data.vertices));data.vertices.foreach_get('co',co)
    h.update(co.tobytes());h.update(repr([tuple(p.vertices) for p in data.polygons]).encode())
    return h.hexdigest()

wall_before=json.loads((P/'wall-positions-before.json').read_text())
assert all(wall_signature(bpy.data.objects[n])==h for n,h in wall_before.items())
before=coords(roof);checks=[]
try:
    for factor in [1,1.15]:
        for name,value in settings.items():mod[ids[name]]=value*factor
        ctrl.update_tag();S.frame_set(S.frame_current);bpy.context.view_layer.update()
        p=coords(roof)
        assert max((a-b).length for a,b in zip(before[:7],p[:7]))<1e-5
        assert max(abs((p[i+14]-p[i]).z-.035) for i in range(14))<1e-5
        assert all(wall_signature(bpy.data.objects[n])==h for n,h in wall_before.items())
        lamp=coords(bpy.data.objects['Upper light | broad chamfered housing'])
        dims=[max(v[k] for v in lamp)-min(v[k] for v in lamp) for k in range(2)]
        assert max(abs(a-b*factor) for a,b in zip(dims,settings.values()))<1e-5
        checks.append({'factor':factor,'lamp_dimensions_m':dims,'wall_and_roof_outer_edge_fixed':True})
finally:
    for name,value in settings.items():mod[ids[name]]=value
    ctrl.update_tag();S.frame_set(S.frame_current);bpy.context.view_layer.update()

names=report['updated']+[b for a,b in report['mirrored']]+[o.name for o in bpy.data.collections['173 | Adjustable beveled rectangular light'].objects if o.type=='MESH']
issues=[];invalid=[];dg=bpy.context.evaluated_depsgraph_get()
for name in names:
    o=bpy.data.objects[name];e=o.evaluated_get(dg);me=e.to_mesh();bm=bmesh.new();bm.from_mesh(me)
    if any(not edge.is_manifold for edge in bm.edges) or any(f.calc_area()<1e-10 for f in bm.faces):issues.append(name)
    bm.free();e.to_mesh_clear()
    for owner in [o,o.data,getattr(o.data,'shape_keys',None)]:
        if owner and owner.animation_data:
            invalid.extend((name,f.data_path) for f in owner.animation_data.drivers if not f.driver.is_valid)
assert not issues,issues
assert not invalid,invalid
errors=[]
for a,b in report['mirrored']:
    pa=[Vector((v.x,-v.y,v.z)) for v in coords(bpy.data.objects[a])]
    pb=coords(bpy.data.objects[b])
    errors.append(max(min((v-u).length for u in pb) for v in pa))
assert max(errors)<.0001,errors  # under 0.1 mm; the bevel solver can reorder intersections
result={'passed':True,'evaluated_meshes_checked':len(names),'topology_issues':issues,
        'invalid_drivers':invalid,'mirrored_parts':len(errors),'maximum_mirror_error_m':max(errors),
        'retained_wall_objects_unchanged':len(wall_before),'slider_checks':checks}
(P/'verification.json').write_text(json.dumps(result,indent=2))
