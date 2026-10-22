"""Reopen both scenes and check the shading fix preserved modeling and controls."""
import bpy, array, hashlib, json
from pathlib import Path
P=Path(__file__).resolve().parent
WALL='150 | continuous cave with oblique carved rooms'

def digest(values):
    return hashlib.sha256(values).hexdigest()

def snapshot(path):
    bpy.ops.wm.open_mainfile(filepath=str(path))
    bpy.context.view_layer.update()
    meshes={};objects={}
    for o in bpy.context.scene.objects:
        record={'type':o.type,'matrix':[list(row) for row in o.matrix_world],
                'modifiers':[(m.name,m.type) for m in o.modifiers],
                'hide_render':o.hide_render}
        if o.type=='MESH':
            me=o.data
            key=me.as_pointer()
            if key not in meshes:
                coords=array.array('f',[0])*(len(me.vertices)*3);me.vertices.foreach_get('co',coords)
                # Face orientation is intentionally reversed; connectivity must stay identical.
                faces=sorted(tuple(sorted(f.vertices)) for f in me.polygons)
                smooth=array.array('b',[0])*len(me.polygons);me.polygons.foreach_get('use_smooth',smooth)
                mats=array.array('i',[0])*len(me.polygons);me.polygons.foreach_get('material_index',mats)
                meshes[key]={'vertices':digest(coords.tobytes()),'faces':digest(repr(faces).encode()),'smooth':digest(smooth.tobytes()),'material_indices':digest(mats.tobytes())}
            record['mesh']=meshes[key]
        objects[o.name]=record
    cam=bpy.context.scene.camera
    ctrl=bpy.data.objects['LIGHTING CONTROLS'];mod=ctrl.modifiers['Reference Lighting']
    settings={k:(list(v) if hasattr(v,'__len__') and not isinstance(v,str) else v) for k,v in mod.items() if k!='_RNA_UI'}
    wall=bpy.data.objects[WALL].data
    normals=[list(p.normal) for p in wall.polygons]
    def canonical(vertices):
        values=list(vertices)
        first=values.index(min(values))
        return tuple(values[first:]+values[:first])
    winding=[canonical(p.vertices) for p in wall.polygons]
    reversed_winding=[canonical(list(p.vertices)[::-1]) for p in wall.polygons]
    return {'objects':objects,'camera':{'name':cam.name,'lens':cam.data.lens,'matrix':[list(row) for row in cam.matrix_world]},'lighting_controls':settings,'wall_normals':normals,'winding':winding,'reversed_winding':reversed_winding}

before=snapshot(P/'before-applying-fix.blend')
after=snapshot(P.parent/'platform-controls/cave-platform-sliders.blend')
changed=[]
for name,values in before['objects'].items():
    if values!=after['objects'].get(name):changed.append(name)
allowed=['RL | Cave | lower reflected bounce -1','RL | Cave | lower reflected bounce +1']
invalid=[]
for data in list(bpy.data.objects)+list(bpy.data.lights)+list(bpy.data.node_groups)+[m.node_tree for m in bpy.data.materials if m.use_nodes]:
    if data.animation_data:
        invalid.extend((data.name,f.data_path) for f in data.animation_data.drivers if not f.driver.is_valid)
normal_error=max(max(abs(a+b) for a,b in zip(x,y)) for x,y in zip(before['wall_normals'],after['wall_normals']))
report={'objects_checked':len(before['objects']),'changed_object_records':changed,
        'unexpected_changes':[n for n in changed if n not in allowed],
        'added_objects':sorted(set(after['objects'])-set(before['objects'])),
        'camera_preserved':before['camera']==after['camera'],
        'lighting_controls_preserved':before['lighting_controls']==after['lighting_controls'],
        'wall_normal_reversal_max_error':normal_error,
        'all_cave_faces_reversed_exactly':after['winding']==before['reversed_winding'],
        'invalid_drivers':invalid}
# Exact winding is authoritative; float normals of very thin triangles vary slightly
# when their cross products are recomputed in the opposite vertex order.
report['passed']=not report['unexpected_changes'] and not report['added_objects'] and report['camera_preserved'] and report['lighting_controls_preserved'] and report['all_cave_faces_reversed_exactly'] and not invalid
(P/'verification.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2),flush=True)
assert report['passed'],report
