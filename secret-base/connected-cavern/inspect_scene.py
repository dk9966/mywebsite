import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'right-cave-bays/central-pillar-right-cave-bays.blend'))
S=bpy.context.scene;F=Matrix.Translation((21.299999237,0,0))@Matrix.Rotation(-math.atan2(12,19),4,'Z');I=F.inverted()
vs=[];fs=[];bounds={}
for o in bpy.data.collections['07 | Continuous approved-style cave wall'].objects:
    if o.type!='MESH':continue
    pts=[I@(o.matrix_world@v.co) for v in o.data.vertices];ofs=len(vs);vs+=pts;fs+=[tuple(ofs+i for i in p.vertices) for p in o.data.polygons]
    bounds[o.name]={'min':[min(p[k] for p in pts) for k in range(3)],'max':[max(p[k] for p in pts) for k in range(3)],'vertices':len(pts)}
tree=BVHTree.FromPolygons(vs,fs);rays={}
for z in [3.0,7.0,9.0]:
    hits=[]
    for deg in range(0,360,10):
        t=math.radians(deg);h=tree.ray_cast(Vector((0,0,z)),Vector((math.cos(t),math.sin(t),0)),70)
        hits.append([deg,h[3]])
    rays[str(z)]=hits
(P/'existing-layout.json').write_text(json.dumps({'bounds':bounds,'radial_wall_distances':rays},indent=2))
# Fast multi-angle structural views, independent of the beauty lighting.
for o in bpy.data.objects:
    if 'atmosphere' in o.name.lower() or any(c.name=='11 | Editable cave excavation volumes' for c in o.users_collection):o.hide_render=True
S.render.engine='BLENDER_WORKBENCH';S.display.shading.light='STUDIO';S.display.shading.studiolight_rotate_z=.4;S.display.shading.color_type='MATERIAL';S.display.shading.show_shadows=True;S.display.shading.show_cavity=True;S.display.shading.cavity_type='BOTH';S.display.shading.curvature_ridge_factor=1.4;S.display.shading.curvature_valley_factor=1.1;S.display.shading.background_type='WORLD';S.world.color=(.07,.09,.12)
for m in bpy.data.materials:
    if m.name.startswith(('Metal |','Bays |')):m.diffuse_color=(.38,.44,.50,1)
for o in bpy.data.collections['07 | Continuous approved-style cave wall'].objects:
    for m in o.data.materials:m.diffuse_color=(.22,.28,.32,1)
S.render.resolution_x=1200;S.render.resolution_y=950;S.render.resolution_percentage=100;S.render.use_border=False
cam=bpy.data.objects.new('Inspection camera',bpy.data.cameras.new('Inspection camera'));S.collection.objects.link(cam);cam.data.type='ORTHO';S.camera=cam
for name,pos,target,scale in [('existing-plan',(3,3,45),(3,3,5),36),('existing-left',(-23,-24,23),(4,2,6),36),('existing-rear',(21,27,22),(4,2,6),38)]:
    cam.location=F@Vector(pos);cam.rotation_euler=(F@Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale
    S.render.filepath=str(P/(name+'.png'));bpy.ops.render.render(write_still=True)
print('INSPECTION_COMPLETE',flush=True)
