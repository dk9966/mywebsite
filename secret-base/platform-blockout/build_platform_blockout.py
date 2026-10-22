"""Simplify the side platforms and resize the central deck from the live scene."""
import bpy,bmesh,math,json,hashlib,array
from pathlib import Path
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P/'source-live-snapshot.blend'))
S=bpy.context.scene
if bpy.context.object and bpy.context.object.mode!='OBJECT':bpy.ops.object.mode_set(mode='OBJECT')
bpy.context.preferences.filepaths.save_version=0
FRAME=Matrix.Translation((21.299999237,0,0))@Matrix.Rotation(-math.atan2(12,19),4,'Z');INV=FRAME.inverted()
R=Matrix.Rotation(math.radians(-72),4,'Z');RI=R.inverted()
F=6.871178627
def fp(ob):
    h=hashlib.sha256(repr([list(r) for r in ob.matrix_world]).encode())
    a=array.array('f',[0.])*(len(ob.data.vertices)*3);ob.data.vertices.foreach_get('co',a);h.update(a.tobytes())
    return h.hexdigest()
terrain={o.name:fp(o) for o in S.objects if o.type=='MESH' and ('continuous cave' in o.name or 'Central rock mound' in o.name)}
def caveverts(ob):return [INV@(ob.matrix_world@v.co) for v in ob.data.vertices]
ring=S.objects['Lower | octagon-centered registration'];pv=caveverts(ring);low_center=sum(pv,Vector())/len(pv)
low_floor=S.objects['Lower | continuous floor footprint'];lv=caveverts(low_floor);low_z=max(p.z for p in lv)
upper=S.objects['Upper | continuous floor footprint'];uv=[RI@p for p in caveverts(upper)]
upper_z=max(p.z for p in uv)
low_local=[RI@(p-low_center) for p in lv];apothem=max(p.x for p in low_local)
lower_radius=apothem/math.cos(math.pi/8);upper_radius=lower_radius*.9
# Keep the rear of the upper floor in its existing alcove while simplifying
# the long gallery into an octagon. Its along-wall midpoint is retained.
ux=(min(p.x for p in uv)+max(p.x for p in uv))*.5
uy=max(p.y for p in uv)-apothem*.9
upper_center=R@Vector((ux,uy,upper_z))
low_center.z=low_z
materials=[bpy.data.materials['Metal | satin blue steel'],bpy.data.materials['Metal | dark structural steel']]
removed=[]
for cn in ['151 | Octagonal service apron','152 | Clipped upper gallery','153 | 125 degree octagon connection']:
    for ob in list(bpy.data.collections[cn].objects):removed.append(ob.name);bpy.data.objects.remove(ob,do_unlink=True)
# Room props, architectural frames, markings, railings and support details are
# all removed. Keep two soft presentation lights so the plain slabs read well.
for ob in list(S.objects):
    if ob.type=='LIGHT' and ob.name.startswith(('Lower |','Upper |')):
        if 'primary room practical' in ob.name:
            ob.name='Blockout | '+('lower' if ob.name.startswith('Lower') else 'upper')+' fill'
        else:removed.append(ob.name);bpy.data.objects.remove(ob,do_unlink=True)
def new_mesh(name,vertices,faces,collection):
    me=bpy.data.meshes.new(name);me.from_pydata(vertices,[],faces);me.update()
    bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
    for m in materials:me.materials.append(m)
    for face in me.polygons:face.material_index=0 if face.normal.z>.5 else 1
    ob=bpy.data.objects.new(name,me);collection.objects.link(ob);return ob
def octagon(name,center,radius,collection):
    pts=[(radius*math.cos(math.pi/8+i*math.tau/8),radius*math.sin(math.pi/8+i*math.tau/8)) for i in range(8)]
    verts=[(x,y,z) for z in [-.20,0] for x,y in pts]
    faces=[tuple(reversed(range(8))),tuple(range(8,16))]+[(i,(i+1)%8,(i+1)%8+8,i+8) for i in range(8)]
    ob=new_mesh(name,verts,faces,collection);ob.matrix_world=FRAME@Matrix.Translation(center)@R
    ob['circumradius']=radius;ob['apothem']=radius*math.cos(math.pi/8)
    return ob,pts
