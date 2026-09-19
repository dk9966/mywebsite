"""Reusable 2K CC0 surface maps on explicit, metric UVs; no projection cards.
Dark Rock by Amal Kumar and Blue Metal Plate by Rob Tuytel / Poly Haven (CC0).
"""
import numpy as np
TEX=os.path.join(ROOT,'textures')
def texture(nt,asset,kind,data=False):
 path=os.path.join(TEX,asset,asset+'_'+kind+'_2k.jpg')
 im=bpy.data.images.load(path,check_existing=True);im.colorspace_settings.name='Non-Color' if data else 'sRGB';im.pack()
 n=nt.nodes.new('ShaderNodeTexImage');n.image=im;n.interpolation='Linear';n.extension='REPEAT';return n

processed={}
def processed_map(source,label,mode):
 key=(source.name,mode)
 if key in processed:return processed[key]
 w,h=source.size;buf=np.empty(w*h*4,dtype=np.float32);source.pixels.foreach_get(buf);arr=buf.reshape(-1,4);rgb=arr[:,:3].copy()
 if 'color' in mode:rgb=np.where(rgb<=.04045,rgb/12.92,((rgb+.055)/1.055)**2.4)
 if mode=='stone_color':
  gray=rgb@np.array([.2126,.7152,.0722],dtype=np.float32);gray=np.median(gray)+(gray-np.median(gray))*.45;arr[:,:3]=gray[:,None]*np.array([1.9,2.05,2.15],dtype=np.float32)
 elif mode=='metal_color':
  gray=rgb@np.array([.2126,.7152,.0722],dtype=np.float32);arr[:,:3]=(gray[:,None]*.75+rgb*.25)*np.array([1.12,1.05,.94],dtype=np.float32)
 elif mode=='stone_rough':arr[:,:3]=.65+rgb*.33
 elif mode=='metal_rough':arr[:,:3]=np.clip(.63+(rgb-np.median(rgb))*2.8,.40,.89)
 if 'color' in mode:arr[:,:3]=np.where(arr[:,:3]<=.0031308,arr[:,:3]*12.92,1.055*np.maximum(arr[:,:3],0)**(1/2.4)-.055)
 im=bpy.data.images.new(label,width=w,height=h,alpha=True);im.colorspace_settings.name='Non-Color' if 'rough' in mode else 'sRGB';im.pixels.foreach_set(arr.ravel());im.update();im.filepath_raw=os.path.join(TEX,label+'.png');im.file_format='PNG';im.save();im.pack();processed[key]=im;return im

def scan_rock(m):
 nt=m.node_tree;nt.nodes.clear();out=nt.nodes.new('ShaderNodeOutputMaterial');p=nt.nodes.new('ShaderNodeBsdfPrincipled');nt.links.new(p.outputs[0],out.inputs['Surface']);p.inputs['Metallic'].default_value=0;p.inputs['Specular IOR Level'].default_value=.32
 diff=texture(nt,'dark_rock','diff');diff.image=processed_map(diff.image,'cavern_stone_color_2k','stone_color');nt.links.new(diff.outputs['Color'],p.inputs['Base Color'])
 rough=texture(nt,'dark_rock','rough',True);rough.image=processed_map(rough.image,'cavern_stone_rough_2k','stone_rough');nt.links.new(rough.outputs['Color'],p.inputs['Roughness'])
 normal=texture(nt,'dark_rock','nor_gl',True);nm=nt.nodes.new('ShaderNodeNormalMap');nm.inputs['Strength'].default_value=.40;nt.links.new(normal.outputs['Color'],nm.inputs['Color']);nt.links.new(nm.outputs[0],p.inputs['Normal'])
 m['source']='https://polyhaven.com/a/dark_rock';m['license']='CC0';m['texture_scale_m']=3.5
scan_rock(rockmat);scan_rock(farrock)
height_image=bpy.data.images.load(os.path.join(TEX,'dark_rock','dark_rock_disp_2k.jpg'),check_existing=True);height_image.colorspace_settings.name='Non-Color';height_image.pack();H,W=height_image.size[1],height_image.size[0];pixels=np.empty(W*H*4,dtype=np.float32);height_image.pixels.foreach_get(pixels);pixels=pixels.reshape(H,W,4)[:,:,0]
for name in geology:
 ob=S.objects[name];me=ob.data;N=len(me.polygons[-1].vertices);levels=len(me.vertices)//N-1
 # Preserve a tiling seam behind the main viewing direction. Caps have planar UVs.
 r0=[me.vertices[i].co for i in range(N)];c=sum(r0,Vector())/N;radius=sum((v-c).xy.length for v in r0)/N
 repeats=max(1,round(2*pi*radius/3.5));uv=me.uv_layers.new(name='Surface UV • metric');offset=(sum(ord(c) for c in me.name)%97)/97
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
   v.co+=d*((value-.5)*.50)
 me.update()

for m in list(bpy.data.materials):
 if not any(k in m.name for k in ['STRUCTURE','FRAME','DECK','PROJECTS | neutral']):continue
 nt=m.node_tree;nt.nodes.clear();out=nt.nodes.new('ShaderNodeOutputMaterial');p=nt.nodes.new('ShaderNodeBsdfPrincipled');nt.links.new(p.outputs[0],out.inputs[0]);p.inputs['Metallic'].default_value=.78;p.inputs['Specular IOR Level'].default_value=.4
 diff=texture(nt,'blue_metal_plate','diff');diff.image=processed_map(diff.image,'cavern_metal_color_2k','metal_color');nt.links.new(diff.outputs[0],p.inputs['Base Color'])
 rough=texture(nt,'blue_metal_plate','rough',True);rough.image=processed_map(rough.image,'cavern_metal_rough_2k','metal_rough');nt.links.new(rough.outputs[0],p.inputs['Roughness'])
 normal=texture(nt,'blue_metal_plate','nor_gl',True);nm=nt.nodes.new('ShaderNodeNormalMap');nm.inputs['Strength'].default_value=.65;nt.links.new(normal.outputs[0],nm.inputs['Color']);nt.links.new(nm.outputs[0],p.inputs['Normal'])
 m['source']='https://polyhaven.com/a/blue_metal_plate';m['license']='CC0';m['texture_scale_m']=4.8
seen=set()
for ob in list(S.objects):
 if ob.type!='MESH' or ob.data.as_pointer() in seen:continue
 me=ob.data;seen.add(me.as_pointer())
 if not any(m and any(k in m.name for k in ['STRUCTURE','FRAME','DECK','PROJECTS | neutral']) for m in me.materials):continue
 uv=me.uv_layers.new(name='Surface UV • metric');offset=(sum(ord(c) for c in me.name)%97)/97
 for f in me.polygons:
  axis=max(range(3),key=lambda k:abs(f.normal[k]));ax=(0,1) if axis==2 else (0,2) if axis==1 else (1,2)
  for li in f.loop_indices:
   p=me.vertices[me.loops[li].vertex_index].co;uv.data[li].uv=(p[ax[0]]/4.8+offset,p[ax[1]]/4.8+offset*.37)
print('Applied metric UVs and packed CC0 2K material maps',flush=True)
