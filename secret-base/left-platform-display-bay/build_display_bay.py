"""Add the approved roofless display bay to the live left landing. No screen/text."""
import bpy, bmesh, math, json, hashlib
import numpy as np
from pathlib import Path
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

P=Path(__file__).resolve().parent
S=bpy.context.scene
FLOOR=bpy.data.objects['Front left | beveled rectangle landing']
FRAME=Matrix(json.loads((P.parent/'left-platform-support-fit/surface-before.json').read_text())['frame'])
INV=FRAME.inverted()
UP=Vector((0,0,1))
NAME='169 | Left platform display bay'
assert not bpy.data.collections.get(NAME), 'Already installed; edit existing objects instead'
if bpy.context.mode!='OBJECT': bpy.ops.object.mode_set(mode='OBJECT')

def signature(o):
    h=hashlib.sha256(repr(([list(r) for r in o.matrix_world],o.hide_render,o.hide_get(),o.parent.name if o.parent else None)).encode())
    if o.type=='MESH':
        a=np.empty(len(o.data.vertices)*3,dtype=np.float32);o.data.vertices.foreach_get('co',a);h.update(a.tobytes())
        h.update(repr([tuple(p.vertices) for p in o.data.polygons]).encode())
    return h.hexdigest()
before={o.name:signature(o) for o in S.objects}
(P/'before-hashes.json').write_text(json.dumps(before,indent=2))
COL=bpy.data.collections.new(NAME);S.collection.children.link(COL)
subs={}
for label in ['Armored channel supports','Wall skirting and lamps','Metal floor and three neon lines']:
    c=bpy.data.collections.new('169 | '+label);COL.children.link(c);subs[label]=c
C=subs['Armored channel supports']

def material(name,color,metal=.65,rough=.37,emission=0):
    m=bpy.data.materials.new('Left bay | '+name);m.use_nodes=True;m.diffuse_color=(*color,1)
    bs=m.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Metallic'].default_value=metal;bs.inputs['Roughness'].default_value=rough
    if emission:
        bs.inputs['Emission Color'].default_value=(*color,1);bs.inputs['Emission Strength'].default_value=emission
    return m
STEEL=bpy.data.materials['Metal | dark structural steel']
TRIM=material('beveled gunmetal armor',(.09,.115,.14),.78,.34)
DARK=material('deep channel inset',(.017,.025,.035),.62,.43)
EDGE=material('machined edge and bolt heads',(.21,.25,.29),.84,.32)
PANEL=material('satin graphite wall panels',(.038,.057,.077),.68,.40)
AMBER=material('warm amber lenses',(1,.29,.052),.1,.24,5)
CYAN=material('cyan floor diffuser',(.01,.55,.82),.1,.23,4)
TILES=[material('deck panel %d'%i,(.052+i*.002,.074+i*.002,.092+i*.002),.68,.39+i*.007) for i in range(3)]
made=[];support_meshes=[];support_records=[]

def mesh(name,verts,faces,mat,bevel=.006,mats=None):
    me=bpy.data.meshes.new('Left bay | '+name);me.from_pydata(verts,[],faces);me.update()
    for ma in mats or [mat]:me.materials.append(ma)
    bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
    o=bpy.data.objects.new(me.name,me);C.objects.link(o);o.parent=FLOOR;o.matrix_world=FRAME
    if bevel:
        b=o.modifiers.new('Machined edge radius','BEVEL');b.width=bevel;b.segments=3
        o.modifiers.new('Weighted corner normals','WEIGHTED_NORMAL')
    o['left_display_bay']=True;made.append(o);return o
