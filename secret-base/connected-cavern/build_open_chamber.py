"""Keep the central island in a wider single-surface cave; remove all right bays."""
import argparse, ast, hashlib, importlib.util, json, math, sys
from pathlib import Path
import bpy, bmesh, numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

P=Path(__file__).resolve().parent; ROOT=P.parents[1]
SOURCE=P/'connected-cavern-right-wall-rebuilt.blend'
CENTER_SOURCE=P.parent/'central-metal-platform/central-metal-platform.blend'
ap=argparse.ArgumentParser();ap.add_argument('--final',action='store_true');a=ap.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
FRAME=Matrix.Translation((21.299999237,0,0))@Matrix.Rotation(-math.atan2(12,19),4,'Z');INV=FRAME.inverted()
src=ast.parse((P.parent/'central-metal-platform/build_metal_platform.py').read_text())
exec(compile(ast.Module(body=[n for n in src.body if isinstance(n,ast.FunctionDef) and n.name=='fingerprint'],type_ignores=[]),'fingerprint','exec'),globals())
bpy.ops.wm.open_mainfile(filepath=str(SOURCE));S=bpy.context.scene;S.name='Central island | spacious continuous cave'
bpy.context.preferences.filepaths.save_version=0
keep_collections=['01 | Approved rock and original console','02 | Machined rings and eight recessed grates']
protected={o.name:fingerprint(o) for c in keep_collections for o in bpy.data.collections[c].objects if o.type=='MESH'}
removed=[]
keep_lights={'Bays | upper rock reveal','Bays | lower cliff soft fill','Bays | central ceiling pool','Interior | left restrained bounce','Interior | rear grazing fill'}
for ob in list(S.objects):
    in_center=any(c.name in keep_collections+['04 | Presentation cameras and studio lights'] for c in ob.users_collection)
    if in_center or 'Atmosphere' in ob.name or ob.name in keep_lights:continue
    removed.append(ob.name);bpy.data.objects.remove(ob,do_unlink=True)
# Replace the cut fence with the untouched central platform's full perimeter.
# This restores only the original seven missing fittings and continuous rails.
rail_name='03 | Steel perimeter and warm inset lamps'
old_rail=bpy.data.collections.get(rail_name)
if old_rail:bpy.data.collections.remove(old_rail)
with bpy.data.libraries.load(str(CENTER_SOURCE),link=False) as (available,loaded):
    loaded.collections=[rail_name]
rail=loaded.collections[0];S.collection.children.link(rail)
for ob in rail.objects:
    for slot in ob.material_slots:
        if slot.material and slot.material.name.rsplit('.',1)[-1].isdigit():
            original=bpy.data.materials.get(slot.material.name.rsplit('.',1)[0])
            if original:slot.material=original
    ob.hide_render=False;ob.hide_viewport=False
for col in list(bpy.data.collections):
    if not col.objects and not col.children:bpy.data.collections.remove(col)
for key in ['right_bay_geometry','engineered_supports_revision']:
    if key in S:del S[key]
wall_col=bpy.data.collections.new('05 | Single cave wall');S.collection.children.link(wall_col)
rig=bpy.data.collections.new('06 | Spacious cave views');S.collection.children.link(rig)
rockmat=S.objects['Central rock mound | continuous cross-column extrusions'].data.materials[0]

