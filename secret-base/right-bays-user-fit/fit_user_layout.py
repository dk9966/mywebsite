"""Fit the cave to the user's live arrangement; retain their placed objects."""
import bpy,bmesh,json,math,hashlib,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree

folder=Path(__file__).resolve().parent
diff=json.loads((folder/'user-layout-diff.json').read_text())
shifts={prefix:np.median([c['shift'] for c in diff['changes'] if c['name'].startswith(prefix+' |') and 'shift' in c],axis=0) for prefix in ['Lower','Upper']}
rotation=np.array([[math.cos(math.radians(-72)),-math.sin(math.radians(-72))],[math.sin(math.radians(-72)),math.cos(math.radians(-72))]])
local_shifts={name:rotation.T@d[:2] for name,d in shifts.items()}

# Reuse only the established wall generator. Platform and prop construction is
# deliberately excluded; the user's actual objects are retained from snapshot.
code=(folder.parent/'right-bays-rock-ledge/build_rock_ledge.py').read_text().split('# New manufactured decks:')[0]
injection="\nlo.offset_x+=LOW_DELTA_LOCAL[0];lo.offset_y+=LOW_DELTA_LOCAL[1];lo.z+=LOW_DELTA[2]\nup.offset_x+=UP_DELTA_LOCAL[0];up.offset_y+=UP_DELTA_LOCAL[1];up.z+=UP_DELTA[2]\n"
code=code.replace('LEDGE_TOP=lo.z-.205',injection+'LEDGE_TOP=lo.z-.205')
code=code.replace('tuple(xy(-6.45,.25))','tuple(xy(-7.35,.25))')
# Reference arc-length data stays fixed, including the old -6.45 vertex.
code=code.replace('param.append(cum[1]+(3.75-x))','param.append(cum[1]+(3.75-x)*source_lengths[1]/lengths[1])')
code=code.replace('param.append(cum[1]+(3.75-x-UPPER_SHIFT))','param.append(cum[1]+(3.75-x-UPPER_SHIFT)*source_lengths[1]/lengths[1])')
code=code.replace('ss=np.array(sorted(set(round(v,8) for v in param))+[total])',"for b,left,right in [(lo,-5.36,2.53),(up,-4.70,2.68)]:\n    for x in [left,left+.48,right-.48,right]:param.append(cum[1]+(3.75-x-b.offset_x)*source_lengths[1]/lengths[1])\nss=np.array(sorted(set(round(v,8) for v in param))+[total])")
code=code.replace('xx=3.75-(s-cum[1])','xx=(R.T@(p-ORIGIN))[0]')
code=code.replace('reach=buttress_depth(xx,z)','reach=buttress_depth(xx-lo.offset_x,z)')
code=code.replace('return reach+tier','return max(0.,reach+tier-LOW_DELTA_LOCAL[1])')
selected_extension="""            # User-selected left bay shoulder: push a broad connected rock
            # mass outward; the actual room carve below keeps the deck clear.
            if -7.14<xx<-3.15 and z<lo.z+lo.h+.72:
                if z<LEDGE_TOP:
                    if -6.48<xx<-3.15:field[i,j]-=.68 if z>lo.z-3.1 else .46
                elif z<lo.z+lo.h:
                    if -7.14<xx<-4.2:field[i,j]-=1.12
                else:
                    field[i,j]-=1.18 if z<lo.z+lo.h+.38 else .69
"""
code=code.replace('            for b,left,right,depth in [(lo,-5.36,2.53,2.55),(up,-4.70,2.68,3.04)]:',selected_extension+'            for b,left,right,depth in [(lo,-5.36,2.53,2.55),(up,-4.70,2.68,3.04)]:')
code=code.replace("if left<xx-b.offset_x<right and b.z-.06<z<b.z+b.h:field[i,j]=depth", "if left<xx-b.offset_x<right and b.z-.06<z<b.z+b.h:field[i,j]=depth+(LOW_DELTA_LOCAL[1] if b==lo else UP_DELTA_LOCAL[1])")
code=code.replace('-1.45<xx<1.32:field[i,j]=-1.53','-1.45<xx-lo.offset_x<1.32:field[i,j]=-1.53+LOW_DELTA_LOCAL[1]')
code=code.replace('-1.79<xx<1.62:field[i,j]=-.82','-1.79<xx-lo.offset_x<1.62:field[i,j]=-.82+LOW_DELTA_LOCAL[1]')
LOW_DELTA=shifts['Lower'];UP_DELTA=shifts['Upper'];LOW_DELTA_LOCAL=local_shifts['Lower'];UP_DELTA_LOCAL=local_shifts['Upper']
exec(compile(code,str(folder/'wall_generator_stage.py'),'exec'),globals())
(folder/'wall_generator_stage.py').write_text(code)
wall_only=folder/'fitted-wall-source.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(wall_only),compress=True)
bay_info={'lower':{'z':lo.z,'offset_x':lo.offset_x,'offset_y':lo.offset_y,'poly':LP},'upper':{'z':up.z,'offset_x':up.offset_x,'offset_y':up.offset_y,'poly':UPOLY}}
base_report=json.loads((folder.parent/'right-bays-rock-ledge/preview-ledge-checks.json').read_text())
original_bridge_start=Vector(base_report['bridge_start']);original_bridge_end=Vector(base_report['bridge_end'])