FACES=[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
def box(name,center,t,n,u,width,depth,height,mat,bevel=.006):
    center,t,n,u=map(Vector,(center,t,n,u))
    return mesh(name,[center+t*x*width/2+n*y*depth/2+u*z*height/2 for z in [-1,1] for x,y in [(-1,-1),(1,-1),(1,1),(-1,1)]],FACES,mat,bevel)
def beam(name,a,b,width,depth,mat):
    a,b=Vector(a),Vector(b);u=(b-a).normalized();h=UP if abs(u.z)<.95 else Vector((0,1,0));t=u.cross(h).normalized();n=u.cross(t).normalized()
    return box(name,(a+b)/2,t,n,u,width,depth,(b-a).length,mat,.007)
def bolt(name,p,axis,r=.027):
    p,axis=Vector(p),Vector(axis).normalized();h=UP if abs(axis.z)<.9 else Vector((1,0,0));t=axis.cross(h).normalized();n=axis.cross(t).normalized()
    verts=[p+axis*z+t*(r*math.cos(i*math.pi/3))+n*(r*math.sin(i*math.pi/3)) for z in [0,.019] for i in range(6)]
    return mesh(name,verts,[tuple(reversed(range(6))),tuple(range(6,12))]+[(i,(i+1)%6,(i+1)%6+6,i+6) for i in range(6)],EDGE,.002)

deps=bpy.context.evaluated_depsgraph_get();ef=FLOOR.evaluated_get(deps)
floor_vs=[INV@ef.matrix_world@v.co for v in ef.data.vertices];TOP=max(v.z for v in floor_vs)
poly=[p for p in floor_vs if abs(p.z-TOP)<.0001];ctr=sum(poly,Vector())/len(poly);poly.sort(key=lambda p:math.atan2(p.y-ctr.y,p.x-ctr.x))
assert abs(max(p.y for p in poly)-13.701388)<.001
DECK=TOP+.014
rock=bpy.data.objects['150 | continuous cave with oblique carved rooms'];er=rock.evaluated_get(deps);rm=er.to_mesh()
tree=BVHTree.FromPolygons([INV@er.matrix_world@v.co for v in rm.vertices],[list(p.vertices) for p in rm.polygons]);er.to_mesh_clear()

def add_light(name,p,target,power,size,color):
    ld=bpy.data.lights.new('Left bay | '+name,'AREA');ob=bpy.data.objects.new(ld.name,ld);C.objects.link(ob);ob.parent=FLOOR
    wp=FRAME@Vector(p);wt=FRAME@Vector(target);rot=(wt-wp).to_track_quat('-Z','Y').to_matrix().to_4x4();rot.translation=wp;ob.matrix_world=rot
    ld.energy=power;ld.shape='DISK';ld.size=size;ld.color=color;ob['left_display_bay']=True;made.append(ob)

H=4.15;KNEE=1.20;TOE=.45
for index,(origin,t,n) in enumerate([
    ((.10,.95,DECK),(0,1,0),(1,0,0)),
    ((.10,3.65,DECK),(0,1,0),(1,0,0)),
    ((.10,10.70,DECK),(0,1,0),(1,0,0)),
    ((3.50,12.03,DECK),(1,0,0),(0,-1,0))],1):
    b,t,n=map(Vector,(origin,t,n));pre='support %02d '%index
    # The U section itself is continuous: front rails stand 0.20 m ahead of its inset web.
    profile=[(-.35,-.12),(.35,-.12),(.35,.20),(.17,.20),(.17,0),(-.17,0),(-.17,.20),(-.35,.20)]
    stations=[(.09,TOE),(KNEE,0),(H,0)]
    vs=[b+t*x+n*(d+y)+UP*z for z,d in stations for x,y in profile]
    fs=[tuple(reversed(range(8))),tuple(range(16,24))]
    for j in range(2):
        for k in range(8):fs.append((j*8+k,j*8+(k+1)%8,(j+1)*8+(k+1)%8,(j+1)*8+k))
    ob=mesh(pre+'continuous recessed U-channel',vs,fs,TRIM,.009,mats=[TRIM,DARK]);support_meshes.append(ob)
    for j in range(2):
        for k in [3,4,5]:ob.data.polygons[2+j*8+k].material_index=1
    ob['upper_section']='Straight vertical above lower outward bend';ob['recess_depth_m']=.20;ob['height_m']=H
    box(pre+'bolted floor anchor',b+n*.43+UP*.055,t,n,UP,.98,.82,.11,TRIM,.015)
    box(pre+'layered upper wall head',b+UP*(H-.10)-n*.025,t,n,UP,.81,.36,.24,TRIM,.012)
    # Separate edge plates preserve the central indentation; no cover bridges across it.
    for side in [-1,1]:
        x=side*.272
        box(pre+'upper edge armor',b+t*x+n*.217+UP*2.73,t,n,UP,.135,.032,2.43,TRIM,.007)
        a=b+t*x+n*(TOE+.21)+UP*.19;end=b+t*x+n*.21+UP*(KNEE-.03)
        axis=(end-a).normalized();out=t.cross(axis).normalized()
        if out.dot(n)<0:out=-out
        box(pre+'sloping foot edge armor',(a+end)/2,t,out,axis,.135,.038,(end-a).length,TRIM,.004)
        for z in [1.48,2.15,2.96,3.71]:bolt(pre+'flange fastener',b+t*x+n*.24+UP*z,n,.023)
        for z in [.3,.68,1.02]:
            d=TOE*(KNEE-z)/(KNEE-.09);bolt(pre+'lower flange fastener',b+t*x+n*(d+.242)+UP*z,n,.023)
        # Paired triangular gussets meet the anchor shoe and lower beam.
        x=side*.39
        tri=[b+t*x+n*.17+UP*.11,b+t*x+n*.78+UP*.11,b+t*x+n*.50+UP*.42]
        gv=[v+t*d for d in [-.027,.027] for v in tri]
        mesh(pre+'triangular foot gusset',gv,[(0,2,1),(3,4,5),(0,1,4,3),(1,2,5,4),(2,0,3,5)],TRIM,.006)
        for d in [.14,.70]:bolt(pre+'floor anchor bolt',b+t*(side*.405)+n*d+UP*.112,UP,.037)
    for z in [1.58,3.76]:
        box(pre+'recess lamp surround',b+n*.021+UP*z,t,n,UP,.14,.04,.54,DARK,.01)
        box(pre+'amber channel lens',b+n*.047+UP*z,t,n,UP,.069,.019,.44,AMBER,.008)
    box(pre+'top lamp visor',b+n*.20+UP*(H+.035),t,n,UP,.77,.55,.10,STEEL,.01)
    box(pre+'top amber downlight',b+n*.34+UP*(H-.025),t,n,UP,.57,.27,.022,AMBER,.005)
    add_light(pre+'warm downward wash',b+n*.49+UP*(H-.07),b+n*1.45+UP*.35,48,.52,(1,.48,.20))
    # Mount to actual evaluated rock, including the receding wall behind the stair pair.
    anchors=[]
    for z in [1.75,H-.23]:
        start=b+UP*z+n*.35;hit,normal,face,dist=tree.ray_cast(start,-n,6)
        assert hit is not None,(index,z)
        normal=normal.normalized()
        if normal.dot(n)<0:normal=-normal
        rockside=hit-normal*.07;front=b+UP*z-n*.08
        beam(pre+'rock standoff',rockside,front,.18,.20,STEEL)
        box(pre+'embedded rock anchor',hit,t,n,UP,.66,.18,.52,TRIM,.009)
        anchors.append({'surface':list(hit),'front':list(front),'length':(front-rockside).length})
    support_records.append({'index':index,'origin':list(b),'normal':list(n),'tangent':list(t),'height':H,'width':.70,'channel_depth':.20,'rock_anchors':anchors})

C=subs['Wall skirting and lamps']
for i in range(12):
    y=.25+(i+.5)*.947
    box('wall skirt panel %02d'%i,(.13,y,DECK+.36),(0,1,0),(1,0,0),UP,.923,.19,.70,PANEL,.009)
    box('wall skirt top cap %02d'%i,(.20,y,DECK+.735),(0,1,0),(1,0,0),UP,.948,.28,.07,TRIM,.008)
for j,y in enumerate([2.25,5.15,7.65,9.65]):
    b=Vector((.37,y,DECK+.66));box('wall lamp housing %d'%j,b,(0,1,0),(1,0,0),UP,.70,.10,.13,STEEL,.012)
    box('wall amber diffuser %d'%j,b+Vector((.056,0,0)),(0,1,0),(1,0,0),UP,.57,.018,.045,AMBER,.006)
    add_light('wall apron wash %d'%j,b+Vector((.065,0,0)),b+Vector((1.1,0,-.60)),12,.65,(1,.5,.23))
# Short, perpendicular return matches the fourth support's axis.
for j in range(4):
    x=.40+(j+.5)*.85
    box('return skirt panel %d'%j,(x,12.10,DECK+.36),(1,0,0),(0,-1,0),UP,.825,.18,.70,PANEL,.009)
    box('return skirt top cap %d'%j,(x,12.03,DECK+.735),(1,0,0),(0,-1,0),UP,.85,.27,.07,TRIM,.008)

C=subs['Metal floor and three neon lines']
# Clip a quiet metal-panel grid to the existing six-sided floor without touching its mesh.
def clip_polygon(points):
    for a,b in zip(poly,poly[1:]+poly[:1]):
        v=b-a;out=[]
        def signed(p):return v.x*(p.y-a.y)-v.y*(p.x-a.x)
        for p,q in zip(points,points[1:]+points[:1]):
            dp,dq=signed(p),signed(q)
            if dp>=0:out.append(p)
            if (dp>=0)!=(dq>=0):out.append(p+(q-p)*(dp/(dp-dq)))
        points=out
        if not points:break
    return points
tile_vs=[];tile_fs=[];tile_mats=[]
for ix in range(6):
    for iy in range(14):
        x0=ix*1.0077+.008;x1=(ix+1)*1.0077-.008;y0=iy*.979+.008;y1=(iy+1)*.979-.008
        points=clip_polygon([Vector((x0,y0,0)),Vector((x1,y0,0)),Vector((x1,y1,0)),Vector((x0,y1,0))])
        if len(points)<3:continue
        off=len(tile_vs);num=len(points)
        tile_vs.extend([(p.x,p.y,z) for z in [TOP+.001,DECK] for p in points])
        fs=[tuple(off+i for i in reversed(range(num))),tuple(off+num+i for i in range(num))]
        fs += [(off+i,off+(i+1)%num,off+(i+1)%num+num,off+i+num) for i in range(num)]
        tile_fs.extend(fs);tile_mats.extend([(ix+iy*2)%3]*len(fs))
tiles=mesh('quiet fitted metal floor panels',tile_vs,tile_fs,TILES[0],.003,mats=TILES)
for p,mi in zip(tiles.data.polygons,tile_mats):p.material_index=mi

angle=math.radians(18);along=Vector((-math.sin(angle),math.cos(angle),0));across=Vector((math.cos(angle),math.sin(angle),0));center=Vector((3.45,7.95,DECK))
line_records=[]
for i,k in enumerate([-1,0,1],1):
    p=center+across*(k*.95)
    box('floor line %d recessed metal bezel'%i,p+UP*.007,across,along,UP,.068,5.08,.022,DARK,.008)
    lens=box('floor line %d cyan inlay'%i,p+UP*.019,across,along,UP,.024,5.0,.011,CYAN,.004)
    lens['line_length_m']=5.;lens['equal_spacing_m']=.95;lens['angle_from_stair_run_degrees']=18
    line_records.append({'index':i,'a':list(p-along*2.5),'b':list(p+along*2.5),'center':list(p),'length':5.,'spacing':.95})
    for sign in [-1,1]:box('floor line %d end fitting'%i,p+along*(sign*2.528)+UP*.012,across,along,UP,.065,.038,.026,EDGE,.004)
COL['screen_reserved']='No screen geometry. Wall-space y=4.20..10.15, z=deck+1.10..deck+3.75 in documented platform frame.'
COL['screen_clear_width_m']=5.95;COL['screen_clear_height_m']=2.65
COL['floor_layout']='Three equal five-meter lines, 0.95 meter spacing, rotated 18 degrees relative to lower stair flight, entirely beyond stairs.'

bpy.context.view_layer.update()
changed=[name for name,value in before.items() if signature(bpy.data.objects[name])!=value]
assert not changed,changed
nonmanifold={}
for o in made:
    if o.type!='MESH':continue
    bm=bmesh.new();bm.from_mesh(o.data);bad=sum(not e.is_manifold for e in bm.edges);bm.free()
    if bad:nonmanifold[o.name]=bad
assert not nonmanifold,nonmanifold

# Project all walking surfaces onto the plan and measure their distance from each line.
stairs=bpy.data.collections['166 | Left bridge and right-turn steel stairs']
stair_vs=[INV@o.matrix_world@v.co for o in stairs.objects if o.type=='MESH' and ('tread' in o.name or 'half-height' in o.name) for v in o.data.vertices]
stair_max_y=max(p.y for p in stair_vs)
minimum_line_y=min(p[1] for rec in line_records for p in [rec['a'],rec['b']])
assert minimum_line_y-stair_max_y>.50
floor_tree=BVHTree.FromPolygons([INV@ef.matrix_world@v.co for v in ef.data.vertices],[list(p.vertices) for p in ef.data.polygons])
for rec in line_records:
    for j in range(21):
        p=Vector(rec['a']).lerp(Vector(rec['b']),j/20)
        hit=floor_tree.ray_cast(p+UP,-UP,2)[0];assert hit is not None
report={'objects_added':len(made),'supports':support_records,'lines':line_records,'frame':[list(r) for r in FRAME],
        'floor_height':TOP,'deck_finish_height':DECK,'screen_clear_width_m':5.95,'screen_clear_height_m':2.65,
        'stair_max_local_y':stair_max_y,'minimum_line_local_y':minimum_line_y,'line_to_stairs_plan_margin_m':minimum_line_y-stair_max_y,
        'all_preexisting_objects_unchanged':len(before),'nonmanifold_edges':nonmanifold,'screen_or_text_created':False}
(P/'verification.json').write_text(json.dumps(report,indent=2))
txt=bpy.data.texts.new('build_left_display_bay.py');txt.write(Path(__file__).read_text())
bpy.ops.wm.save_as_mainfile(filepath=str(P/'display-bay-candidate.blend'),copy=True,compress=True)
result=report
