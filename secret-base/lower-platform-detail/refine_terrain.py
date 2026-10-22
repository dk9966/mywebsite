import bpy,math,json
from pathlib import Path
from mathutils import Matrix,Vector
from bpy_extras.object_utils import world_to_camera_view
P=Path('/Users/danielku/mywebsite/secret-base/lower-platform-detail')
S=bpy.context.scene
FRAME=Matrix.Translation((21.299999237,0,0))@Matrix.Rotation(-math.atan2(12,19),4,'Z');INV=FRAME.inverted()
F=6.824491024; ROOF=F+2.03
terrain=bpy.data.objects['150 | continuous cave with oblique carved rooms']
with bpy.data.libraries.load(str(P/'before-detail.blend'),link=False) as (src,dst):
    dst.objects=[terrain.name]
source=dst.objects[0]
terrain.data=source.data.copy();terrain.data.name='Cave | connected reference workshop recess'
bpy.data.objects.remove(source,do_unlink=True)
back=[(5.05,-.10),(6.482775,-.089331),(8.141458,-.643934),(9.585233,-1.578686),(10.783675,-2.669809),(11.351686,-3.570891),(12.20,-4.35)]
def back_y(x):
    for a,b in zip(back,back[1:]):
        if a[0]<=x<=b[0]:return a[1]+(b[1]-a[1])*(x-a[0])/(b[0]-a[0])
    return back[0][1] if x<back[0][0] else back[-1][1]
mx=INV@terrain.matrix_world;imx=mx.inverted();changed=0
for v in terrain.data.vertices:
    p=mx@v.co;old=p.copy()
    if 5.05<p.x<12.4 and -11<p.y<1.4 and F-.48<p.z<ROOF+1.0:
        sc=world_to_camera_view(S,S.camera,FRAME@p)
        if p.y < -3.25 and .80<sc.x<1.055:
            # Foreground cave return stays in front of the room. Widen the
            # opening laterally instead of folding its surface behind the room.
            desired=.987+.004*math.sin(p.z*2.3+p.y*.8)
            x=(desired-.5)*1.5*sc.z
            wz=min(1,max(0,(p.z-(F-.48))/.32),max(0,(ROOF+1.0-p.z)/.42))
            p.x+=max(0,x-p.x)*wz
        elif p.y >= -3.25:
            target=back_y(p.x)+.42
            wz=min(1,max(0,(p.z-(F-.48))/.32),max(0,(ROOF+.9-p.z)/.5))
            wx=min(1,max(0,(p.x-5.05)/.45),max(0,(12.4-p.x)/.5))
            p.y+=max(0,target-p.y)*wz*wx
    if 5.4<p.x<9.4 and F-2.2<p.z<F-.72 and -4.1<p.y<.4:
        w=math.sin(math.pi*(p.z-(F-2.2))/1.48)**2
        w*=min(1,(p.x-5.4)/.6,(9.4-p.x)/.6)
        p.y-=max(0,p.y+4.13)*max(0,w)*.85
    if (p-old).length>1e-7:v.co=imx@p;changed+=1
terrain.data.update()
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath='/Users/danielku/mywebsite/secret-base/platform-controls/cave-platform-sliders.blend',compress=True)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'detailed-workshop.blend'),copy=True,compress=True)
result={'terrain_vertices_adjusted':changed}