bpy.ops.wm.open_mainfile(filepath=str(folder/'user-layout-snapshot.blend'));S=bpy.context.scene
bpy.context.preferences.filepaths.save_version=0
def state_hash(ob):
    h=hashlib.sha256(np.array(ob.matrix_world,dtype=np.float64).tobytes())
    if ob.type=='MESH':
        a=np.empty(len(ob.data.vertices)*3,dtype=np.float32);ob.data.vertices.foreach_get('co',a);h.update(a.tobytes())
    return h.hexdigest()
(folder/'snapshot-object-hashes.json').write_text(json.dumps({o.name:state_hash(o) for o in S.objects},indent=2))
def is_anchor(name):return any(x in name for x in ['diagonal bracket','bracket flange','bolting shoe'])
user_placed={c['name']:fingerprint(S.objects[c['name']]) for c in diff['changes'] if 'shift' in c and c['name'].startswith(('Lower |','Upper |')) and not is_anchor(c['name']) and S.objects[c['name']].type=='MESH'}
middle={o.name:fingerprint(o) for cn in ['01 | Approved rock and original console','02 | Machined rings and eight recessed grates','03 | Steel perimeter and warm inset lamps'] for o in bpy.data.collections[cn].objects if o.type=='MESH'}
changed_names={c['name'] for c in diff['changes']};aligned=[]
for ob in S.objects:
    for prefix in ['Lower','Upper']:
        if ob.name.startswith(prefix+' |') and ob.type=='MESH' and ob.name not in changed_names:
            ob.matrix_world.translation+=FRAME.to_3x3()@Vector(shifts[prefix]);aligned.append(ob.name)
bpy.context.view_layer.update()

with bpy.data.libraries.load(str(wall_only),link=False) as (src,dst):dst.objects=['150 | continuous cave with oblique carved rooms']
imported=dst.objects[0];wall=S.objects['150 | continuous cave with oblique carved rooms'];wall.data=imported.data;bpy.data.objects.remove(imported,do_unlink=True)

# Stretch the old bridge to the user's new lower landing, keeping its central
# attachment fixed. Boundary-distance weights preserve the skew landing edge.
old_axis=original_bridge_end-original_bridge_start;old_axis.z=0;old_axis.normalize()
normal=Vector((*R[:,1],0));new_bridge_end=original_bridge_end+Vector(shifts['Lower'])
bridge_names=[]
observed_shifts={c['name']:Vector(c['shift']) for c in diff['changes'] if 'shift' in c}
for ob in list(S.objects):
    if not ob.name.startswith('Bridge |') or ob.type!='MESH':continue
    to_local=ob.matrix_world.inverted()@FRAME
    for v in ob.data.vertices:
        p=INV@(ob.matrix_world@v.co)-observed_shifts.get(ob.name,Vector((0,0,0)))
        a=(p-original_bridge_start).dot(old_axis);b=(original_bridge_end-p).dot(normal)
        weight=0. if a<=0 else 1. if b<=0 else a/(a+b/max(.01,old_axis.dot(normal)))
        v.co=to_local@(p+Vector(shifts['Lower'])*weight)
    ob.data.update();bridge_names.append(ob.name)

# Seat moved brackets on the new stone instead of leaving shoes in the air.
tree=BVHTree.FromPolygons([INV@(wall.matrix_world@v.co) for v in wall.data.vertices],[tuple(p.vertices) for p in wall.data.polygons])
def set_beam(ob,p,q):
    span=max(v.co.z for v in ob.data.vertices)-min(v.co.z for v in ob.data.vertices)
    direction=q-p
    ob.matrix_world=FRAME@Matrix.Translation((p+q)/2)@direction.to_track_quat('Z','Y').to_matrix().to_4x4()@Matrix.Diagonal((1,1,direction.length/span,1))
anchor_errors=[]
for ob in list(S.objects):
    if ' | engineered diagonal bracket' not in ob.name:continue
    half=(max(v.co.z for v in ob.data.vertices)-min(v.co.z for v in ob.data.vertices))/2
    endpoints=[INV@(ob.matrix_world@Vector((0,0,z))) for z in [-half,half]];p,q=sorted(endpoints,key=lambda v:v.z,reverse=True)
    hit=tree.find_nearest(q);q=Vector(hit[0]);set_beam(ob,p,q)
    prefix=ob.name.split(' | ')[0];suffix=ob.name.split('diagonal bracket')[1]
    flange=S.objects[prefix+' | upper bracket flange'+suffix];set_beam(flange,p,Vector((q.x,q.y,p.z)))
    shoe=S.objects[prefix+' | rock bolting shoe'+suffix];n=Vector(hit[1]);n=n if n.dot(p-q)>0 else -n
    shoe.matrix_world=FRAME@Matrix.Translation(q+n*.012)@n.to_track_quat('Z','Y').to_matrix().to_4x4()
    anchor_errors.append(float(tree.find_nearest(q)[3]))

