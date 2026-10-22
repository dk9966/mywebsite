"""Final support silhouette, connected handrail miters and practical light."""
import bpy,bmesh,math,json
from pathlib import Path
from mathutils import Vector,Matrix
P=Path('/Users/danielku/mywebsite/secret-base/lower-platform-detail')
S=bpy.context.scene
FRAME=Matrix.Translation((21.299999237,0,0))@Matrix.Rotation(-math.atan2(12,19),4,'Z')
INV=FRAME.inverted();F=6.824491024
C=bpy.data.collections['157 | Lower deck and cliff supports']
lower=bpy.data.objects['Lower | plain octagon']
steel=bpy.data.materials['Metal | dark structural steel'];alloy=bpy.data.materials['Metal | outer walkway alloy']
def beam(name,a,b,width,depth,mat):
    a,b=Vector(a),Vector(b);axis=(b-a).normalized()
    u=axis.cross(Vector((0,0,1)) if abs(axis.z)<.95 else Vector((0,1,0))).normalized()*width/2
    v=axis.cross(u).normalized()*depth/2
    verts=[tuple(p+su*u+sv*v) for p in (a,b) for su,sv in [(-1,-1),(1,-1),(1,1),(-1,1)]]
    me=bpy.data.meshes.new(name);me.from_pydata(verts,[],[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]);me.materials.append(mat);me.update()
    ob=bpy.data.objects.new(name,me);C.objects.link(ob);ob.matrix_world=FRAME
    bevel=ob.modifiers.new('Fabricated bevel','BEVEL');bevel.width=.006;bevel.segments=2
    ob.modifiers.new('Fabricated normals','WEIGHTED_NORMAL')
    mw=ob.matrix_world.copy();ob.parent=lower;ob.matrix_world=mw
    return ob

# Front V trusses stand below the perimeter instead of disappearing behind it.
for i,(xa,xb) in enumerate([(5.87,7.38),(7.38,8.87)]):
    mid=(xa+xb)/2
    foot=Vector((mid,-5.55,F-1.72))
    for x in (xa,xb):
        beam('Lower | exposed front V truss',(x,-6.18,F-.29),foot,.095,.14,steel)
        beam('Lower | front load transfer upright',(x,-6.18,F-.28),(x,-6.18,F-.77),.075,.105,steel)
    beam('Lower | V truss anchor shoe',foot-Vector((.1,0,0)),foot+Vector((.1,0,0)),.19,.10,alloy)
    beam('Lower | V foundation rock tie',foot,(mid,-3.75,F-1.72),.105,.14,steel)
    beam('Lower | V foundation rear bearing',(mid,-3.75,F-1.80),(mid,-3.75,F-1.62),.27,.24,alloy)

# Seat the visible front feet in the existing cliff. This deforms only a
# narrow height band of that same mesh; no detached rock chunks are added.
terrain=bpy.data.objects['150 | continuous cave with oblique carved rooms']
mx=INV@terrain.matrix_world;ix=mx.inverted();modified=0
for v in terrain.data.vertices:
    p=mx@v.co
    if 5.95<p.x<8.92 and F-2.12<p.z<F-1.17 and -5.7<p.y<-.6:
        w=min(1,max(0,(p.x-5.95)/.45),max(0,(8.92-p.x)/.45))
        w*=max(0,1-abs(p.z-(F-1.72))/.5)
        p.y-=max(0,p.y+5.43)*w
        v.co=ix@p;modified+=1
terrain.data.update()

# Finish the boolean exactly at the mitered bridge rail centreline.
d=Vector((1,-.625,0)).normalized();n=Vector((-d.y,d.x,0))
cutter=bpy.data.objects['Bridge | editable gate aperture']
for v in cutter.data.vertices:
    off=v.co.dot(n)
    v.co+=n*(math.copysign(.668,off)-off)
cutter.data.update()

def area(name,p,target,energy,size):
    data=bpy.data.lights.new(name,'AREA');data.energy=energy;data.color=(.63,.77,1);data.shape='DISK';data.size=size
    ob=bpy.data.objects.new(name,data);C.objects.link(ob);ob.location=FRAME@Vector(p)
    ob.rotation_euler=(FRAME.to_3x3()@(Vector(target)-Vector(p))).to_track_quat('-Z','Y').to_euler()
area('Lower | soft room bounce',(7.9,-5.4,F+2.1),(8.1,-.8,F+.8),48,3.2)
area('Lower | faint cliff reflected fill',(6.4,-8.4,F-.25),(7.3,-5.4,F-1.0),75,4.0)
bpy.data.objects['Lower | canopy downlight'].data.energy=70
bpy.data.objects['Lower | canopy downlight'].data.size=1.9

# Dedicated review camera preserves the user's main camera and its framing.
camdata=S.camera.data.copy();camdata.name='Lower | architecture review lens'
cam=bpy.data.objects.new('Lower | architecture detail camera',camdata);C.objects.link(cam)
target=Vector((7.3,-2.9,7.0))
ray=Vector((0,.9424,-.334467))
cam.location=FRAME@(target-ray*12.8)
cam.rotation_euler=S.camera.rotation_euler
cam.data.lens=32;cam.data.shift_y=0;cam.data.show_background_images=False

bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath='/Users/danielku/mywebsite/secret-base/platform-controls/cave-platform-sliders.blend',compress=True)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'detailed-workshop.blend'),copy=True,compress=True)
result={'saved':bpy.data.filepath,'foundation_vertices':modified,'front_V_trusses':2}