lower,lp=octagon('Lower | plain octagon',low_center,lower_radius,bpy.data.collections['151 | Octagonal service apron'])
top,_=octagon('Upper | plain octagon - 90 percent radius',upper_center,upper_radius,bpy.data.collections['152 | Clipped upper gallery'])

heading=math.atan2(low_center.y,low_center.x);direction=Vector((math.cos(heading),math.sin(heading),0))
old_gate=math.atan2(-1.5085060596466064,2.154369831085205)
deck_transform=FRAME@Matrix.Diagonal((1.2,1.2,1,1))@INV
rail_transform=FRAME@Matrix.Rotation(heading-old_gate,4,'Z')@Matrix.Diagonal((1.2,1.2,1,1))@INV
for ob in bpy.data.collections['02 | Machined rings and eight recessed grates'].objects:ob.matrix_world=deck_transform@ob.matrix_world
for ob in bpy.data.collections['03 | Steel perimeter and warm inset lamps'].objects:ob.matrix_world=rail_transform@ob.matrix_world
for ob in S.objects:
    if ob.name.startswith('Metal | amber floor pool'):ob.matrix_world=rail_transform@ob.matrix_world

# Shrink the complete console/machinery assembly around its shared floor pivot.
props=[o for o in S.objects if o.name.startswith('deck_desk') and o.type=='MESH']
points=[p for o in props for p in caveverts(o)]
pivot=Vector(((min(p.x for p in points)+max(p.x for p in points))*.5,(min(p.y for p in points)+max(p.y for p in points))*.5,min(p.z for p in points)))
destination=Vector((pivot.x*1.2,pivot.y*1.2,pivot.z))
prop_xform=FRAME@Matrix.Translation(destination)@Matrix.Diagonal((.5,.5,.5,1))@Matrix.Translation(-pivot)@INV
prop_dimensions_before={o.name:list(o.dimensions) for o in props}
for ob in props:ob.matrix_world=prop_xform@ob.matrix_world

# Find the near octagon edge along the central platform's radial direction.
d=RI@(-direction);distance_to_edge=float('inf')
for i in range(8):
    p=Vector((*lp[i],0));q=Vector((*lp[(i+1)%8],0));edge=q-p
    normal=Vector((edge.y,-edge.x,0)).normalized();den=normal.dot(d)
    if den>1e-8:distance_to_edge=min(distance_to_edge,normal.dot(p)/den)
near=low_center-direction*distance_to_edge
start=direction*(2.806*1.2-.13);start.z=F
end=near+direction*.12;end.z=low_z
span=end-start;length=span.length;bridge_width=1.08;thickness=.14
verts=[(x,y,z) for x in [0,length] for y in [-bridge_width/2,bridge_width/2] for z in [-thickness,0]]
faces=[(0,4,6,2),(1,3,7,5),(0,1,5,4),(2,6,7,3),(0,2,3,1),(4,5,7,6)]
bridge=new_mesh('Bridge | floating rectangle',verts,faces,bpy.data.collections['153 | 125 degree octagon connection'])
rot=Matrix.Rotation(heading,4,'Z')@Matrix.Rotation(-math.atan2(span.z,Vector((span.x,span.y,0)).length),4,'Y')
bridge.matrix_world=FRAME@Matrix.Translation(start)@rot
bridge['editing_note']='One mesh. Origin at the middle-platform end; local X follows the bridge. Rotate or scale along local axes.'
bridge['width']=bridge_width