# Retain the accepted field's broad planes and shallow ledges. The right side
# uses the same field family without architectural cavities or support folds.
code=(P/'build_interior_cavern.py').read_text();ns={'np':np,'math':math}
exec(code[code.index('rng=np.random.default_rng(76183)'):code.index('outer=np.full((N,M),20.)')],ns)
theta,zv,field=ns['theta'],ns['zv'],ns['inner'].copy();N,M=field.shape
for i in range(N):
    deg=math.degrees(theta[i])
    if deg<75 or deg>300:
        # Use a varied broad-step patch from the opposite wall. Do not copy its
        # deep alcoves; the removed right platforms leave an uninterrupted wall.
        j=(i+N//2)%N
        field[i]=6+np.clip(ns['inner'][j]-6,-.72,.30)
for _ in range(12):
    fixes=0
    for i in range(N):
        k=(i+1)%N
        for j in range(M-1):
            aa,bb,cc,dd=field[i,j],field[k,j],field[i,j+1],field[k,j+1]
            if min(aa,dd)>max(bb,cc)+1e-7:
                if bb>=cc:field[k,j]=min(aa,dd)
                else:field[i,j+1]=min(aa,dd)
                fixes+=1
            elif min(bb,cc)>max(aa,dd)+1e-7:
                if aa>=dd:field[i,j]=min(bb,cc)
                else:field[k,j+1]=min(bb,cc)
                fixes+=1
    if not fixes:break

# The chamber sides move outward, and the camera/front side has extra room.
# These are upright faceted plan contours, with no upper-bay jutting volumes.
stations=[(0,9.2),(18,9.5),(36,9.8),(54,10.2),(72,10.0),(90,10.4),
          (110,10.8),(131,10.1),(144,9.4),(157,8.8),(174,8.5),(190,8.9),
          (203,9.8),(218,11.7),(234,13.8),(252,15.0),(270,15.5),
          (287,15.0),(307,14.0),(320,12.8),(334,11.3),(350,9.8)]
angs=np.radians([d for d,r in stations]);radii=np.array([r for d,r in stations]);contour=np.column_stack((np.cos(angs)*radii,np.sin(angs)*radii))
def plan_radius(t):
    direction=np.array((math.cos(t),math.sin(t)));hits=[]
    for p,q in zip(contour,np.roll(contour,-1,axis=0)):
        e=q-p;den=direction[0]*e[1]-direction[1]*e[0]
        if abs(den)<1e-10:continue
        u=(p[0]*direction[1]-p[1]*direction[0])/den;r=(p[0]*e[1]-p[1]*e[0])/den
        if r>0 and -1e-6<=u<=1.000001:hits.append(r)
    return min(hits)
spec=importlib.util.spec_from_file_location('pillar_steps',ROOT/'meshes/pillars/island_pillar_src/shape.py');shape=importlib.util.module_from_spec(spec);spec.loader.exec_module(shape)
tri,raw=shape.mesh_field(theta,zv,np.ones(M+1),field,np.full_like(field,30.)).arrays()
rad=np.hypot(raw[:,0],raw[:,2]);inner=np.all(rad[tri]<20,axis=1)
caps=np.all(abs(raw[tri,1]-zv[0])<1e-8,axis=1)|np.all(abs(raw[tri,1]-zv[-1])<1e-8,axis=1)
tri=tri[inner&~caps];used=np.unique(tri);remap=np.full(len(raw),-1,dtype=int);remap[used]=np.arange(len(used));tri=remap[tri];raw=raw[used]
vertices=[]
for x,z,y in raw:
    t=math.atan2(y,x);r=plan_radius(t)+math.hypot(x,y)-6;h=(z-zv[0])/(zv[-1]-zv[0])
    z+=h**6*(.45*math.sin(t*5)-max(0.,-math.sin(t)))
    vertices.append((r*math.cos(t),r*math.sin(t),z))
me=bpy.data.meshes.new('Cave | continuous interior step skin');me.from_pydata(vertices,[],tri.tolist());me.materials.append(rockmat);me.update()
bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bmesh.ops.dissolve_limit(bm,angle_limit=.00002,verts=list(bm.verts),edges=list(bm.edges),delimit={'NORMAL'})
bm.to_mesh(me);bm.free()
wall=bpy.data.objects.new('Cave | one continuous spacious wall',me);wall_col.objects.link(wall);wall.matrix_world=FRAME
wall['surface_only']=True;wall['thickness']=0.;wall['open_top_and_bottom']=True
wall['construction']='One connected interior surface from the original pillar step mesher. No right bays, exterior layers, roof, floor, smoothing or solidify.'
for face in me.polygons:face.use_smooth=False

def camera(name,pos,target,lens=24,ortho=None):
    ob=bpy.data.objects.new(name,bpy.data.cameras.new(name));rig.objects.link(ob);ob.location=FRAME@Vector(pos);ob.rotation_euler=(FRAME@Vector(target)-ob.location).to_track_quat('-Z','Y').to_euler();ob.data.lens=lens;ob.data.clip_end=200
    if ortho:ob.data.type='ORTHO';ob.data.ortho_scale=ortho
    return ob
hero=camera('Cave | spacious overview',(0,-13.0,11.2),(0,1.4,5.7),22)
reverse=camera('Cave | reverse inspection',(0,7.8,10.0),(0,-1.8,5.5),22)
plan=camera('Cave | overhead spacing',(0,-1.5,43),(0,-1.5,0),ortho=32)
# Preserve the island's practical lights. Move the two former cliff washes to
# graze the new bare wall; remove every light belonging to the deleted bays.
for name,pos,target in [('Bays | upper rock reveal',(4,-.5,14),(9,3,8)),('Bays | lower cliff soft fill',(4,-6,5),(9,-3,3)),('Interior | left restrained bounce',(-3,-3,11),(-8,1,8)),('Interior | rear grazing fill',(1,3,12),(-2,10,8))]:
    ob=S.objects[name];ob.location=FRAME@Vector(pos);ob.rotation_euler=(FRAME@Vector(target)-ob.location).to_track_quat('-Z','Y').to_euler()
    if name.startswith('Bays |'):ob.name=name.replace('Bays |','Cave |')
bpy.context.view_layer.update()
changed=[n for n,h in protected.items() if n not in S.objects or fingerprint(S.objects[n])!=h];assert not changed,changed

def inspect():
    bm=bmesh.new();bm.from_mesh(me);tree=BVHTree.FromBMesh(bm);seen=set();parts=[]
    for v in bm.verts:
        if v in seen:continue
        seen.add(v);stack=[v];count=0
        while stack:
            q=stack.pop();count+=1
            for edge in q.link_edges:
                other=edge.other_vert(q)
                if other not in seen:seen.add(other);stack.append(other)
        parts.append(count)
    todo={e for e in bm.edges if e.is_boundary};loops=[]
    while todo:
        stack=[todo.pop()];count=0
        while stack:
            edge=stack.pop();count+=1
            for v in edge.verts:
                for e in v.link_edges:
                    if e in todo:todo.remove(e);stack.append(e)
        loops.append(count)
    invalid=sum(len(e.link_faces)>2 or not e.link_faces for e in bm.edges);degenerate=sum(f.calc_area()<1e-10 for f in bm.faces)
    gaps=[];radial={}
    for z in [0.,3.,6.9,10.,14.]:
        hits=[]
        for deg in range(360):
            t=math.radians(deg+.23);hit=tree.ray_cast(Vector((0,0,z)),Vector((math.cos(t),math.sin(t),0)),60)
            if hit[0] is None:gaps.append([z,deg])
            else:hits.append(hit[3])
        radial[str(z)]={'min':min(hits),'max':max(hits)}
    deck_points=[INV@(o.matrix_world@v.co) for c in ['02 | Machined rings and eight recessed grates',rail_name] for o in bpy.data.collections[c].objects if o.type=='MESH' for v in o.data.vertices]
    deck_radius=max(math.hypot(v.x,v.y) for v in deck_points)
    nearest=min(tree.find_nearest(v)[3] for v in deck_points)
    unexpected=[o.name for o in S.objects if o.type=='MESH' and o.name not in protected and o not in rail.objects.values() and o!=wall and 'Atmosphere' not in o.name]
    result={'source':str(SOURCE),'right_side_objects_removed':len(removed),'protected_center_meshes':len(protected),'center_meshes_changed':changed,'rail_restored_from':str(CENTER_SOURCE),'rail_meshes':len(rail.objects),'wall_components':parts,'boundary_loops':loops,'invalid_edges':invalid,'degenerate_faces':degenerate,'ray_gaps':gaps,'wall_radial_distance':radial,'central_deck_radius':deck_radius,'nearest_wall_distance_from_platform_geometry':nearest,'minimum_radial_gap_at_deck':radial['6.9']['min']-deck_radius,'wall_thickness':0,'wall_modifiers':len(wall.modifiers),'unexpected_meshes':unexpected}
    result['passed']=len(parts)==1 and len(loops)==2 and not invalid and not degenerate and not gaps and not changed and not unexpected and nearest>4
    bm.free();return result
report=inspect();assert report['passed'],report
tag='open-chamber' if a.final else 'preview-open-chamber';out=P/('connected-cavern-open-chamber.blend' if a.final else tag+'.blend')
(P/(tag+'-verification.json')).write_text(json.dumps(report,indent=2));print('OPEN_CHAMBER_CHECK',json.dumps(report),flush=True)
try:
    prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='METAL';prefs.get_devices()
    for device in prefs.devices:device.use=device.type=='METAL'
    S.cycles.device='GPU'
except Exception:S.cycles.device='CPU'
S.camera=hero;S.render.engine='CYCLES';S.cycles.samples=64 if a.final else 24;S.cycles.use_denoising=True
S.render.resolution_x=2000 if a.final else 1400;S.render.resolution_y=round(S.render.resolution_x*.625);S.render.resolution_percentage=100;S.render.use_border=False;S.render.use_crop_to_border=False;S.render.image_settings.file_format='PNG'
S.render.filepath=str(P/(tag+'-overview.png'))
for screen in bpy.data.screens:
    for ar in screen.areas:
        if ar.type=='VIEW_3D':ar.spaces.active.region_3d.view_perspective='CAMERA';ar.spaces.active.overlay.show_extras=False
bpy.ops.object.select_all(action='DESELECT');wall.select_set(True);bpy.context.view_layer.objects.active=wall
tx=bpy.data.texts.get('build_open_chamber.py') or bpy.data.texts.new('build_open_chamber.py');tx.clear();tx.write(Path(__file__).read_text())
bpy.ops.wm.save_as_mainfile(filepath=str(out),compress=True)
bpy.ops.wm.open_mainfile(filepath=str(out));S=bpy.context.scene
report['reopened_saved_file']=True;report['sha256']=hashlib.sha256(out.read_bytes()).hexdigest()
report['saved_center_changes']=[n for n,h in protected.items() if n not in S.objects or fingerprint(S.objects[n])!=h];assert not report['saved_center_changes']
(P/(tag+'-verification.json')).write_text(json.dumps(report,indent=2))
bpy.ops.render.render(write_still=True)
S.camera=S.objects['Cave | reverse inspection'];S.render.filepath=str(P/(tag+'-reverse.png'));bpy.ops.render.render(write_still=True)
S.camera=S.objects['Cave | overhead spacing'];S.render.engine='BLENDER_WORKBENCH';S.render.resolution_x=1500;S.render.resolution_y=1500
sh=S.display.shading;sh.light='STUDIO';sh.color_type='OBJECT';sh.show_cavity=True;sh.cavity_type='BOTH';sh.background_type='WORLD';S.world.color=(.055,.065,.08)
for ob in S.objects:
    if ob.type=='MESH':ob.color=(.26,.32,.38,1) if ob.name=='Cave | one continuous spacious wall' else (.65,.69,.74,1)
    if 'Atmosphere' in ob.name:ob.hide_render=True
S.render.filepath=str(P/(tag+'-plan.png'));bpy.ops.render.render(write_still=True)
print('OPEN_CHAMBER_SAVED',str(out),flush=True)
