"""Flatten the local cave wall, shorten its eight ties, and align the floor inlays."""
import bpy, bmesh, math, json, hashlib
import numpy as np
from pathlib import Path
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parent
P=ROOT/'wall-fit';P.mkdir(exist_ok=True)
S=bpy.context.scene
report=json.loads((ROOT/'verification.json').read_text())
F=Matrix(report['frame']);IV=F.inverted()
R=bpy.data.objects['150 | continuous cave with oblique carved rooms']
COL=bpy.data.collections['169 | Left platform display bay']
KEY='Left bay | flatter close wall and short anchors'
assert not R.data.shape_keys or KEY not in R.data.shape_keys.key_blocks, 'Correction already installed'
if bpy.context.mode!='OBJECT':bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.wm.save_as_mainfile(filepath=str(P/'before-wall-fit.blend'),copy=True,compress=True)

def signature(o):
    h=hashlib.sha256(repr(([list(r) for r in o.matrix_world],o.hide_render,o.hide_get(),o.parent.name if o.parent else None)).encode())
    if o.type=='MESH':
        a=np.empty(len(o.data.vertices)*3,dtype=np.float32);o.data.vertices.foreach_get('co',a);h.update(a.tobytes())
        h.update(repr([tuple(p.vertices) for p in o.data.polygons]).encode())
    return h.hexdigest()
allowed={R.name}|{o.name for o in COL.all_objects if any(s in o.name for s in ['rock standoff','embedded rock anchor','floor line'])}
protected={o.name:signature(o) for o in S.objects if o.name not in allowed}
original_keys=[(k.name,k.value,k.mute,k.relative_key.name) for k in R.data.shape_keys.key_blocks] if R.data.shape_keys else []
old=R.data;old.use_fake_user=True;R.data=old.copy();R.data.name='Cave | close left display-bay wall';R['left_bay_before_wall_mesh']=old.name
if not R.data.shape_keys:R.shape_key_add(name='Basis')
keys=R.data.shape_keys.key_blocks;basis=keys[0]
# Measure the existing relative-key mixture. The new key stores only its own delta,
# so current upper-platform sculpt keys remain at their original values.
mixed=[p.co.copy() for p in basis.data]
for key in list(keys)[1:]:
    if key.mute or key.value==0:continue
    assert not key.vertex_group, 'Weighted sculpt key requires an explicit weight mix'
    for i,p in enumerate(key.data):mixed[i]+=(p.co-key.relative_key.data[i].co)*key.value
mx=IV@R.matrix_world;imx=mx.inverted()
key=R.shape_key_add(name=KEY,from_mix=False);key.relative_key=basis;key.value=1

def sm(t):
    t=max(0.,min(1.,t));return t*t*(3-2*t)
changed=[];moves=[]
for i,co in enumerate(mixed):
    p=mx@co;x,y,z=p
    # Preserve the bearing shelf below and gently return to the existing cavern above.
    wz=sm((z-2.65)/.70)*sm((8.30-z)/1.20)
    wx=sm((x+5.0)/1.8)*sm((1.20-x)/1.00)
    wy=sm((y+2.0)/2.2)*sm((13.0-y)/1.3)
    a=wz*wx*wy
    tx=-.24+.023*math.sin(y*1.18+z*.82)+.012*math.sin(y*2.7-z*1.42)
    q=p.copy();q.x=x+(tx-x)*a
    # The perpendicular return is fitted to the fourth upright as the same surface.
    b=wz*sm((x+.20)/.90)*sm((5.20-x)/1.0)*sm((y-10.45)/.80)*sm((15.0-y)/1.2)
    ty=12.32+.025*math.sin(x*1.33+z*.91)+.010*math.sin(x*2.3-z)
    q.y=y+(ty-y)*b
    delta=imx.to_3x3()@(q-p)
    key.data[i].co=basis.data[i].co+delta
    if delta.length>1e-7:
        changed.append(i);moves.append(delta.length)
R['left_bay_wall_sculpt']='Reversible local flattening; close wall x about -0.24 m, perpendicular return y about 12.32 m in bay frame.'
bpy.context.view_layer.update()

def rock_tree():
    ev=R.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh()
    t=BVHTree.FromPolygons([IV@ev.matrix_world@v.co for v in me.vertices],[list(p.vertices) for p in me.polygons]);ev.to_mesh_clear();return t
