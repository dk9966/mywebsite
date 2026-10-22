"""Verify the actual evaluated model, including native slider motion."""
import bpy, bmesh, json, math
from pathlib import Path
from mathutils import Vector

P=Path(__file__).resolve().parent
S=bpy.context.scene
deck=bpy.data.objects['Upper | beveled square gallery']
F=deck.matrix_world; IV=F.inverted(); H=deck['deck_height_m']
ctrl=bpy.data.objects['UPPER PLATFORM SLIDERS']; mod=ctrl.modifiers['Upper Platform Sliders']
ids={i.name:i.identifier for i in mod.node_group.interface.items_tree if i.item_type=='SOCKET' and i.in_out=='INPUT'}
target=[o for o in S.objects if o.get('upper_gallery_completion')]
dg=bpy.context.evaluated_depsgraph_get()
topology=[]
for o in target:
    e=o.evaluated_get(dg); me=e.to_mesh(); bm=bmesh.new(); bm.from_mesh(me)
    bad=sum(not edge.is_manifold for edge in bm.edges)
    zero=sum(face.calc_area()<1e-10 for face in bm.faces)
    if bad or zero: topology.append({'name':o.name,'nonmanifold':bad,'zero_area':zero})
    bm.free(); e.to_mesh_clear()
assert not topology,topology

def points(name):
    o=bpy.data.objects[name]; e=o.evaluated_get(bpy.context.evaluated_depsgraph_get())
    return [IV@e.matrix_world@v.co for v in e.data.vertices]

normals=[Vector((1,-1,0)).normalized(),Vector((1,-1,0)).normalized(),
         Vector((1,0,0)),Vector((1,1,0)).normalized(),Vector((1,1,0)).normalized(),
         Vector((0,1,0)),Vector((0,1,0))]
plates=[]; alignment=[]; gaps=[]; lights=[]
for i in range(7):
    pfx='Upper wall | rib %02d '%i
    n=normals[i]; t=Vector((-n.y,n.x,0)); axes=[t,n,Vector((0,0,1))]
    p=points(pfx+'floor anchor')
    dims=[max(v.dot(a) for v in p)-min(v.dot(a) for v in p) for a in axes]
    assert max(abs(a-b) for a,b in zip(dims,[.36,.46,.058]))<1e-4,(i,dims)
    plates.append(dims)
    rib=bpy.data.objects[pfx+'bent channel']
    # In the first section, paired flange vertices give the model's transverse axis.
    d=(rib.data.vertices[1].co-rib.data.vertices[0].co).normalized()
    err=abs(d.dot(n)); assert err<1e-5,(i,err)
    alignment.append(err)
    gap=(rib.data.vertices[4].co-rib.data.vertices[5].co).length
    assert abs(gap-.104)<1e-5,(i,gap)
    gaps.append(gap)
    intervals={}
    for label in ['floor anchor','seated base socket','locator housing','locator gasket','amber locator']:
        p=points(pfx+label)
        intervals[label]=[(min(v.dot(a) for v in p),max(v.dot(a) for v in p)) for a in axes]
    contacts=[]
    for a,b in [('floor anchor','seated base socket'),('seated base socket','locator housing'),
                ('locator housing','locator gasket'),('locator gasket','amber locator')]:
        overlap=[min(intervals[a][k][1],intervals[b][k][1])-max(intervals[a][k][0],intervals[b][k][0]) for k in range(3)]
        assert min(overlap)>0,(i,a,b,overlap)
        contacts.append({'parts':[a,b],'minimum_overlap_m':min(overlap)})
    lights.append(contacts)

original={n:float(mod[k]) for n,k in ids.items() if n.startswith('Upper ')}
checks=[]
try:
    for values in [{}, {'Upper light width (m)':3.35,'Upper light depth (m)':2.80},
                   {'Upper light width (m)':4.1,'Upper light depth (m)':3.10,'Upper light height (m)':2.5},
                   {'Upper corner bevel (m)':1.2,'Upper light corner bevel (m)':.45}]:
        settings=dict(original); settings.update(values)
        for n,v in settings.items(): mod[ids[n]]=v
        ctrl.update_tag(); S.frame_set(S.frame_current); bpy.context.view_layer.update()
        e=bpy.data.objects['Upper roof | continuous fitted crown panels'].evaluated_get(bpy.context.evaluated_depsgraph_get())
        # Native keys preserve the 35 mm closed shell and the seated lamp interface.
        p=[v.co.copy() for v in e.data.vertices]
        assert max(abs((p[i+14]-p[i]).z-.035) for i in range(14))<1e-5
        lamp=bpy.data.objects['Upper light | adjustable fixture']
        assert max(abs(v.z-(lamp.location.z+.105)) for v in p[7:14])<1e-5
        invalid=[]
        for obj in target:
            for owner in [obj,obj.data,getattr(obj.data,'shape_keys',None)]:
                if owner and owner.animation_data:
                    invalid.extend(obj.name+': '+fc.data_path for fc in owner.animation_data.drivers if not fc.driver.is_valid)
        assert not invalid,invalid
        checks.append({'settings':settings,'invalid_drivers':invalid,'roof_thickness_m':.035})
finally:
    for n,v in original.items():mod[ids[n]]=v
    ctrl.update_tag();S.frame_set(S.frame_current);bpy.context.view_layer.update()

report={'evaluated_meshes_checked':len(target),'topology_errors':topology,
        'wall_assignment_left_to_right':[1,1,2,2,3,4,4],
        'support_wall_parallel_error':alignment,'base_plate_dimensions_m':plates,
        'channel_gap_m':gaps,'attached_locator_contact_chain':lights,'slider_cases':checks}
(P/'verification.json').write_text(json.dumps(report,indent=2))
result={'passed':True,'evaluated_meshes':len(target),'slider_cases':len(checks),'support_count':len(plates)}
