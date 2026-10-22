"""Camera-fit the lower workshop while preserving source meshes and slider rig."""
import bpy, math, json
import numpy as np
from pathlib import Path
from mathutils import Vector, Matrix
from bpy_extras.object_utils import world_to_camera_view
P=Path('/Users/danielku/mywebsite/secret-base/lower-reference-alignment')
S=bpy.context.scene; CAM=S.camera
FRAME=Matrix.Translation((21.299999237,0,0))@Matrix.Rotation(-math.atan2(12,19),4,'Z')
INV=FRAME.inverted();F=6.824491024;H=2.03
W=1697; IH=927; RH=W*S.render.resolution_y/S.render.resolution_x; PAD=(RH-IH)/2
# Reference pixels are the FIT background image, not the padded render frame.
proj=CAM.calc_matrix_camera(bpy.context.evaluated_depsgraph_get(),x=S.render.resolution_x,y=S.render.resolution_y)
vp=proj@CAM.matrix_world.inverted();ivp=vp.inverted()
def ray(uv):
 x=2*uv[0]/W-1;y=1-2*(uv[1]+PAD)/RH
 p=ivp@Vector((x,y,-1,1));p=p.xyz/p.w
 return CAM.matrix_world.translation.copy(),(p-CAM.matrix_world.translation).normalized()
def at_z(uv,z):
 a,d=ray(uv);return a+d*((z-a.z)/d.z)
def local_at(uv,z=F):return INV@at_z(uv,z)
def uv(p):
 p=world_to_camera_view(S,CAM,FRAME@Vector(p));return np.array([p.x*W,(1-p.y)*RH-PAD])
oldfoot=np.array([(4.621191,-5.011547),(5.871193,-6.261546),(8.871193,-6.261546),(10.121193,-5.011547),(11.351686,-3.570891),(10.783675,-2.669809),(9.585233,-1.578686),(8.141458,-.643934),(6.482775,-.089331),(5.52,-.08),(4.621191,-2.011547)])
targetpix=[(1218,668),(1335,699),(1593,699),(1645,664),(1656,588),(1590,565),(1458,530),(1340,516),(1244,515),(1220,515),(1150,559)]
newfoot=np.array([local_at(p)[:2] for p in targetpix])
# Smooth planar deformation, with bridge attachment held in place.
anchor=np.array([(2,-3),(2,-1),(3,-2)])
base=np.vstack([oldfoot,anchor]);dst=np.vstack([newfoot,anchor])
def phi(r):return r*r*np.log(np.maximum(r,1e-9))
r=np.linalg.norm(base[:,None,:]-base[None,:,:],axis=2);n=len(base)
A=np.block([[phi(r),np.ones((n,1)),base],[np.ones((1,n)),np.zeros((1,3))],[base.T,np.zeros((2,3))]])
coef=np.linalg.solve(A,np.vstack([dst-base,np.zeros((3,2))]))
def warp(p):
 p=np.asarray(p);q=np.concatenate([phi(np.linalg.norm(base-p,axis=1)),[1],p])
 return p+q@coef
# Piecewise wall fit using measured floor and lintel corners.
oldwall=np.array([(5.52,-.08),(6.482775,-.089331),(8.141458,-.643934),(9.585233,-1.578686),(10.783675,-2.669809),(11.351686,-3.570891)])
bottompix=[(1220,515),(1244,515),(1340,516),(1458,530),(1590,565),(1656,588)]
toppix=[(1237,394),(1250,393),(1357,399),(1486,426),(1615,469),(1670,500)]
newbottom=np.array([local_at(p,F) for p in bottompix]);newtop=np.array([local_at(p,F+H) for p in toppix])
def wallwarp(p):
 x,y,z=p;j=max(0,min(len(oldwall)-2,int(np.searchsorted(oldwall[:,0],x)-1)))
 t=(x-oldwall[j,0])/(oldwall[j+1,0]-oldwall[j,0]);h=(z-F)/H
 ob=oldwall[j]*(1-t)+oldwall[j+1]*t
 nb=newbottom[j]*(1-t)+newbottom[j+1]*t;nt=newtop[j]*(1-t)+newtop[j+1]*t
 q=nb*(1-h)+nt*h
 # Retain actual depth of beams, roof overhangs and panel layers.
 q[1]+=y-(ob[1]+.075*h)
 return Vector(q)
# Retain editable before-fit source data for further passes.
changed=[]
def begin(o):
 key='reference_fit_source_mesh'
 if key not in o:
  o.data.use_fake_user=True;o[key]=o.data.name;o.data=o.data.copy();o.data.name=o.name+' | reference fit'
 else:
  src=bpy.data.meshes[o[key]]
  for a,b in zip(o.data.vertices,src.vertices):a.co=b.co
 return INV@o.matrix_world

def finish(o):o.data.update();changed.append(o.name)
for col in [bpy.data.collections['156 | Lower workshop walls and canopy']]:
 for o in col.objects:
  if o.type!='MESH':continue
  mx=begin(o);back=mx.inverted()
  for v in o.data.vertices:v.co=back@wallwarp(mx@v.co)
  finish(o)
# Lower slab and underframe: plan fit only; a later pass tunes the visible V braces.
for o in [bpy.data.objects['Lower | plain octagon']]+list(bpy.data.collections['157 | Lower deck and cliff supports'].objects):
 if o.type!='MESH':continue
 mx=begin(o);back=mx.inverted()
 isring=any(s in o.name for s in ['circular','registration circle','center service plate','radial plate joint'])
 for v in o.data.vertices:
  p=mx@v.co
  if isring:
   dx=p.x-7.52;dy=p.y+3.52;r=math.hypot(dx,dy)/2.092;theta=math.atan2(dy,dx)
   # Screen-space ellipse calibrated to the reference service track.
   pt=(1425+183*r*math.cos(theta),604+13*r*math.cos(theta)+56*r*math.sin(theta))
   q=local_at(pt,p.z)
  else:
   xy=warp(p[:2]);q=Vector((xy[0],xy[1],p.z))
  v.co=back@q
 finish(o)
# Continuous rail/curb meshes include the bridge: zero out the warp at its main end.
for o in bpy.data.collections['158 | Connected bridge and railings'].objects:
 if o.type!='MESH' or 'main rim' in o.name:continue
 mx=begin(o);back=mx.inverted()
 for v in o.data.vertices:
  p=mx@v.co;xy=warp(p[:2]);w=min(1,max(0,(p.x-3.6)/(4.621191-3.6)))
  v.co=back@Vector((p.x+(xy[0]-p.x)*w,p.y+(xy[1]-p.y)*w,p.z))
 finish(o)
# Leave camera, other rooms, original materials and controls intact.
S['lower_platform_reference']='images/batcave-empty-platform-v3.png; measured camera alignment'
CAM.data.background_images[0].alpha=.5
for a in bpy.context.screen.areas:
 if a.type=='VIEW_3D':a.spaces.active.overlay.show_overlays=False;a.tag_redraw()
bpy.context.view_layer.update()
P.joinpath('fit-measurements.json').write_text(json.dumps({'floor_reference_pixels':targetpix,'wall_bottom_pixels':bottompix,'wall_top_pixels':toppix,'objects_adjusted':len(changed)},indent=2))
result={'adjusted':len(changed),'reference_points':len(targetpix)+len(toppix)+len(bottompix)}