bpy.context.view_layer.update()
preservation_errors=[name for name,h in user_placed.items() if fingerprint(S.objects[name])!=h]
middle_errors=[name for name,h in middle.items() if fingerprint(S.objects[name])!=h]
assert not preservation_errors,preservation_errors
assert not middle_errors,middle_errors

# Inspect the wall's actual saved geometry and walkable platform envelopes.
bm=bmesh.new();bm.from_mesh(wall.data);seen=set();parts=[]
for v in bm.verts:
    if v in seen:continue
    todo=[v];seen.add(v);count=0
    while todo:
        current=todo.pop();count+=1
        for edge in current.link_edges:
            other=edge.other_vert(current)
            if other not in seen:seen.add(other);todo.append(other)
    parts.append(count)
bad=sum(len(e.link_faces)>2 or not e.link_faces for e in bm.edges);bm.free()
def inside(x,y,poly):
    yes=False
    for p,q in zip(poly,poly[1:]+poly[:1]):
        if (p[1]>y)!=(q[1]>y) and x<(q[0]-p[0])*(y-p[1])/(q[1]-p[1])+p[0]:yes=not yes
    return yes
intrusions=[]
for label,b in bay_info.items():
    for x in np.arange(min(p[0] for p in b['poly'])+.16,max(p[0] for p in b['poly']),.24):
        for y in np.arange(min(p[1] for p in b['poly'])+.16,max(p[1] for p in b['poly']),.24):
            if inside(x,y,b['poly']):
                p=Vector((*xy(x+b['offset_x'],y+b['offset_y']),b['z']+.09))
                hit=tree.ray_cast(p,Vector((0,0,1)),1.75)
                if hit[0] is not None:intrusions.append([label,float(x),float(y),list(hit[0])])
report={'user_source':str(folder/'user-layout-snapshot.blend'),'selected_terrain_extension':True,'user_shifts':{k:v.tolist() for k,v in shifts.items()},'bay_info':bay_info,'origin':ORIGIN.tolist(),'yaw_degrees':-72,'aligned_stragglers':aligned,'user_placed_mesh_count':len(user_placed),'user_placed_changes':preservation_errors,'middle_changes':middle_errors,'wall_components':parts,'invalid_wall_edges':bad,'standing_rock_intrusions':intrusions,'anchor_errors':anchor_errors,'bridge_start':list(original_bridge_start),'bridge_end':list(new_bridge_end)}
report['passed']=not preservation_errors and not middle_errors and len(parts)==1 and bad==0 and not intrusions
(folder/'coherent-bays-checks.json').write_text(json.dumps(report,indent=2))
print('FIT_CHECK',json.dumps(report),flush=True)
assert report['passed'],'Terrain or preservation checks failed; inspect JSON.'

# Reframe the inspection cameras for the higher user-positioned upper bay.
detail=S.objects['150 | same azimuth detail'];detail.rotation_euler=(FRAME@Vector((7.3,.5,9.5))-detail.location).to_track_quat('-Z','Y').to_euler();detail.data.lens=36
foundation=S.objects['155 | rock foundation detail'];foundation.rotation_euler=(FRAME@Vector((7.55,-.16,4.8))-foundation.location).to_track_quat('-Z','Y').to_euler()
S.camera=S.objects['150 | main cave camera'];S.name='Cave | terrain fitted to user platform layout'
try:
    prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='METAL';prefs.get_devices()
    for d in prefs.devices:d.use=d.type=='METAL'
    S.cycles.device='GPU'
except Exception:S.cycles.device='CPU'
S.render.engine='CYCLES';S.cycles.samples=48;S.cycles.use_denoising=True;S.render.resolution_x=2000;S.render.resolution_y=1120;S.render.resolution_percentage=100
S.render.filepath=str(folder/'coherent-bays-overview.png')
tx=bpy.data.texts.new('fit_user_layout.py');tx.write(Path(__file__).read_text())
bpy.ops.wm.save_as_mainfile(filepath=str(folder/'coherent-bays.blend'),compress=True)
for cam,suffix in [(S.camera,'overview'),(detail,'detail'),(foundation,'foundation')]:
    S.camera=cam;S.render.filepath=str(folder/('coherent-bays-'+suffix+'.png'));bpy.ops.render.render(write_still=True)
print('SAVED_RESULT',str(folder/'coherent-bays.blend'),flush=True)