tree=rock_tree()
FACES=[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
def center(o):return sum((IV@o.matrix_world@v.co for v in o.data.vertices),Vector())/len(o.data.vertices)
def rebox(o,c,t,n,u,w,d,h):
    local=o.matrix_world.inverted()@F
    vs=[local@(c+t*x*w/2+n*y*d/2+u*z*h/2) for z in [-1,1] for x,y in [(-1,-1),(1,-1),(1,1),(-1,1)]]
    old=o.data;old.use_fake_user=True;me=bpy.data.meshes.new(old.name+' | shortened');me.from_pydata(vs,[],FACES)
    for ma in old.materials:me.materials.append(ma)
    bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free();me.update();o.data=me
connections=[]
for support in report['supports']:
    idx=support['index'];n=Vector(support['normal']);t=Vector(support['tangent']);up=Vector((0,0,1));b=Vector(support['origin'])
    prefix='Left bay | support %02d '%idx
    beams=sorted([o for o in COL.all_objects if o.name.startswith(prefix+'rock standoff')],key=lambda o:center(o).z)
    shoes=sorted([o for o in COL.all_objects if o.name.startswith(prefix+'embedded rock anchor')],key=lambda o:center(o).z)
    assert len(beams)==len(shoes)==2
    for j,(beam,shoe) in enumerate(zip(beams,shoes)):
        z=center(shoe).z;front=Vector(support['rock_anchors'][j]['front']);front.z=z
        hit,normal,face,distance=tree.ray_cast(front+n*.32,-n,6)
        assert hit is not None
        # End buried slightly inside the fitted rock, front remains joined to the upright.
        rear=hit-n*.065;axis=(front-rear).normalized();a=axis.cross(up).normalized();bb=axis.cross(a).normalized();length=(front-rear).length
        assert .10<length<.55,(idx,length,list(hit))
        rebox(beam,(rear+front)/2,a,bb,axis,.18,.20,length)
        rebox(shoe,hit,t,n,up,.66,.18,.52)
        beam['wall_tie_length_m']=length;shoe['seated_on_fitted_rock']=True
        connections.append({'support':idx,'level':j,'before_length_m':support['rock_anchors'][j]['length'],'after_length_m':length,'surface':list(hit),'front':list(front),'beam':beam.name})

# Rotate the entire three-line layout around its common center, including every bezel and cap.
line_objects=[o for o in COL.all_objects if o.type=='MESH' and 'floor line' in o.name]
lenses=sorted([o for o in line_objects if 'cyan inlay' in o.name],key=lambda o:o.name)
assert len(lenses)==3
cc=sum((center(o) for o in lenses),Vector())/3
vs=np.array([list(IV@lenses[0].matrix_world@v.co) for v in lenses[0].data.vertices]);_,_,vh=np.linalg.svd(vs-vs.mean(axis=0));direction=Vector(vh[0]);
if direction.y<0:direction=-direction
angle=math.atan2(direction.x,direction.y)
rotation=Matrix.Rotation(angle,4,'Z');transform=Matrix.Translation(cc)@rotation@Matrix.Translation(-cc)
for o in line_objects:
    o.data=o.data.copy();m=o.matrix_world.inverted()@F@transform@IV@o.matrix_world
    for v in o.data.vertices:v.co=m@v.co
    o.data.update()
    if 'angle_from_stair_run_degrees' in o:o['angle_from_stair_run_degrees']=0
    o['parallel_to_platform']=True
COL['floor_layout']='Three equal five-meter lines, 0.95 meter spacing, parallel to platform long edge and entirely beyond stairs.'
bpy.context.view_layer.update()

new_lines=[]
for o in lenses:
    vs=[IV@o.matrix_world@v.co for v in o.data.vertices];c=sum(vs,Vector())/len(vs)
    ext=[max(v[i] for v in vs)-min(v[i] for v in vs) for i in range(3)]
    assert abs(ext[1]-5)<.0001 and abs(ext[0]-.024)<.0001,ext
    new_lines.append({'name':o.name,'center':list(c),'length':ext[1],'a':[c.x,min(v.y for v in vs),c.z],'b':[c.x,max(v.y for v in vs),c.z]})
stairs=bpy.data.collections['166 | Left bridge and right-turn steel stairs']
sv=[IV@o.matrix_world@v.co for o in stairs.objects if o.type=='MESH' and ('tread' in o.name or 'half-height' in o.name) for v in o.data.vertices]
margin=min(line['a'][1] for line in new_lines)-max(p.y for p in sv)
assert margin>.6,margin
protected_changes=[name for name,value in protected.items() if signature(bpy.data.objects[name])!=value]
assert not protected_changes,protected_changes
assert original_keys==[(k.name,k.value,k.mute,k.relative_key.name) for k in list(R.data.shape_keys.key_blocks)[:-1]]
flatness=[]
for y in [.95,3.65,6.5,9.0,10.7]:
    samples=[]
    for z in [3.7,4.3,5.0,5.8,6.47]:
        p=tree.ray_cast(Vector((.8,y,z)),Vector((-1,0,0)),4)[0];assert p is not None;samples.append(p.x)
    flatness.append({'y':y,'x_samples':samples,'depth_variation':max(samples)-min(samples)})
out={'wall_shape_key':KEY,'sculpted_vertices':len(changed),'maximum_displacement_m':max(moves),'connections':connections,'lines':new_lines,
     'parallel_to_platform':True,'equal_line_spacing_m':abs(new_lines[1]['center'][0]-new_lines[0]['center'][0]),'stair_clearance_m':margin,
     'wall_flatness_samples':flatness,'preserved_objects':len(protected),'protected_changes':protected_changes,'existing_shape_keys_preserved':original_keys,'frame':[list(row) for row in F]}
(P/'verification.json').write_text(json.dumps(out,indent=2))
t=bpy.data.texts.new('fit_left_display_bay_wall.py');t.write(Path(__file__).read_text())
bpy.ops.wm.save_as_mainfile(filepath=str(P/'wall-fit-candidate.blend'),copy=True,compress=True)
result=out
