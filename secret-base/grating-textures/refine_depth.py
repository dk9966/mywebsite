"""Sparse textured depth sheets recover bar occlusion at grazing angles."""
import bpy,json
from pathlib import Path
P=Path(__file__).resolve().parent
rows=json.loads((P/'replacement-geometry.json').read_text())
source={r['name']:r for r in json.loads((P/'source-geometry.json').read_text())}
for row in rows:
    ob=bpy.data.objects[row['name']]
    assert ob.get('texture_grating')
    material=ob.data.materials[0]
    closed=any(m.type=='BOOLEAN' for m in ob.modifiers)
    thin='crossbar cassette' in ob.name
    layers=3 if closed or thin else 5
    depth=.010 if thin else .022
    count=len(row['vertices'])
    vertices=[(x,y,z-depth*k/(layers-1)) for k in range(layers) for x,y,z in row['vertices']]
    faces=[tuple(i+count*k for i in face) for k in range(layers) for face in row['faces']]
    mesh=bpy.data.meshes.new(ob.name+' | textured depth sheets')
    mesh.from_pydata(vertices,[],faces);mesh.update()
    uv=mesh.uv_layers.new(name='GratingUV')
    for loop in mesh.loops:
        uv.data[loop.index].uv=row['uv'][loop.vertex_index%count]
    for name,values in row['attributes'].items():
        attr=mesh.attributes.new(name,'FLOAT','POINT')
        attr.data.foreach_set('value',values*layers)
    mesh.materials.append(material);ob.data=mesh
    ob['grating_depth_sheets']=layers
bpy.context.view_layer.update()
DG=bpy.context.evaluated_depsgraph_get()
report=json.loads((P/'verification.json').read_text())
for row in report['details']:
    ob=bpy.data.objects[row['name']];ev=ob.evaluated_get(DG);mesh=ev.to_mesh();mesh.calc_loop_triangles()
    assert len(mesh.polygons)>0,ob.name
    row['after_triangles']=len(mesh.loop_triangles);row['vertices']=len(mesh.vertices)
    row['depth_sheets']=ob['grating_depth_sheets'];ev.to_mesh_clear()
report['after_triangles']=sum(r['after_triangles'] for r in report['details'])
report['depth_refinement']='3–5 sparse textured sheets within the original bar depth'
(P/'verification.json').write_text(json.dumps(report,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
result={k:v for k,v in report.items() if k!='details'}
