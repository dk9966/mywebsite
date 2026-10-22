"""Double the triangle count without changing the faceted surface or layout."""
import bpy,bmesh,json,hashlib,array
from pathlib import Path
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P/'density-2x-source.blend'))
if bpy.context.object and bpy.context.object.mode!='OBJECT':bpy.ops.object.mode_set(mode='OBJECT')
bpy.context.preferences.filepaths.save_version=0
names=['150 | continuous cave with oblique carved rooms','Central rock mound | continuous cross-column extrusions']
def fingerprint(o):
    h=hashlib.sha256(repr([list(r) for r in o.matrix_world]).encode())
    if o.type=='MESH':
        a=array.array('f',[0.])*(len(o.data.vertices)*3);o.data.vertices.foreach_get('co',a);h.update(a.tobytes())
    return h.hexdigest()
before={o.name:fingerprint(o) for o in bpy.context.scene.objects if o.name not in names}
report={}
for name in names:
    ob=bpy.data.objects[name];old=ob.data
    assert all(len(f.vertices)==3 for f in old.polygons)
    vertices=[v.co.copy() for v in old.vertices]
    edges={}
    for f in old.polygons:
        a,b,c=f.vertices
        for e in [(a,b),(b,c),(c,a)]:edges.setdefault(tuple(sorted(e)),[]).append(f.index)
    # Prefer longest edges and distribute splits over the whole terrain.
    candidates=sorted([e for e,fs in edges.items() if len(fs)==2],key=lambda e:(vertices[e[0]]-vertices[e[1]]).length_squared,reverse=True)
    target=len(old.polygons)//2;selected=set();covered=set()
    for max_covered in [0,1,2]:
        for e in candidates:
            if len(selected)==target:break
            if e not in selected and sum(f in covered for f in edges[e])<=max_covered:
                selected.add(e);covered.update(edges[e])
    mids={}
    for e in sorted(selected):
        mids[e]=len(vertices);vertices.append((vertices[e[0]]+vertices[e[1]])*.5)
    faces=[];source_faces=[]
    for f in old.polygons:
        v=list(f.vertices)
        split=[tuple(sorted((v[i],v[(i+1)%3]))) in mids for i in range(3)]
        k=sum(split)
        if k==0:out=[v]
        elif k==1:
            j=split.index(True);a,b,c=v[j],v[(j+1)%3],v[(j+2)%3];m=mids[tuple(sorted((a,b)))];out=[(a,m,c),(m,b,c)]
        elif k==2:
            # Rotate so the two split edges are AB and BC.
            j=(split.index(False)+1)%3;a,b,c=v[j],v[(j+1)%3],v[(j+2)%3]
            ab=mids[tuple(sorted((a,b)))];bc=mids[tuple(sorted((b,c)))]
            out=[(ab,b,bc)]
            if (vertices[a]-vertices[bc]).length_squared<(vertices[ab]-vertices[c]).length_squared:out.extend([(a,ab,bc),(a,bc,c)])
            else:out.extend([(a,ab,c),(ab,bc,c)])
        else:
            a,b,c=v;ab=mids[tuple(sorted((a,b)))];bc=mids[tuple(sorted((b,c)))];ca=mids[tuple(sorted((c,a)))];out=[(a,ab,ca),(ab,b,bc),(ca,bc,c),(ab,bc,ca)]
        faces.extend(out);source_faces.extend([f.index]*len(out))
    me=bpy.data.meshes.new(old.name+' | double density');me.from_pydata(vertices,[],faces);me.update()
    for m in old.materials:me.materials.append(m)
    for f,src in zip(me.polygons,source_faces):f.material_index=old.polygons[src].material_index;f.use_smooth=old.polygons[src].use_smooth
    # Preserve sculpt masks and face-set attributes if present in the live file.
    for attr in old.attributes:
        if attr.name.startswith('.') and attr.name not in {'.sculpt_mask','.sculpt_face_set'}:continue
        if attr.name in {'position','material_index','sharp_face','sharp_edge'}:continue
        if attr.data_type not in {'FLOAT','INT','BOOLEAN'} or attr.domain not in {'POINT','FACE'}:continue
        dst=me.attributes.new(attr.name,attr.data_type,attr.domain)
        if attr.domain=='FACE':
            for i,src in enumerate(source_faces):dst.data[i].value=attr.data[src].value
        else:
            for i in range(len(old.vertices)):dst.data[i].value=attr.data[i].value
            for (a,b),i in mids.items():
                value=(attr.data[a].value+attr.data[b].value)/2
                dst.data[i].value=value if attr.data_type=='FLOAT' else round(value)
    bm=bmesh.new();bm.from_mesh(me)
    invalid=sum(len(e.link_faces)>2 or not e.link_faces for e in bm.edges)
    boundary=sum(e.is_boundary for e in bm.edges);bm.free()
    old_area=sum(f.area for f in old.polygons);new_area=sum(f.area for f in me.polygons)
    # All added points are edge midpoints and all new faces partition an old
    # planar triangle. These checks detect missing/overlapping or flipped faces.
    normal_error=max(1-me.polygons[i].normal.dot(old.polygons[src].normal) for i,src in enumerate(source_faces))
    assert len(me.polygons)==2*len(old.polygons)
    assert invalid==0 and abs(new_area-old_area)<old_area*1e-5 and normal_error<1e-4
    report[name]={'before_triangles':len(old.polygons),'after_triangles':len(me.polygons),'average_area_ratio':old_area/len(me.polygons)/(old_area/len(old.polygons)),'shape_preserved':True,'invalid_edges':invalid,'boundary_edges':boundary}
    ob.data=me;ob['density_multiplier']=2
    if 'low_poly_triangles' in ob:ob['low_poly_triangles']=len(me.polygons)
report['other_object_changes']=[n for n,h in before.items() if fingerprint(bpy.data.objects[n])!=h]
assert not report['other_object_changes']
(P/'density-2x-checks.json').write_text(json.dumps(report,indent=2))
bpy.context.scene.name='Cave | faceted terrain with double triangle density'
bpy.ops.wm.save_as_mainfile(filepath=str(P/'cave-faceted-sculpt-2x.blend'),compress=True)
print('DENSITY_RESULT',json.dumps(report),flush=True)
