"""Add an empty matching pillar and a level bridge to the current base.blend.

Run once on the pre-bridge scene. Preserves original meshes in a hidden backup
collection; bridge parts are individually editable and use existing materials.
"""
import bpy, bmesh, math
from mathutils import Vector, Matrix

assert not bpy.data.objects.get('island_pillar_empty'), 'Bridge already built'
if bpy.context.object and bpy.context.object.mode != 'OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')
host = bpy.data.objects.get('island_pillar_project') or bpy.data.objects['island_pillar_workshop']
host.name = 'island_pillar_project'
host['station_role'] = 'Project'
coll = bpy.data.collections.get('deck_workshop') or bpy.data.collections['deck_project']
coll.name = 'deck_project'
newcoll = bpy.data.collections.new('deck_empty')
bpy.context.scene.collection.children.link(newcoll)
bridgecoll = bpy.data.collections.new('bridge_project_empty')
bpy.context.scene.collection.children.link(bridgecoll)
archive = bpy.data.collections.new('bridge_original_geometry')
bpy.context.scene.collection.children.link(archive)
archive.hide_render = True
archive.hide_viewport = True
CX = host.matrix_world.translation.x
CY = host.matrix_world.translation.y
OFFSET = Vector((0,-9.3,0))
F = 6.871178627
R = 2.712
HALF = .65
LAND = math.sqrt(R*R-HALF*HALF)
Y0, Y1 = CY-LAND, CY-9.3+LAND

def duplicate(src, name, target, delta=Vector((0,0,0)), parent=None):
    ob=src.copy()
    if src.data: ob.data=src.data.copy()
    ob.name=name
    target.objects.link(ob)
    mw=src.matrix_world.copy(); mw.translation += delta
    ob.parent=parent
    ob.matrix_world=mw
    return ob

empty=duplicate(host,'island_pillar_empty',newcoll,OFFSET)
empty['station_role']='Empty'
for name in ['deck_floor_b','deck_parapet_b','deck_railing_b','deck_railing_back_b',
             'deck_pillar_veins_neonCyan_b','deck_pillar_veins_neonCyanFaint_b']:
    duplicate(bpy.data.objects[name],name.removesuffix('_b')+'_empty',newcoll,OFFSET,empty)
for ob in list(coll.objects):
    if ob.type=='LIGHT' and any(k in ob.name for k in ('key_b','fill_b','rim_b','shaft_','vein_spill')):
        duplicate(ob,ob.name.removesuffix('_b')+'_empty',newcoll,OFFSET,empty)

def cube(name, loc, dims, mat, collection=bridgecoll):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc)
    ob=bpy.context.object; ob.name=name
    ob.dimensions=dims
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    for c in list(ob.users_collection): c.objects.unlink(ob)
    collection.objects.link(ob)
    if mat: ob.data.materials.append(bpy.data.materials[mat])
    return ob

def cut_entrance(ob, center_y, direction):
    duplicate(ob,ob.name+'_before_bridge',archive)
    # Remove complete individual posts near the mouth; no sliced half-posts.
    if 'railing' in ob.name:
        bm=bmesh.new(); bm.from_mesh(ob.data)
        unseen=set(bm.verts)
        while unseen:
            start=unseen.pop(); component={start}; stack=[start]
            while stack:
                v=stack.pop()
                for e in v.link_edges:
                    w=e.other_vert(v)
                    if w in unseen: unseen.remove(w); component.add(w); stack.append(w)
            world=[ob.matrix_world@v.co for v in component]
            mid=sum(world,Vector())/len(world)
            if len(component)<=24 and abs(mid.x-CX)<HALF+.14 and direction*(mid.y-center_y)>2.3:
                bmesh.ops.delete(bm,geom=list(component),context='VERTS')
        bm.to_mesh(ob.data); bm.free()
    cutter=cube('temporary_entrance_cutter',(CX,center_y+direction*3.05,7.35),(HALF*2,1.3,1.5),None)
    bpy.context.view_layer.objects.active=ob
    mod=ob.modifiers.new('Open bridge entrance','BOOLEAN'); mod.operation='DIFFERENCE'; mod.solver='EXACT'; mod.object=cutter
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter,do_unlink=True)

