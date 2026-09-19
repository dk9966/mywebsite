"""Consolidate flat shared-mesh GLB nodes into EXT_mesh_gpu_instancing groups."""
import json,struct,os,collections
ROOT=os.path.dirname(os.path.abspath(__file__))
path=os.path.join(ROOT,'cavern-portfolio.glb')
raw=open(path,'rb').read();magic,version,length=struct.unpack_from('<4sII',raw)
assert magic==b'glTF' and version==2 and length==len(raw)
jlen,jtype=struct.unpack_from('<I4s',raw,12);doc=json.loads(raw[20:20+jlen]);off=20+jlen
blen,btype=struct.unpack_from('<I4s',raw,off);binary=bytearray(raw[off+8:off+8+blen])
assert not doc.get('animations') and not doc.get('skins')
assert len(doc['scenes'])==1 and all('children' not in n for n in doc['nodes'])
assert not any('matrix' in n for n in doc['nodes'])
groups=collections.defaultdict(list)
roots=set(doc['scenes'][0]['nodes'])
for i,n in enumerate(doc['nodes']):
 if i in roots and 'mesh' in n and 'extensions' not in n:groups[n['mesh']].append(i)
removed=set();new=[];instances=0;group_count=0
def accessor(values,kind):
 while len(binary)%4:binary.append(0)
 start=len(binary);width={'VEC3':3,'VEC4':4}[kind]
 flat=[v for row in values for v in row];binary.extend(struct.pack('<%df'%len(flat),*flat))
 view=len(doc.setdefault('bufferViews',[]));doc['bufferViews'].append({'buffer':0,'byteOffset':start,'byteLength':len(values)*width*4,'target':34962})
 idx=len(doc.setdefault('accessors',[]));a={'bufferView':view,'componentType':5126,'count':len(values),'type':kind}
 doc['accessors'].append(a);return idx
for mesh,ids in groups.items():
 if len(ids)<8:continue
 source=[doc['nodes'][i] for i in ids]
 attrs={'TRANSLATION':accessor([n.get('translation',[0,0,0]) for n in source],'VEC3'),'ROTATION':accessor([n.get('rotation',[0,0,0,1]) for n in source],'VEC4'),'SCALE':accessor([n.get('scale',[1,1,1]) for n in source],'VEC3')}
 new.append({'name':'INSTANCES | '+source[0].get('name','module'),'mesh':mesh,'extensions':{'EXT_mesh_gpu_instancing':{'attributes':attrs}},'extras':{'instanceNames':[n.get('name','') for n in source]}})
 removed.update(ids);instances+=len(ids);group_count+=1
retained=[n for i,n in enumerate(doc['nodes']) if i not in removed];doc['nodes']=retained+new;doc['scenes'][0]['nodes']=list(range(len(doc['nodes'])))
doc.setdefault('extensionsUsed',[]).append('EXT_mesh_gpu_instancing');doc.setdefault('extensionsRequired',[]).append('EXT_mesh_gpu_instancing')
doc['buffers'][0]['byteLength']=len(binary)
encoded=json.dumps(doc,separators=(',',':'),ensure_ascii=False).encode('utf8')
encoded+=b' '*((-len(encoded))%4);binary+=b'\0'*((-len(binary))%4)
result=struct.pack('<4sII',b'glTF',2,12+8+len(encoded)+8+len(binary))+struct.pack('<I4s',len(encoded),b'JSON')+encoded+struct.pack('<I4s',len(binary),b'BIN\0')+binary
open(path,'wb').write(result)
manifest_path=os.path.join(ROOT,'runtime-manifest.json');manifest=json.load(open(manifest_path))
manifest.update({'glb_bytes':len(result),'gltf_nodes':len(doc['nodes']),'gltf_meshes':len(doc['meshes']),'gpu_instance_groups':group_count,'gpu_instances':instances,'gltf_materials':len(doc.get('materials',[])),'gltf_extensions':doc['extensionsUsed']})
manifest['runtime_notes'].append('Use GLTFLoader with a Draco decoder; EXT_mesh_gpu_instancing retains shared repeated modules. Instance names are preserved in node extras.')
json.dump(manifest,open(manifest_path,'w'),indent=2)
print(json.dumps({k:manifest[k] for k in ['glb_bytes','gltf_nodes','gltf_meshes','gpu_instance_groups','gpu_instances','gltf_extensions']},indent=2))
