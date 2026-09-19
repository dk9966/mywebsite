"""Bake wear around the existing radial panel seams without changing their geometry.
Compact standard PBR textures carry the treatment to glTF.
"""
def pixels_of(im):
 w,h=im.size;a=np.empty(w*h*4,np.float32);im.pixels.foreach_get(a);return a.reshape(h,w,4)
def store_surface_image(label,data,is_color):
 h,w=data.shape[:2];a=np.ones((h,w,4),np.float32);a[:,:,:3]=data
 if is_color:a[:,:,:3]=np.where(a[:,:,:3]<=.0031308,a[:,:,:3]*12.92,1.055*np.maximum(a[:,:,:3],0)**(1/2.4)-.055)
 im=bpy.data.images.new(label,width=w,height=h,alpha=True);im.colorspace_settings.name='sRGB' if is_color else 'Non-Color';im.pixels.foreach_set(a.ravel());im.filepath_raw=os.path.join(TEX,label+'.png');im.file_format='PNG';im.save();im.pack();return im
source_color=pixels_of(bpy.data.images['cavern_metal_color_2k'])[:,:,:3];source_color=np.where(source_color<=.04045,source_color/12.92,((source_color+.055)/1.055)**2.4)
source_rough=pixels_of(bpy.data.images['cavern_metal_rough_2k'])[:,:,:3]
source_normal=pixels_of(next(i for i in bpy.data.images if 'blue_metal_plate_nor_gl' in i.name))[:,:,:3]
for number,name in enumerate(['PROJECTS | floor','ABOUT ME | floor']):
 ob=S.objects[name];me=ob.data;radius=max(abs(v.co.x) for v in me.vertices);R=radius+.13;res=1024
 yy,xx=np.mgrid[0:res,0:res].astype(np.float32);x=((xx+.5)/res-.5)*radius*2;y=((yy+.5)/res-.5)*radius*2
 u=(x/4.8+.27+number*.41)%1;v=(y/4.8+.18+number*.13)%1;H,W=source_color.shape[:2];ix=(u*W).astype(int)%W;iy=(v*H).astype(int)%H
 base=source_color[iy,ix].copy();rough=source_rough[iy,ix].copy();normal=source_normal[iy,ix].copy()
 r=np.sqrt(x*x+y*y);theta=np.arctan2(y,x);sector=np.floor((theta+pi)*24/(2*pi))
 angular_dist=np.abs(np.sin(theta*12))*r/12;angular_dist=np.where(r>R*.50,angular_dist,99)
 ring_dist=np.minimum.reduce([np.abs(r-a*R) for a in [.49,.45,.22]]+[np.abs(r-(R-.4)),np.abs(r-(R-.63))])
 dist=np.minimum(angular_dist,ring_dist)
 irregular=np.clip(.50+.24*np.sin(x*7+y*2)+.23*np.sin(x*3-y*11)+.14*np.sin(x*31+y*9),0,1)
 grime=np.exp(-(dist/.032)**2)*(.5+.5*irregular)
 worn=np.exp(-((dist-.06)/.044)**2)*np.clip((irregular-.30)*1.5,0,1)*(np.sin(sector*13.27+number)>.15)
 # Slightly different service histories among panels, without a painted checker pattern.
 panel=.035*np.sin(sector*7.91+number)
 base*=1+panel[:,:,None]-.42*grime[:,:,None]+.55*worn[:,:,None]
 base+=worn[:,:,None]*np.array([.015,.016,.016])
 rough=np.clip(rough+.16*grime[:,:,None]-.20*worn[:,:,None]+panel[:,:,None],.35,.9)
 color_im=store_surface_image('deck_'+str(number)+'_worn_color',base,True);rough_im=store_surface_image('deck_'+str(number)+'_worn_rough',rough,False);normal_im=store_surface_image('deck_'+str(number)+'_worn_normal',normal,False)
 m=me.materials[0].copy();m.name='DECK | seam wear '+name;me.materials.clear();me.materials.append(m);nt=m.node_tree;p=nt.nodes.get('Principled BSDF')
 for n in nt.nodes:
  if n.type!='TEX_IMAGE' or not n.image:continue
  if 'color' in n.image.name:n.image=color_im
  elif 'rough' in n.image.name:n.image=rough_im
  elif 'nor_gl' in n.image.name:n.image=normal_im
 uv=me.uv_layers.active
 for f in me.polygons:
  for li in f.loop_indices:
   q=me.vertices[me.loops[li].vertex_index].co;uv.data[li].uv=(.5+q.x/(radius*2),.5+q.y/(radius*2))
 print('Baked existing deck seam wear',name,flush=True)