for suff,cy,direction in [('_b',CY,-1),('_empty',CY-9.3,1)]:
    for prefix in ['deck_railing','deck_railing_back','deck_parapet']:
        ob=bpy.data.objects[prefix+suff]
        # Match rear fence heights to the existing slim front fence.
        if prefix=='deck_railing_back':
            for v in ob.data.vertices:
                z=v.co.z
                if abs(z-7.1852)<.001: v.co.z=7.154
                elif abs(z-7.2112)<.001: v.co.z=7.1717
                elif abs(z-7.3802)<.001: v.co.z=7.2866
                elif abs(z-7.4062)<.001: v.co.z=7.3043
                elif abs(z-7.4327)<.001: v.co.z=7.3223
        cut_entrance(ob,cy,direction)

# A continuous bearing slab extends into each deck; the top is flush with paving.
length=Y0-Y1
cube('bridge_bearing_slab',(CX,(Y0+Y1)/2,F-.075),(1.42,length+.26,.15),'stationFloorSatin')
for side in (-1,1):
    x=CX+side*HALF
    cube('bridge_edge_kerb_'+str(side),(x,(Y0+Y1)/2,F+.025),(.12,length,.05),'stationFloorSatin')
    cube('bridge_side_girder_'+str(side),(x,(Y0+Y1)/2,F-.20),(.15,length+.35,.22),'graphite')
    for z in (7.16285,7.29545):
        cube('bridge_rail_'+str(side)+'_'+str(z),(x,(Y0+Y1)/2,z),(.038,length,.0177),'mcWood')
    bays=8
    for i in range(bays+1):
        y=Y1+length*i/bays
        endpoint=i in (0,bays)
        width=.095 if endpoint else .05
        top=7.3757 if endpoint else 7.3223
        cube('bridge_post_%s_%02d'%(side,i),(x,y,(F+.05+top)/2),(width,width,top-F-.05),'mcWood')
        if endpoint:
            cube('bridge_newel_cap_%s_%02d'%(side,i),(x,y,7.38655),(.125,.125,.0217),'mcWood')
        cube('bridge_crossbearer_%s_%02d'%(side,i),(CX,y,F-.145),(1.45,.07,.14),'graphite') if side==-1 else None
# Shallow separated paving plates match the scale and finish of the deck stones.
for i in range(16):
    y=Y1+length*(i+.5)/16
    for side in (-1,1):
        cube('bridge_paving_%02d_%s'%(i,side),(CX+side*.285,y,F+.003),(.56,length/16-.009,.006),'stationFloorSatin')

# Soft scene illumination: no props or fixtures are added to the empty deck.
ld=bpy.data.lights.new('bridge_soft_fill','AREA'); ld.energy=65; ld.shape='DISK'; ld.size=5
ld.color=(.48,.69,1)
lo=bpy.data.objects.new('bridge_soft_fill',ld); bridgecoll.objects.link(lo)
lo.location=(CX,(Y0+Y1)/2,11)

for ob in bridgecoll.objects:
    if ob.type=='MESH':
        mw=ob.matrix_world.copy(); ob.parent=host; ob.matrix_world=mw
bpy.context.view_layer.update()
camera_data=bpy.data.cameras.new('project_bridge_review')
camera=bpy.data.objects.new('project_bridge_review',camera_data)
bpy.context.scene.collection.objects.link(camera)
camera.location=(CX+16,CY-18,18)
target=Vector((CX,CY-4.65,4.6))
camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
camera_data.type='ORTHO'; camera_data.ortho_scale=16.5
bpy.context.scene.camera=camera
scene=bpy.context.scene
scene.render.resolution_x=1400; scene.render.resolution_y=1100; scene.render.resolution_percentage=100
scene.render.filepath='/Users/danielku/mywebsite/secret-base/bridge-review/iteration-1.png'
bpy.ops.render.render(write_still=True)
