"""Read both saved files and independently compare the protected center assembly."""
import bpy, hashlib, json, sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'secret-base/mound-study/central-platform-rock-mound-balanced.blend'
TARGET=Path(sys.argv[sys.argv.index('--')+1]) if '--' in sys.argv else ROOT/'secret-base/cavern-layout/cavern-approved-terrain.blend'

def values(v):
    if isinstance(v,(str,bool,int,float)) or v is None:return v
    if isinstance(v,bpy.types.ID):return {'type':v.bl_rna.identifier,'name':v.name}
    try:return [values(x) for x in v]
    except TypeError:return str(v)
def props(block):
    d={}
    for p in block.bl_rna.properties:
        if p.identifier in {'rna_type','id_data','name','name_full'} or p.type=='COLLECTION' or p.is_readonly:continue
        try:d[p.identifier]=values(getattr(block,p.identifier))
        except (TypeError,AttributeError):pass
    return d
def material(m):
    if m is None:return None
    d={'name':m.name,'properties':props(m)}
    if m.use_nodes:
        d['nodes']={n.name:{'type':n.bl_idname,'properties':props(n),'inputs':{s.identifier:values(s.default_value) for s in n.inputs if hasattr(s,'default_value')}} for n in m.node_tree.nodes}
        d['links']=sorted((l.from_node.name,l.from_socket.identifier,l.to_node.name,l.to_socket.identifier) for l in m.node_tree.links)
    return d
def fingerprint(o):
    h=hashlib.sha256()
    h.update(np.array(o.matrix_world,dtype=np.float64).tobytes())
    for attr,field,size,dtype in [('vertices','co',3,np.float32),('loops','vertex_index',1,np.int32),('polygons','material_index',1,np.int32)]:
        src=getattr(o.data,attr);a=np.empty(len(src)*size,dtype=dtype);src.foreach_get(field,a);h.update(a.tobytes())
    h.update(json.dumps([material(m) for m in o.data.materials],sort_keys=True).encode())
    h.update(json.dumps([{'type':m.type,'props':props(m)} for m in o.modifiers],sort_keys=True).encode())
    return h.hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
names=[o.name for o in bpy.data.collections['deck_project'].objects if not o.hide_render and o.type=='MESH']+['Central rock mound | continuous cross-column extrusions']
bpy.context.view_layer.update()
before={n:fingerprint(bpy.data.objects[n]) for n in names}
bpy.ops.wm.open_mainfile(filepath=str(TARGET))
bpy.context.view_layer.update()
after={n:fingerprint(bpy.data.objects[n]) for n in names}
missing=[n for n in names if n not in bpy.context.scene.objects]
changed=[n for n in names if before[n]!=after[n]]
report={'source':str(SOURCE),'output':str(TARGET),'output_sha256':hashlib.sha256(TARGET.read_bytes()).hexdigest(),'active_scene':bpy.context.scene.name,'protected_objects':len(names),'compared':'World transforms, mesh vertices and topology, face material indices, material node graphs and input values, and modifier settings','changed_objects':changed,'missing_from_active_scene':missing,'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'asset_source_sha256':hashlib.sha256((ROOT/'reference-cavern/cavern-portfolio.blend').read_bytes()).hexdigest(),'passed':not changed and not missing}
(TARGET.parent/(TARGET.stem+'-preservation.json')).write_text(json.dumps(report,indent=2))
print('CENTER_PRESERVATION',json.dumps(report),flush=True)
assert report['passed'],report
