"""Apply baked grating cards in the current scene, preserving rigs and frames."""
import bpy, json, hashlib, array
from pathlib import Path

P=Path(__file__).resolve().parent
S=bpy.context.scene
rows=json.loads((P/'replacement-geometry.json').read_text())
source={r['name']:r for r in json.loads((P/'source-geometry.json').read_text())}
targets={r['name'] for r in rows}
assert Path(bpy.data.filepath).name=='cave-platform-sliders.blend', bpy.data.filepath

def fingerprint(o):
    h=hashlib.sha256(repr([list(r) for r in o.matrix_world]).encode())
    if o.type=='MESH':
        data=array.array('f',[0])*(len(o.data.vertices)*3)
        o.data.vertices.foreach_get('co',data)
        h.update(data.tobytes())
        h.update(repr([tuple(p.vertices) for p in o.data.polygons]).encode())
        h.update(repr([m.name if m else None for m in o.data.materials]).encode())
    return h.hexdigest()

untouched={o.name:fingerprint(o) for o in S.objects if o.name not in targets}
for row in rows:
    o=bpy.data.objects[row['name']]
    assert not o.get('texture_grating'), 'Already converted: '+o.name
    old=source[o.name]
    assert len(o.data.vertices)==len(old['vertices']), 'Mesh edited since inspection: '+o.name
    assert all((v.co.x-p[0])**2+(v.co.y-p[1])**2+(v.co.z-p[2])**2<1e-14
               for v,p in zip(o.data.vertices,old['vertices'])),o.name

materials={}
for row in rows:
    key=row['texture']
    if key in materials:continue
    material=bpy.data.materials[row['material']].copy()
    material.name='Grating texture | '+key
    material.use_backface_culling=False
    if hasattr(material,'surface_render_method'):material.surface_render_method='DITHERED'
    nodes=material.node_tree.nodes;links=material.node_tree.links
    bsdf=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
    uv=nodes.new('ShaderNodeUVMap');uv.uv_map='GratingUV';uv.location=(-700,0)
    for role in ['color','normal']:
        path=P/'textures'/(key+'-'+role+'.png')
        img=bpy.data.images.load(str(path),check_existing=True)
        img.name='Grating | '+key+' | '+role
        img.colorspace_settings.name='sRGB' if role=='color' else 'Non-Color'
        img.alpha_mode='STRAIGHT'
        img.pack()
        tex=nodes.new('ShaderNodeTexImage');tex.image=img;tex.extension='EXTEND';tex.interpolation='Linear'
        tex.location=(-470,180 if role=='color' else -150)
        links.new(uv.outputs['UV'],tex.inputs['Vector'])
        if role=='color':
            links.new(tex.outputs['Color'],bsdf.inputs['Base Color'])
            links.new(tex.outputs['Alpha'],bsdf.inputs['Alpha'])
        else:
            norm=nodes.new('ShaderNodeNormalMap');norm.uv_map='GratingUV';norm.location=(-180,-120)
            links.new(tex.outputs['Color'],norm.inputs['Color'])
            links.new(norm.outputs['Normal'],bsdf.inputs['Normal'])
    material['grating_bake']='Exact source bar footprint; alpha holes and bevel normal; reusable packed images'
    materials[key]=material

for row in rows:
    o=bpy.data.objects[row['name']]
    me=bpy.data.meshes.new(o.data.name+' | textured surface')
    me.from_pydata(row['vertices'],[],row['faces']);me.update()
    uv=me.uv_layers.new(name='GratingUV')
    for face in me.polygons:
        for index in face.loop_indices:
            uv.data[index].uv=row['uv'][me.loops[index].vertex_index]
    for name,values in row['attributes'].items():
        attr=me.attributes.new(name,'FLOAT','POINT')
        attr.data.foreach_set('value',values)
    me.materials.append(materials[row['texture']])
    o.data=me
    for mod in list(o.modifiers):
        if mod.type in {'BEVEL','WEIGHTED_NORMAL'}:o.modifiers.remove(mod)
    o['texture_grating']=True
    o['grating_before_triangles']=row['before_triangles']
    o['grating_uv_direction']='Original sector radial/tangent frame' if o.name.startswith('Metal |') else 'Original fabrication axes'

bpy.context.view_layer.update()
DG=bpy.context.evaluated_depsgraph_get()
report=[]
for row in rows:
    o=bpy.data.objects[row['name']];ev=o.evaluated_get(DG);me=ev.to_mesh();me.calc_loop_triangles()
    assert len(me.polygons)>0, 'Empty evaluated replacement: '+o.name
    report.append({'name':o.name,'before_triangles':row['before_triangles'],
                   'after_triangles':len(me.loop_triangles),'vertices':len(me.vertices),
                   'modifiers':[m.type for m in o.modifiers]})
    ev.to_mesh_clear()
assert all(fingerprint(bpy.data.objects[n])==sig for n,sig in untouched.items()), 'Unrelated object changed'
summary={'file':bpy.data.filepath,'objects':len(rows),'materials':len(materials),
         'before_triangles':sum(r['before_triangles'] for r in report),
         'after_triangles':sum(r['after_triangles'] for r in report),
         'unchanged_objects':len(untouched),'details':report}
(P/'verification.json').write_text(json.dumps(summary,indent=2))
S['grating_optimization']='Baked source geometry to alpha/normal cards; circular sector UVs, packed textures, original live rig controls'
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
result={k:v for k,v in summary.items() if k!='details'}