# Clear the resized central railing at the radial landing if its old oblique
# cut leaves a fragment in the wider opening. The bridge itself stays plain.
cuts=[]
for ob in bpy.data.collections['03 | Steel perimeter and warm inset lamps'].objects:
    if ob.type!='MESH':continue
    cv=caveverts(ob)
    if any(abs(p.x*direction.y-p.y*direction.x)<bridge_width*.65 and p.dot(direction)>3.0 and p.z>F+.035 for p in cv):cuts.append(ob)
bpy.ops.mesh.primitive_cube_add(size=1)
cut=bpy.context.object;cut.name='Temporary bridge aperture'
cut.matrix_world=FRAME@Matrix.Translation(direction*3.3+Vector((0,0,F+.35)))@Matrix.Rotation(heading,4,'Z')@Matrix.Diagonal((.8,bridge_width+.12,.68,1))
for ob in cuts:
    bpy.context.view_layer.objects.active=ob
    mod=ob.modifiers.new('Radial bridge aperture','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cut
    bpy.ops.object.modifier_apply(modifier=mod.name)
bpy.data.objects.remove(cut,do_unlink=True)
bpy.context.view_layer.update()
obstacles=[];dg=bpy.context.evaluated_depsgraph_get();perp=Vector((-direction.y,direction.x,0))
for ob in bpy.data.collections['03 | Steel perimeter and warm inset lamps'].objects:
    if ob.type!='MESH' or not len(ob.data.polygons):continue
    ev=ob.evaluated_get(dg);me=ev.to_mesh();tree=BVHTree.FromPolygons([INV@(ob.matrix_world@v.co) for v in me.vertices],[tuple(f.vertices) for f in me.polygons])
    for offset in [-.42,0,.42]:
        for height in [.15,.35]:
            p=direction*3.02+perp*offset+Vector((0,0,F+height))
            if tree.ray_cast(p,direction,.70)[0] is not None:obstacles.append(ob.name)
    ev.to_mesh_clear()
terrain_changes=[n for n,h in terrain.items() if fp(S.objects[n])!=h]
report={'terrain_changes':terrain_changes,'lower_radius':lower_radius,'upper_radius':upper_radius,'upper_lower_radius_ratio':upper_radius/lower_radius,'middle_radius_multiplier':1.2,'console_scale':.5,'side_platform_objects':[lower.name,top.name],'bridge_object':bridge.name,'bridge_start':list(start),'bridge_end':list(end),'bridge_dimensions':list(bridge.dimensions),'bridge_radial_alignment':Vector((span.x,span.y,0)).normalized().dot(direction),'bridge_obstacles':sorted(set(obstacles)),'removed_detail_objects':len(removed)}
report['passed']=not terrain_changes and not obstacles and abs(report['bridge_radial_alignment']-1)<1e-5 and abs(upper_radius/lower_radius-.9)<1e-6
(P/'checks.json').write_text(json.dumps(report,indent=2));print('BLOCKOUT_CHECKS',json.dumps(report),flush=True)
assert report['passed']
bpy.ops.object.select_all(action='DESELECT');bridge.select_set(True);bpy.context.view_layer.objects.active=bridge
S.name='Cave | octagon platform blockout'
S.camera=S.objects['150 | main cave camera'];S.render.engine='CYCLES';S.cycles.samples=32;S.cycles.use_denoising=True
S.render.resolution_x=1600;S.render.resolution_y=896;S.render.resolution_percentage=100
try:
    prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='METAL';prefs.get_devices()
    for dev in prefs.devices:dev.use=dev.type=='METAL'
    S.cycles.device='GPU'
except Exception:S.cycles.device='CPU'
bpy.ops.wm.save_as_mainfile(filepath=str(P/'cave-octagon-platforms.blend'),compress=True)
for camera,suffix in [('150 | main cave camera','overview'),('150 | same azimuth detail','detail')]:
    S.camera=S.objects[camera];S.render.filepath=str(P/('octagon-platforms-'+suffix+'.png'));bpy.ops.render.render(write_still=True)
print('DONE',flush=True)
