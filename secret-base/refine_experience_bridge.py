"""Second review pass: expose staggered paving and add abutment fasteners."""
import bpy, math
from mathutils import Vector

# Load only geometry helpers; do not repeat the one-shot island resize.
source=open('/Users/danielku/mywebsite/secret-base/build_experience_bridge.py').read()
CX=21.299999237060547;F=6.871178627
spec=bpy.context.scene['experience_bridge_specs'];YP=spec['project_end_y'];YE=spec['experience_end_y'];L=YP-YE;GRADE=.5/L
project=bpy.data.objects['island_pillar_project'];bc=bpy.data.collections['bridge_project_experience']
import bmesh
exec(source[source.index('def mesh('):source.index('# Restore continuous Project rim')])

# Slab top below finished paving, avoiding coplanar surfaces and hidden seams.
slab=bpy.data.objects['bridge_structural_deck']
slab.location.z-=.038
for ob in list(bpy.data.objects):
    if ob.name.startswith('bridge_paver_'):bpy.data.objects.remove(ob,do_unlink=True)
base=bpy.data.materials['stationFloorSatin']
for name,factor in [('bridgePavingSlate',.94),('bridgePavingLight',1.035)]:
    mat=bpy.data.materials.get(name) or base.copy();mat.name=name
    bsdf=mat.node_tree.nodes.get('Principled BSDF')
    color=bsdf.inputs['Base Color'].default_value
    bsdf.inputs['Base Color'].default_value=tuple(c*factor for c in color[:3])+(1,)
N=18; step=L/N
for col in range(2):
    offset=step*.5*col
    for i in range(-1,N+1):
        lo=max(YE,YE+i*step+offset);hi=min(YP,YE+(i+1)*step+offset)
        if hi-lo<.015:continue
        mat='bridgePavingLight' if (i+col)%4==0 else 'bridgePavingSlate' if (i-col)%3==0 else 'stationFloorSatin'
        box('bridge_paver_%s_%02d'%(col,i+1),(CX+(-1 if col==0 else 1)*.177,(lo+hi)/2,F-.016),(.344,hi-lo-.008,.032),mat,bevel=.004,slope=True)
        if i%3==0:
            x=CX+(-1 if col==0 else 1)*.313
            for y in (lo+.035,hi-.035):box('bridge_paver_pin_%s_%s_%s'%(col,i,y),(x,y,F-.002),(.013,.013,.006),'metalDark',bevel=.002,slope=True)

# Triangular steel connection plates follow the knee/support junctions.
for tag,y,f,d in [('project',YP,F,-1),('experience',YE,F-.5,1)]:
    for side in (-1,1):
        x=CX+side*.4225
        vertices=[]
        outline=[(y+d*.23,f-.14),(y+d*.62,f-.14),(y+d*.23,f-.40)]
        for xx in (x+side*.071,x+side*.09):vertices.extend([(xx,yy,zz) for yy,zz in outline])
        mesh('bridge_connection_plate_'+tag+'_'+str(side),vertices,[(0,2,1),(3,4,5),(0,1,4,3),(1,2,5,4),(2,0,3,5)],'metalDark',bevel=.003)
        for i,(yy,zz) in enumerate([(y+d*.29,f-.19),(y+d*.50,f-.19),(y+d*.29,f-.32)]):
            box('bridge_connection_bolt_%s_%s_%s'%(tag,side,i),(x+side*.097,yy,zz),(.015,.023,.023),'stationFloorSatin',bevel=.003)

scene=bpy.context.scene;cam=scene.camera
for view in ('overview','detail','supports'):
    if view=='overview':pos=(37.3,-18,18);target=(CX,-4.65,4.45);scale=16.5
    elif view=='detail':pos=(30,-9.7,12.5);target=(CX,-4.9,6.55);scale=7.8
    else:pos=(31,-5,7.4);target=(CX,-4.9,6.1);scale=7.3
    cam.location=pos;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale
    scene.render.filepath='/Users/danielku/mywebsite/secret-base/bridge-review/experience-2-'+view+'.png'
    bpy.ops.render.render(write_still=True)
