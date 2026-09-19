exec(compile(open('/Users/danielku/mywebsite/secret-base/refine_wired_depth.py').read().split('# Remove unsupported')[0],'helpers','exec'))
random.seed(1394)
# Split the broad geological planes with irregular fracture ridges.
for o in bpy.data.objects:
 if o.type!='MESH' or 'bedrock foundation island' not in o.name:continue
 bm=bmesh.new();bm.from_mesh(o.data)
 original=set(bm.verts)
 bmesh.ops.subdivide_edges(bm,edges=list(bm.edges),cuts=1,use_grid_fill=True)
 bm.normal_update()
 for v in bm.verts:
  if v not in original and v.co.z<-.6:v.co+=v.normal*random.uniform(-.18,.16)
 bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free();o.data.update()
 for f in o.data.polygons:f.material_index=random.choice([2,3,4,4,5]);f.use_smooth=False
# Place fog behind the near foundations; use separate pockets through the channels.
old=bpy.data.objects['Wired | low curling chasm mist'];old.hide_render=True;old.hide_set(True)
for j,(xyz,sc) in enumerate([((-10,-7,-5),(7,7,7)),((.6,-8,-7),(7,9,8)),((5,-4,-10),(6,7,8)),((10,-8,-5),(5,8,7))]):
 o=bpy.data.objects.new('Wired | channel mist pocket %d'%j,old.data.copy());col.objects.link(o);o.location=p(*xyz);o.rotation_euler=cam.rotation_euler;o.scale=sc
 m=old.data.materials[0].copy();o.data.materials.clear();o.data.materials.append(m)
 for n in m.node_tree.nodes:
  if n.type=='PRINCIPLED_VOLUME':
   inp=n.inputs['Density'];src=inp.links[0].from_socket;mul=m.node_tree.nodes.new('ShaderNodeMath');mul.operation='MULTIPLY';mul.inputs[1].default_value=.55;m.node_tree.links.new(src,mul.inputs[0]);m.node_tree.links.new(mul.outputs[0],inp)
# A ragged layered opening instead of uninterrupted blue cliff planes.
for i,(x,y,d,w,h) in enumerate([(-1.3,5,-20,1.4,2.7),(2.3,6.2,-21,1.5,3),(0,3.2,-22,1.6,1.8),(-2.7,7.4,-22,1.2,2.1),(1,8.3,-25,.8,1.8)]):
 crag('Wired | broken opening ridge',(x,y,d),(w,h,1.5),2)
# Near buttresses have dark neutral rock; blue light remains in the recesses.
for o in col.objects:
 if o.type=='LIGHT' and any(k in o.name for k in ['abyss light','lower chasm grazing']):o.data.energy*=.7
# Coherent stone texture, barely visible at render distance, enriches large planes.
for m in rocks:
 nt=m.node_tree;bs=nt.nodes.get('Principled BSDF');tex=nt.nodes.new('ShaderNodeTexNoise');tex.inputs['Scale'].default_value=5;tex.inputs['Detail'].default_value=2;tex.inputs['Roughness'].default_value=.7
 bump=nt.nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.11;bump.inputs['Distance'].default_value=.035;nt.links.new(tex.outputs['Fac'],bump.inputs['Height']);nt.links.new(bump.outputs[0],bs.inputs['Normal'])
# Fine broken stone at the front of the large buttresses.
for o in list(bpy.data.objects):
 if o.type!='MESH' or 'bedrock foundation island' not in o.name:continue
 polys=[f for f in o.data.polygons if f.center.z<-.4 and f.center.z>-8 and f.normal.dot(D)>.15]
 for f in random.sample(polys,min(40,len(polys))):
  pos=o.matrix_world@f.center;v=pos-C;size=random.uniform(.12,.3)
  crag('Wired | embedded buttress splinter',(v.dot(R),v.dot(U),v.dot(D)),(size,size*random.uniform(1.2,2.5),size*.8),1)
# Slightly brighter neutral grazing accent for metal surface readability.
o=area('Wired | station gray grazing',(0,5,12),(0,0,0),180,8,(.6,.67,.76));o.data.volume_factor=0;o.data.specular_factor=.15
s.render.filepath='/Users/danielku/mywebsite/secret-base/wired-review/iteration-5.png'
bpy.ops.wm.save_as_mainfile(filepath='/Users/danielku/mywebsite/secret-base/base.blend')
