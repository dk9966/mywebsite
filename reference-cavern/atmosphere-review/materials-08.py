"""Reusable 2K CC0 surface maps on explicit, metric UVs; no projection cards.
Rock 06 and Blue Metal Plate by Rob Tuytel / Poly Haven (CC0).
"""
import numpy as np
TEX=os.path.join(ROOT,'textures')
def texture(nt,asset,kind,data=False):
 path=os.path.join(TEX,asset,asset+'_'+kind+'_2k.jpg')
 im=bpy.data.images.load(path,check_existing=True);im.colorspace_settings.name='Non-Color' if data else 'sRGB';im.pack()
 n=nt.nodes.new('ShaderNodeTexImage');n.image=im;n.interpolation='Linear';n.extension='REPEAT';return n

def scan_rock(m):
 nt=m.node_tree;nt.nodes.clear();out=nt.nodes.new('ShaderNodeOutputMaterial');p=nt.nodes.new('ShaderNodeBsdfPrincipled');nt.links.new(p.outputs[0],out.inputs['Surface']);p.inputs['Metallic'].default_value=0;p.inputs['Specular IOR Level'].default_value=.32
 diff=texture(nt,'rock_06','diff');gray=nt.nodes.new('ShaderNodeRGBToBW');nt.links.new(diff.outputs['Color'],gray.inputs[0]);tint=nt.nodes.new('ShaderNodeMixRGB');tint.blend_type='MULTIPLY';tint.inputs[0].default_value=1;nt.links.new(gray.outputs[0],tint.inputs[1]);tint.inputs[2].default_value=(.25,.28,.30,1);nt.links.new(tint.outputs[0],p.inputs['Base Color'])
 rough=texture(nt,'rock_06','rough',True);nt.links.new(rough.outputs['Color'],p.inputs['Roughness'])
 normal=texture(nt,'rock_06','nor_gl',True);nm=nt.nodes.new('ShaderNodeNormalMap');nm.inputs['Strength'].default_value=.85;nt.links.new(normal.outputs['Color'],nm.inputs['Color'])
 disp=texture(nt,'rock_06','disp',True);b=nt.nodes.new('ShaderNodeBump');b.inputs['Distance'].default_value=.14;b.inputs['Strength'].default_value=.32;nt.links.new(disp.outputs['Color'],b.inputs['Height']);nt.links.new(nm.outputs[0],b.inputs['Normal']);nt.links.new(b.outputs[0],p.inputs['Normal'])
 m['source']='https://polyhaven.com/a/rock_06';m['license']='CC0';m['texture_scale_m']=3.5
scan_rock(rockmat);scan_rock(farrock)
height_image=bpy.data.images.get('rock_06_disp_2k.jpg');H,W=height_image.size[1],height_image.size[0];pixels=np.empty(W*H*4,dtype=np.float32);height_image.pixels.foreach_get(pixels);pixels=pixels.reshape(H,W,4)[:,:,0]
for name in geology:
 ob=S.objects[name];me=ob.data;N=len(me.polygons[-1].vertices);levels=len(me.vertices)//N-1
 # Preserve a tiling seam behind the main viewing direction. Caps have planar UVs.
 r0=[me.vertices[i].co for i in range(N)];c=sum(r0,Vector())/N;radius=sum((v-c).xy.length for v in r0)/N
 repeats=max(1,round(2*pi*radius/3.5));uv=me.uv_layers.new(name='Surface UV • metric')
 for f in me.polygons:
  for li in f.loop_indices:
   vi=me.loops[li].vertex_index;v=me.vertices[vi].co;i=vi%N
   if f.index<levels*N:
    u=(i/N)*repeats
    if f.index%N==N-1 and i==0:u=repeats
    uv.data[li].uv=(u,(v.z+.12*v.x)/3.5)
   else:uv.data[li].uv=(v.x/3.5,v.y/3.5)
 # A small amount of measured relief is real geometry as well as a normal map.
 for j in range(levels+1):
  ring=[me.vertices[j*N+i].co.copy() for i in range(N)];center=sum(ring,Vector())/N
  for i in range(N):
   v=me.vertices[j*N+i];d=v.co-center;d.z=0
   if d.length<.12:continue
   d.normalize();u=(i/N)*repeats;vv=(v.co.z+.12*v.co.x)/3.5;value=float(pixels[int((vv%1)*H)%H,int((u%1)*W)%W])
   v.co+=d*((value-.5)*.27)
 me.update()

for m in list(bpy.data.materials):
 if not any(k in m.name for k in ['STRUCTURE','FRAME','DECK','PROJECTS | neutral']):continue
 nt=m.node_tree;nt.nodes.clear();out=nt.nodes.new('ShaderNodeOutputMaterial');p=nt.nodes.new('ShaderNodeBsdfPrincipled');nt.links.new(p.outputs[0],out.inputs[0]);p.inputs['Metallic'].default_value=.64;p.inputs['Specular IOR Level'].default_value=.4
 diff=texture(nt,'blue_metal_plate','diff');hs=nt.nodes.new('ShaderNodeHueSaturation');hs.inputs['Saturation'].default_value=.25;hs.inputs['Value'].default_value=.8;nt.links.new(diff.outputs[0],hs.inputs['Color']);nt.links.new(hs.outputs[0],p.inputs['Base Color'])
 rough=texture(nt,'blue_metal_plate','rough',True);nt.links.new(rough.outputs[0],p.inputs['Roughness'])
 normal=texture(nt,'blue_metal_plate','nor_gl',True);nm=nt.nodes.new('ShaderNodeNormalMap');nm.inputs['Strength'].default_value=.45;nt.links.new(normal.outputs[0],nm.inputs['Color']);nt.links.new(nm.outputs[0],p.inputs['Normal'])
 m['source']='https://polyhaven.com/a/blue_metal_plate';m['license']='CC0';m['texture_scale_m']=2.5
seen=set()
for ob in list(S.objects):
 if ob.type!='MESH' or ob.data.as_pointer() in seen:continue
 me=ob.data;seen.add(me.as_pointer())
 if not any(m and any(k in m.name for k in ['STRUCTURE','FRAME','DECK','PROJECTS | neutral']) for m in me.materials):continue
 uv=me.uv_layers.new(name='Surface UV • metric')
 for f in me.polygons:
  axis=max(range(3),key=lambda k:abs(f.normal[k]));ax=(0,1) if axis==2 else (0,2) if axis==1 else (1,2)
  for li in f.loop_indices:
   p=me.vertices[me.loops[li].vertex_index].co;uv.data[li].uv=(p[ax[0]]/2.5,p[ax[1]]/2.5)
print('Applied metric UVs and packed CC0 2K material maps',flush=True)
