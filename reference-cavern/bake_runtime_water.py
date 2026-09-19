"""Bake portable water base color, tangent normal, and roughness for the export copy.
Call from finalize.py after editable scene is saved. No original shader is overwritten on disk.
"""
waterob=next(o for o in S.objects if o.name.startswith('Water | rippled'))
me=waterob.data;uv=me.uv_layers.new(name='Water runtime UV')
xs=[v.co.x for v in me.vertices];ys=[v.co.y for v in me.vertices];xmin,xmax=min(xs),max(xs);ymin,ymax=min(ys),max(ys)
for f in me.polygons:
 for li in f.loop_indices:
  q=me.vertices[me.loops[li].vertex_index].co;uv.data[li].uv=((q.x-xmin)/(xmax-xmin),(q.y-ymin)/(ymax-ymin))
bpy.ops.object.select_all(action='DESELECT');waterob.select_set(True);bpy.context.view_layer.objects.active=waterob
material=me.materials[0];nt=material.node_tree;p=nt.nodes.get('Principled BSDF');maps={};S.cycles.samples=8
for tag,kind,color in [('color','DIFFUSE',True),('normal','NORMAL',False),('rough','ROUGHNESS',False)]:
 im=bpy.data.images.new('Water runtime '+tag,width=2048,height=2048,alpha=False);im.colorspace_settings.name='sRGB' if color else 'Non-Color'
 node=nt.nodes.new('ShaderNodeTexImage');node.image=im;nt.nodes.active=node
 kwargs={'type':kind,'margin':4,'use_clear':True}
 if kind=='DIFFUSE':kwargs['pass_filter']={'COLOR'}
 if kind=='NORMAL':kwargs['normal_space']='TANGENT'
 bpy.ops.object.bake(**kwargs)
 im.filepath_raw=os.path.join(ROOT,'textures','water_runtime_'+tag+'.png');im.file_format='PNG';im.save();im.pack();maps[tag]=im
 nt.nodes.remove(node)
# Standard PBR nodes preserve the static look in glTF; animate UVs/normal blending in runtime.
m=bpy.data.materials.new('WATER | portable baked surface');nt=m.node_tree;p=nt.nodes.get('Principled BSDF');p.inputs['Metallic'].default_value=0;p.inputs['IOR'].default_value=1.333;p.inputs['Specular IOR Level'].default_value=.28
for tag,socket in [('color','Base Color'),('rough','Roughness')]:
 n=nt.nodes.new('ShaderNodeTexImage');n.image=maps[tag];nt.links.new(n.outputs['Color'],p.inputs[socket])
n=nt.nodes.new('ShaderNodeTexImage');n.image=maps['normal'];nm=nt.nodes.new('ShaderNodeNormalMap');nt.links.new(n.outputs['Color'],nm.inputs['Color']);nt.links.new(nm.outputs['Normal'],p.inputs['Normal']);me.materials.clear();me.materials.append(m)
print('Baked portable water PBR maps',flush=True)
