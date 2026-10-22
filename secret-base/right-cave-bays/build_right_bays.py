"""Perspective reconstruction of the reference's two right-hand recessed cave bays."""
import argparse, ast, hashlib, json, math, sys
from pathlib import Path
import bpy, bmesh
import numpy as np
from mathutils import Matrix, Vector
from bpy_extras.object_utils import world_to_camera_view
from mathutils.bvhtree import BVHTree

P=Path(__file__).resolve().parent
ROOT=P.parents[1]
SOURCE=P.parent/'central-metal-platform/central-metal-platform.blend'
OUTPUT=P/'central-pillar-right-cave-bays.blend'
ap=argparse.ArgumentParser();ap.add_argument('--pass',dest='stage',type=int,default=1);ap.add_argument('--final',action='store_true');ap.add_argument('--samples',type=int,default=28);ap.add_argument('--width',type=int,default=1500);ap.add_argument('--verify',action='store_true');ap.add_argument('--verify-file',type=Path);a=ap.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
bpy.ops.wm.open_mainfile(filepath=str(SOURCE));bpy.context.preferences.filepaths.save_version=0
S=bpy.context.scene;S.name='Central pillar and two recessed right cave bays'
F=6.871178627
FRAME=Matrix.Translation((21.299999237,0,0))@Matrix.Rotation(-math.atan2(12,19),4,'Z');INV=FRAME.inverted()
src=ast.parse((P.parent/'central-metal-platform/build_metal_platform.py').read_text())
exec(compile(ast.Module(body=[n for n in src.body if isinstance(n,ast.FunctionDef) and n.name=='fingerprint'],type_ignores=[]),'protected_fingerprint','exec'),globals())
protected={o.name:fingerprint(o) for o in S.objects if o.type=='MESH' and not any(s in o.name for s in ['guardrail','perimeter post','post bolted foot','reinforcement strap','rim strap bolt','lamp armor','lamp cap','diffuser'])}
if a.verify:
    verified_file=a.verify_file or OUTPUT
    bpy.ops.wm.open_mainfile(filepath=str(verified_file));bpy.context.view_layer.update()
    changed=[n for n,h in protected.items() if n not in bpy.context.scene.objects or fingerprint(bpy.data.objects[n])!=h]
    scene=bpy.context.scene;dg=bpy.context.evaluated_depsgraph_get()
    spec=json.loads(scene['right_bay_geometry'])
    start_v,end_v=Vector(spec['start']),Vector(spec['end'])
    axis=(end_v-start_v).normalized();side=Vector((-axis.y,axis.x,0))
    obstacles=[o for o in scene.objects if o.type=='MESH' and (
        o.name.startswith(('Metal | continuous steel guardrail','Metal | guardrail polished top edge','Metal | perimeter post'))
        or any(c.name=='07 | Continuous approved-style cave wall' for c in o.users_collection))]
    hits=[];balcony_hits=[]
    supports=json.loads(scene.get('engineered_supports_revision','{"brackets":[]}'))
    anchor_distances=[float('inf') for _ in supports['brackets']]
    camera=scene.camera;frame=camera.data.view_frame(scene=scene)
    xs=[v.x for v in frame];ys=[v.y for v in frame];camera_origin=INV@camera.location
    balcony_rays=[]
    for px,py in [(895,174),(920,176),(975,178)]:
        d=camera.matrix_world.to_3x3()@Vector((min(xs)+(max(xs)-min(xs))*px/1199,min(ys)+(max(ys)-min(ys))*(1-py/654),frame[0].z))
        local_d=INV.to_3x3()@d
        target=FRAME@(camera_origin+local_d*((spec['upper_floor']-camera_origin.z)/local_d.z))
        balcony_rays.append((px,py,(target-camera.location).normalized(),(target-camera.location).length-.02))
    for ob in obstacles:
        ev=ob.evaluated_get(dg);me=ev.to_mesh()
        tree=BVHTree.FromPolygons([ob.matrix_world@v.co for v in me.vertices],[list(p.vertices) for p in me.polygons],all_triangles=False)
        for lane in [-.27,0,.27]:
            p=FRAME@(start_v-axis*.30+side*lane+Vector((0,0,.22)))
            q=FRAME@(end_v+axis*.02+side*lane+Vector((0,0,.22)))
            result=tree.ray_cast(p,(q-p).normalized(),(q-p).length)
            if result[0] is not None:hits.append({'object':ob.name,'lane':lane})
        if any(c.name=='07 | Continuous approved-style cave wall' for c in ob.users_collection):
            for index,bracket in enumerate(supports['brackets']):
                nearest=tree.find_nearest(FRAME@Vector(bracket['rock_anchor']))
                if nearest[0] is not None:anchor_distances[index]=min(anchor_distances[index],nearest[3])
            for px,py,direction,distance in balcony_rays:
                result=tree.ray_cast(camera.location,direction,distance)
                if result[0] is not None:balcony_hits.append({'object':ob.name,'reference_pixel':[px,py]})
        ev.to_mesh_clear()
    vehicle_objects=[o.name for o in scene.objects if any(t in o.name.lower() for t in ['batmobile','aircraft |','landing wheel','fuselage'])]
    stair_objects=[o.name for o in scene.objects if 'stair' in o.name.lower()]
    anchors_passed=len(anchor_distances)==6 and max(anchor_distances)<.025
    passed=not changed and not hits and not balcony_hits and not vehicle_objects and not stair_objects and anchors_passed
    report={'passed':passed,'protected_central_meshes':len(protected),'changed':changed,
            'bridge_clearance_obstructions':hits,'upper_balcony_rock_occlusions':balcony_hits,'vehicle_objects':vehicle_objects,
            'support_anchor_distances_from_rock':anchor_distances,'stair_objects':stair_objects,'camera_lens_mm':scene.camera.data.lens,
            'permitted_center_change':'New opening in right perimeter fence for the connecting bridge',
            'file':str(verified_file),'sha256':hashlib.sha256(verified_file.read_bytes()).hexdigest()}
    (P/('preview-verification.json' if a.verify_file else 'preservation.json')).write_text(json.dumps(report,indent=2));print('RIGHT_VERIFY',json.dumps(report),flush=True);assert report['passed'];sys.exit(0)

def collection(name):
    c=bpy.data.collections.new(name);S.collection.children.link(c);return c
LOW=collection('05 | Lower recessed garage and apron')
UP=collection('06 | Upper recessed aircraft hangar')
GEO=collection('07 | Continuous approved-style cave wall')
BRIDGE=collection('08 | Short straight bridge')
RIG=collection('10 | Wide perspective camera and cave practicals')
CUT=collection('11 | Editable cave excavation volumes')
DECK=LOW;RAIL=LOW
# Existing platform helpers are reused without executing their source scene edits.
names={'mesh','annulus','box','cylinder','radial_box'}
exec(compile(ast.Module(body=[n for n in src.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[]),'shared_metal_geometry','exec'),globals())
steel=bpy.data.materials['Metal | satin blue steel'];panel=bpy.data.materials['Metal | outer walkway alloy'];dark=bpy.data.materials['Metal | dark structural steel'];trim=bpy.data.materials['Metal | machined edge highlights'];grate=bpy.data.materials['Metal | brushed grating steel'];warm=bpy.data.materials['Metal | amber lamp diffusers']
def mat(name,col,metal=.5,rough=.45,emit=0):
    m=bpy.data.materials.new('Bays | '+name);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*col,1);p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=rough;p.inputs['Emission Color'].default_value=(*col,1);p.inputs['Emission Strength'].default_value=emit;return m
black=mat('recess black',(.006,.010,.013),.25,.72)
wallmat=mat('inset steel wall',(.027,.039,.046),.55,.49)
white=mat('cool strip light',(.63,.82,1),.0,.4,4)
yellow=mat('muted turntable alignment stripe',(.26,.23,.13),.6,.4)
cyan=mat('equipment status blue',(.018,.30,.5),.25,.35,.9)
red=mat('equipment status amber',(.6,.15,.027),.25,.4,.8)

def beam(name,p,q,r=.02,ma=dark,c=LOW):
    p,q=Vector(p),Vector(q);v=q-p;o=box(name,(p+q)/2,(2*r,2*r,v.length),ma,c,bevel=min(r*.2,.003));o.matrix_world=FRAME@Matrix.Translation((p+q)/2)@v.to_track_quat('Z','Y').to_matrix().to_4x4();return o
def prism(name,poly,zlo,zhi,ma=dark,c=LOW,bevel=.008):
    n=len(poly);vs=[(p[0],p[1],z) for z in [zlo,zhi] for p in poly];fs=[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)];return mesh(name,vs,fs,ma,c,bevel)
def area(name,p,target,power,size=2,color=(.59,.75,.91),size_y=.5):
    d=bpy.data.lights.new('Bays | '+name,'AREA');d.energy=power;d.color=color;d.shape='RECTANGLE';d.size=size;d.size_y=size_y
    o=bpy.data.objects.new(d.name,d);RIG.objects.link(o);o.location=FRAME@Vector(p);o.rotation_euler=(FRAME@Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();return o

# A 32 mm perspective, lowered viewing elevation, and matching principal point.
cam=bpy.data.objects.new('Bays | wide reference camera',bpy.data.cameras.new('Bays | wide reference camera'));RIG.objects.link(cam)
distance=19.25;elevation=math.radians(19.5)
cam.location=FRAME@Vector((0,-distance*math.cos(elevation),F+distance*math.sin(elevation)))
cam.rotation_euler=(FRAME@Vector((0,0,F))-cam.location).to_track_quat('-Z','Y').to_euler()
cam.data.type='PERSP';cam.data.lens=32;cam.data.sensor_width=36;cam.data.shift_y=.029;cam.data.clip_end=200;S.camera=cam
S.render.resolution_x=1199;S.render.resolution_y=654;S.render.resolution_percentage=100
bpy.context.view_layer.update()
def project(p):
    v=world_to_camera_view(S,cam,FRAME@Vector(p));return [v.x*1199,(1-v.y)*654]
def unproject(px,py,z):
    frame=cam.data.view_frame(scene=S);xs=[v.x for v in frame];ys=[v.y for v in frame];zz=frame[0].z
    direction=cam.matrix_world.to_3x3()@Vector((min(xs)+(max(xs)-min(xs))*px/1199,min(ys)+(max(ys)-min(ys))*(1-py/654),zz))
    origin=cam.location;direction=INV.to_3x3()@direction;origin=INV@origin
    return origin+direction*((z-origin.z)/direction.z)

Z=F-.04;H=F+2.80
lo_pixels=[(832,411),(856,378),(864,360),(1157,405),(1155,446),(1123,485),(1095,518),(982,477),(925,459),(866,451)]
up_pixels=[(844,180),(1105,184),(1137,124),(966,125),(933,148),(855,153)]
lp=[unproject(x,y,Z).xy for x,y in lo_pixels];hp=[unproject(x,y,H).xy for x,y in up_pixels]
center=unproject(1005,423,Z)
rear0,rear1=lp[2],lp[3];u=(rear1-rear0).normalized();v=Vector((-u.y,u.x));origin=(rear0+rear1)/2
ang=math.atan2(u.y,u.x);width=(rear1-rear0).length
def baypoint(xx,yy,zz):return Vector((origin.x+u.x*xx+v.x*yy,origin.y+u.y*xx+v.y*yy,zz))

prism('Garage | deep clipped structural apron',lp,Z-.36,Z-.055,dark)
prism('Garage | satin floor plate',lp,Z-.06,Z,panel)
prism('Hangar | heavy inset slab',hp,H-.32,H-.04,dark,UP)
prism('Hangar | satin flight deck',hp,H-.04,H,panel,UP)
# Broad manufactured floor seams follow the actual angled bay axes.
def line_clip(poly,p,q):
    # Keep segments inside any simple planar polygon; midpoint ray parity.
    ts=[0.,1.];dv=q-p
    def cross(a,b):return a.x*b.y-a.y*b.x
    for aa,bb in zip(poly,poly[1:]+poly[:1]):
        e=bb-aa;den=cross(dv,e)
        if abs(den)<1e-8:continue
        t=cross(aa-p,e)/den;s=cross(aa-p,dv)/den
        if 0<t<1 and 0<=s<=1:ts.append(t)
    ts=sorted(set(ts));result=[]
    def inside(point):
        hit=False
        for aa,bb in zip(poly,poly[1:]+poly[:1]):
            if (aa.y>point.y)!=(bb.y>point.y) and point.x<(bb.x-aa.x)*(point.y-aa.y)/(bb.y-aa.y)+aa.x:hit=not hit
        return hit
    for aa,bb in zip(ts,ts[1:]):
        if inside(p+dv*((aa+bb)/2)):result.append((p+dv*aa,p+dv*bb))
    return result
for along in range(-6,8):
    for transverse in [False,True]:
        axis=u if transverse else v;side=v if transverse else u;p0=origin+side*(along*.85)-axis*14;p1=p0+axis*28
        for aa,bb in line_clip(lp,p0,p1):beam('Garage | broad panel seam',(*aa,Z+.001),(*bb,Z+.001),.004,black)

# Flush circular vehicle turntable and concentric metal bands, not a raised table.
for ri,ro,ma,top in [(0.001,1.73,steel,.008),(1.736,1.78,black,.005),(1.785,1.804,trim,.009),(1.81,1.99,panel,.005),(1.999,2.018,yellow,.008),(2.03,2.062,trim,.008),(2.07,2.20,panel,.004),(2.205,2.218,black,.006)]:
    o=annulus('Garage | flush turntable ring',ri*.90,ro*.90,Z-.025,Z+top,ma,c=LOW)
    o.matrix_world=FRAME@Matrix.Translation((center.x,center.y,0))
for i in range(12):
    t=i*math.tau/12
    p=center+Vector((math.cos(t)*1.926,math.sin(t)*1.926,.010));cylinder('Garage | ring bolt',p,.013,.006,dark)

def wall_segment(name,aa,bb,z,height,c=LOW):
    aa,bb=Vector(aa),Vector(bb);length=(bb-aa).length;axis=(bb-aa).normalized();theta=math.atan2(axis.y,axis.x);middle=(aa+bb)/2
    box(name+' | lining',(*middle,z+height/2),(length,.16,height),wallmat,c,theta,.012)
    count=max(2,round(length/.86))
    for j in range(count+1):
        pp=aa.lerp(bb,j/count);beam(name+' | vertical frame',(*pp,z+.03),(*pp,z+height),.030,trim,c)
    for zz in [z+.08,z+height-.04]:beam(name+' | horizontal frame',(*aa,zz),(*bb,zz),.026,dark,c)
    for j in range(count):
        p=aa.lerp(bb,(j+.18)/count);q=aa.lerp(bb,(j+.82)/count);normal=Vector((axis.y,-axis.x))*.115
        if j%2==0:
            beam(name+' | recessed fixture',(*(p+normal),z+height-.23),(*(q+normal),z+height-.23),.026,white,c)
    return theta
rear_segments=[baypoint(-width/2,0,Z).xy,baypoint(-.65,.22,Z).xy,baypoint(1.02,.10,Z).xy,baypoint(width/2,0,Z).xy]
for index,(aa,bb) in enumerate(zip(rear_segments,rear_segments[1:])):wall_segment('Garage | faceted back service wall %d'%index,aa,bb,Z,1.72)
wall_segment('Garage | right return',rear1,lp[4],Z,1.72)
wall_segment('Garage | left return',rear0,lp[1],Z,1.65)
# Steel arch ribs sit within the excavated stone; there is no standalone roof.
def arch_shape(w,base,top):return [(-w/2,base),(-w/2,top-.40),(-w/2+.48,top),(w/2-.48,top),(w/2,top-.35),(w/2,base)]
for yy in [-.22,.9]:
    pts=[baypoint(x,yy,z) for x,z in arch_shape(width+.20,Z,Z+2.02)]
    for pp,qq in zip(pts,pts[1:]):beam('Garage | inset angled arch frame',pp,qq,.046,dark)
area('garage overhead pool',baypoint(0,-.45,Z+1.97),center+Vector((0,0,.1)),240,4.5,size_y=1.0)
area('garage soft side fill',baypoint(-width/2+.3,-1,Z+1.45),center+Vector((0,0,.4)),90,1.2)

# Existing approved geology becomes a normalized reusable stone volume.
rock=bpy.data.objects['Central rock mound | continuous cross-column extrusions']
dg=bpy.context.evaluated_depsgraph_get();ev=rock.evaluated_get(dg);base_mesh=bpy.data.meshes.new_from_object(ev)
zmin=min((INV@(rock.matrix_world@vv.co)).z for vv in base_mesh.vertices)
for vv in base_mesh.vertices:
    vv.co=INV@(rock.matrix_world@vv.co);vv.co.z-=zmin
base_mesh.update()
def rock_mass(name,pos,scale,rot=0):
    ob=bpy.data.objects.new('Bays | '+name,base_mesh);GEO.objects.link(ob);ob.matrix_world=FRAME@Matrix.Translation(pos)@Matrix.Rotation(rot,4,'Z')@Matrix.Diagonal((*scale,1));return ob
def stacked_rock(name,xy,scales,rotation):
    # Preserve the approved pillar's vertical chunk scale instead of stretching
    # its short fractures into continuous cliff-height flutes.
    pieces=[]
    for i,zz in enumerate([-6.,.6,7.1]):
        pieces.append(rock_mass(name+' | stratum %d'%i,(xy[0]+[.08,-.10,.16][i],xy[1]+[0,.25,-.15][i],zz),(scales[0]*[1.02,.95,1.06][i],scales[1]*[1.0,1.03,.94][i],1.36),rotation+[.06,-.13,.14][i]))
    root=pieces[0];root.data=root.data.copy();bpy.context.view_layer.objects.active=root
    for other in pieces[1:]:
        mod=root.modifiers.new('Continuous overlapping rock strata','BOOLEAN');mod.operation='UNION';mod.solver='EXACT';mod.object=other
        bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(other,do_unlink=True)
    return root
masses=[stacked_rock('continuous cave wall',(10.1,6.0),(1.95,3.2),.10),
        stacked_rock('left broken cave return',(5.4,4.0),(.57,1.95),-.16),
        stacked_rock('right overlapping cave cheek',(12.25,1.0),(.72,1.5),.32)]

def screen_volume(name,pixels,near=8,far=65):
    # A three-dimensional tapered cutter controls the visible rock contour.
    # This remains actual excavated geometry, with side surfaces and full depth.
    fr=cam.data.view_frame(scene=S);xs=[p.x for p in fr];ys=[p.y for p in fr];zz=fr[0].z
    rays=[Vector((min(xs)+(max(xs)-min(xs))*x/1199,min(ys)+(max(ys)-min(ys))*(1-y/654),zz))/(-zz) for x,y in pixels]
    vs=[tuple(ray*depth) for depth in [near,far] for ray in rays];n=len(rays)
    faces=[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    ob=mesh(name,vs,faces,black,CUT);ob.matrix_world=cam.matrix_world.copy();ob.hide_render=True;ob.hide_set(True);ob.display_type='WIRE';return ob
contour=[(993,-160),(969,-5),(953,28),(962,54),(932,80),(922,117),(901,149),(883,180),(889,201),(856,218),(837,244),(844,274),(826,302),(819,337),(827,359),(808,383),(820,421),(822,454),(807,494),(826,535),(821,575),(846,615),(872,690),(880,1000),(2000,1000),(2000,-160)]
outline=screen_volume('Cave | reference-shaped broken outer contour',contour)
for ob in masses:
    mod=ob.modifiers.new('Stepped cave boundary','BOOLEAN');mod.operation='INTERSECT';mod.solver='EXACT';mod.object=outline
def excavation(name,section,depths,transform):
    n=len(section);vs=[(xx,yy,zz) for yy in depths for xx,zz in section];fs=[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    cut=mesh(name,vs,fs,black,CUT);cut.matrix_world=FRAME@transform;cut.hide_render=True;cut.hide_set(True);cut.display_type='WIRE'
    for ob in masses:
        mod=ob.modifiers.new(name,'BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cut
    return cut
lowT=Matrix.Translation((origin.x,origin.y,0))@Matrix.Rotation(ang,4,'Z')
lowsec=[(-width/2-.32,Z-.09),(-width/2-.32,Z+1.66),(-width/2+.20,Z+2.22),(width/2-.05,Z+2.22),(width/2+.5,Z+1.67),(width/2+.5,Z-.09)]
lowercut=excavation('Garage | vaulted rock excavation',lowsec,[-9,1.05],lowT)
lowmask=screen_volume('Garage | irregular overlapping rock lip',[(843,372),(850,326),(871,293),(919,277),(979,290),(1040,298),(1120,320),(1158,335),(1165,383),(1139,445),(1120,487),(1095,525),(980,481),(866,451),(832,432)])
mod=lowercut.modifiers.new('Rock overlaps garage entrance','BOOLEAN');mod.operation='INTERSECT';mod.solver='EXACT';mod.object=lowmask

# A narrow shadow reveal lets the apron project beyond the load-bearing cliff.
# Brackets connect its front beam back into the stone instead of floating.
for edge_index in range(6,9):
    aa,bb=lp[edge_index],lp[edge_index+1]
    along=(bb-aa).normalized();inside=Vector((along.y,-along.x))
    shape=[aa-inside*.25,bb-inside*.25,bb+inside*.62,aa+inside*.62]
    undercut=prism('Garage | apron undercroft cut',shape,Z-1.02,Z-.32,black,CUT,0)
    undercut.hide_render=True;undercut.hide_set(True);undercut.display_type='WIRE'
    for ob in masses:
        mod=ob.modifiers.new('Recess behind projecting apron','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=undercut
    beam('Garage | apron underside edge girder',(*aa,Z-.38),(*bb,Z-.38),.052,dark)
    for t in [.20,.75]:
        tip=aa.lerp(bb,t);anchor=tip+inside*.80
        beam('Garage | rock-anchored diagonal bracket',(*tip,Z-.36),(*anchor,Z-1.12),.040,dark)
        beam('Garage | rock-anchored horizontal bracket',(*tip,Z-.36),(*anchor,Z-.36),.042,dark)

# Upper bay has a horizontal projected balcony edge and considerable depth.
hu=(hp[1]-hp[0]).normalized();hv=Vector((-hu.y,hu.x));ho=(hp[0]+hp[1])/2;hang_width=(hp[1]-hp[0]).length;hang_angle=math.atan2(hu.y,hu.x)
def hangpoint(xx,yy,zz):return Vector((ho.x+hu.x*xx+hv.x*yy,ho.y+hu.y*xx+hv.y*yy,zz))
uppersec=[(-12,H-.10),(-12,H+10),(12,H+10),(12,H-.10)]
uppercut=excavation('Hangar | deep rock arch excavation',uppersec,[-10,16.0],Matrix.Translation((ho.x,ho.y,0))@Matrix.Rotation(hang_angle,4,'Z'))
archmask=screen_volume('Hangar | irregular rock mouth',[(842,189),(842,150),(925,150),(931,140),(942,117),(944,80),(964,52),(978,30),(1008,26),(1040,17),(1090,18),(1107,43),(1118,72),(1130,92),(1145,119),(1134,143),(1105,189)])
mod=uppercut.modifiers.new('Rock overlaps aircraft entrance','BOOLEAN');mod.operation='INTERSECT';mod.solver='EXACT';mod.object=archmask
porch_outline=[hp[0]-hv*.17,hp[1]-hv*.17]+hp[2:]
porchcut=prism('Hangar | clear front balcony',porch_outline,H-.40,H+.67,black,CUT,0);porchcut.hide_render=True;porchcut.hide_set(True);porchcut.display_type='WIRE'
for ob in masses:
    mod=ob.modifiers.new('Continuous exposed hangar balcony','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=porchcut
# Extend the far-right connected cliff toward the viewer so the apron ends
# against rock, with the approved pillar's connected broad outcrop style.
forward_wall=stacked_rock('forward right cave wall',(9.6,-5.2),(1.45,2.0),-.30)
forward_boundary=screen_volume('Cave | forward right return inner contour',[
    (1187,-200),(1183,240),(1170,326),(1166,400),(1147,458),
    (1123,487),(1100,503),(1090,525),(1093,568),(1086,654),
    (1110,900),(1600,900),(1600,-200)
])
mod=forward_wall.modifiers.new('Natural angled foreground wall boundary','BOOLEAN');mod.operation='INTERSECT';mod.solver='EXACT';mod.object=forward_boundary
masses.append(forward_wall)

wall_segment('Hangar | rear wall',hp[3],hp[2],H,3.02,UP)
wall_segment('Hangar | side service wall',hp[2],hp[1],H,2.65,UP)
def on_hangar_portal(px,py,depth):
    target=hangpoint(0,depth,H);normal=Vector((hv.x,hv.y,0));origin_ray=INV@cam.location
    p=unproject(px,py,H);ray=p-origin_ray
    return origin_ray+ray*((target-origin_ray).dot(normal)/ray.dot(normal))
portal_pixels=[(938,169),(945,123),(951,82),(983,39),(1009,34),(1040,27),(1086,28),(1110,75),(1135,119)]
for depth in [2.25,3.15,5.1]:
    pts=[on_hangar_portal(x,y,depth) for x,y in portal_pixels]
    for p,q in zip(pts,pts[1:]):beam('Hangar | embedded polygonal arch rib',p,q,.035,dark,UP)
beam('Hangar | recessed ceiling light',on_hangar_portal(1018,38,4.0),on_hangar_portal(1070,38,4.0),.025,white,UP)
jetcenter=unproject(1015,147,H)
area('hangar ceiling beam',hangpoint(0,3.2,H+2.87),jetcenter,440,2.5,size_y=.7)
area('hangar front soft return',hangpoint(-1,-1,H+1.9),jetcenter,90,2.0)
area('hangar interior overhead pool',jetcenter+Vector((0,-1.0,2.15)),jetcenter+Vector((0,0,.4)),260,2.8,(.70,.83,.97),1.4)

def guard(name,aa,bb,z,c=LOW,posts=True):
    aa,bb=Vector((*aa,z)),Vector((*bb,z));length=(bb-aa).length
    for h in [.20,.43]:beam(name+' | rail',aa+Vector((0,0,h)),bb+Vector((0,0,h)),.014,dark,c)
    beam(name+' | toe plate',aa+Vector((0,0,.018)),bb+Vector((0,0,.018)),.025,dark,c)
    if posts:
        for j in range(max(1,math.ceil(length/.56))+1):
            p=aa.lerp(bb,j/max(1,math.ceil(length/.56)));beam(name+' | post',p,p+Vector((0,0,.445)),.023,dark,c)
for aa,bb in [(lp[i],lp[i+1]) for i in range(6,9)]:guard('Garage | exposed apron guard',aa,bb,Z)
guard('Hangar | front balcony guard',hp[0],hp[1],H,UP)
beam('Hangar | continuous balcony front beam',(*hp[0],H-.19),(*hp[1],H-.19),.060,dark,UP)
beam('Hangar | balcony machined lip',(*hp[0],H+.006),(*hp[1],H+.006),.022,trim,UP)
for t in [.16,.34,.68,.88]:
    tip=hp[0].lerp(hp[1],t);root=tip+hv*.70
    beam('Hangar | balcony bracket into cliff',(*tip,H-.29),(*root,H-.85),.040,dark,UP)
# Small upper control tower at the left end of the balcony.
tower=hangpoint(-hang_width/2+.40,1.0,H)
box('Hangar | control tower body',tower+Vector((0,0,.78)),(.70,.75,1.56),wallmat,UP,hang_angle,.016)
glass=mat('control tower glass',(.03,.11,.15),.38,.24)
for zz in [H+.95,H+1.30]:box('Hangar | tower window',Vector((tower.x,tower.y-.386,zz)),(.62,.022,.23),glass,UP,hang_angle)
box('Hangar | tower crown',tower+Vector((0,0,1.62)),(.93,.89,.10),dark,UP,hang_angle)

# Workbenches, tool panels, lockers and movable service equipment give the
# lower room the same working-garage content hierarchy as the reference.
for j,xx in enumerate([-width*.34,-.20,width*.31]):
    p=baypoint(xx,-.36,Z)
    box('Garage | service bench worktop',p+Vector((0,0,.60)),(1.04,.43,.065),steel,LOW,ang)
    box('Garage | drawer cabinet',p+Vector((0,0,.29)),(.72,.37,.56),wallmat,LOW,ang)
    for z in [.16,.30,.44]:
        q=baypoint(xx,-.555,Z+z);box('Garage | drawer front',q,(.66,.015,.115),panel,LOW,ang)
        box('Garage | drawer pull',q+Vector((0,-.018,.023)),(.23,.025,.014),trim,LOW,ang)
    board=baypoint(xx,-.08,Z+1.15)
    box('Garage | wall equipment board',board,(1.08,.045,.68),dark,LOW,ang)
    for k in range(7):
        q=baypoint(xx-.42+k*.13,-.115,Z+1.12+(k%3)*.055)
        beam('Garage | hanging service tool',q,q+Vector((0,0,.15+(k%2)*.06)),.014,trim)
        box('Garage | tool head',q+Vector((0,0,.15+(k%2)*.06)),(.045,.023,.035),trim,LOW,ang)
    for k in range(3):box('Garage | worktop equipment',baypoint(xx-.33+k*.29,-.36,Z+.69),(.16,.16,.13),[dark,trim,wallmat][k],LOW,ang)
for xx in [-width*.43,width*.45]:
    p=baypoint(xx,-.48,Z)
    box('Garage | tall equipment locker',p+Vector((0,0,.67)),(.40,.46,1.34),wallmat,LOW,ang)
    for k in range(6):box('Garage | locker louver',baypoint(xx,-.72,Z+.45+k*.075),(.30,.014,.018),dark,LOW,ang)
    box('Garage | locker status',baypoint(xx+.12,-.735,Z+1.12),(.025,.015,.055),red,LOW,ang)
for xx in [-width*.38,-width*.22]:
    base=baypoint(xx,-1.05,Z)
    box('Garage | hydraulic service jack',base+Vector((0,0,.075)),(.22,.40,.15),dark,LOW,ang)
    beam('Garage | jack lifting arm',base+Vector((0,0,.1)),base+Vector((.10,0,.56)),.027,trim)
    beam('Garage | jack top support',base+Vector((.02,0,.56)),base+Vector((.20,0,.56)),.022,dark)
    for sign in [-1,1]:cylinder('Garage | jack roller',base+Vector((sign*.115,-.1,.06)),.055,.032,black,LOW,Vector((1,0,0)))
for k in range(4):
    pp=hangpoint(-hang_width*.15+k*.45,4.7,H+.28);box('Hangar | logistics case',pp,(.35,.40,.55),wallmat,UP,hang_angle)
# A low maintenance gantry remains behind the apron, inside the upper room.
gantry_a=on_hangar_portal(991,126,6.4);gantry_b=on_hangar_portal(1091,127,6.4)
for point in [gantry_a,gantry_b]:
    beam('Hangar | recessed service gantry upright',Vector((point.x,point.y,H)),point,.026,dark,UP)
beam('Hangar | recessed service gantry header',gantry_a,gantry_b,.039,wallmat,UP)
for j in range(12):
    p=gantry_a.lerp(gantry_b,(j+.10)/12);q=gantry_a.lerp(gantry_b,(j+.35)/12)
    beam('Hangar | restrained crane identification stripe',p-Vector((0,.041,.005)),q-Vector((0,.041,.005)),.015,yellow,UP)
for xx in [-.80,1.6]:
    beam('Hangar | recessed floor guide',hangpoint(xx,2.0,H+.004),hangpoint(xx,7.5,H+.004),.012,trim,UP)

# Straight short bridge departs through an actual opening in the center fence.
gate_hint=unproject(741,391,F);theta=math.atan2(gate_hint.y,gate_hint.x)
start=Vector((math.cos(theta)*2.64,math.sin(theta)*2.64,F));end=unproject(841,417,Z)
axis=end-start;axis.z=0;axis.normalize();side=Vector((-axis.y,axis.x,0));length=(end-start).xy.length;bridge_width=.88
opening=box('Center | right bridge opening',Vector((math.cos(theta)*2.74,math.sin(theta)*2.74,F+.29)),(.82,1.02,.83),black,CUT,theta,.0);opening.hide_render=True;opening.hide_set(True)
for ob in list(S.objects):
    if ob.name.startswith(('Metal | continuous steel guardrail','Metal | guardrail polished top edge')):
        mod=ob.modifiers.new('Right bridge gate','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=opening
    elif ob.type=='MESH' and any(s in ob.name for s in ['perimeter post','post bolted foot','reinforcement strap','rim strap bolt','lamp armor','lamp cap','diffuser']):
        p=INV@ob.matrix_world.translation
        if abs(math.atan2(p.y,p.x)-theta)<.20:bpy.data.objects.remove(ob,do_unlink=True)
for j in range(max(1,math.ceil(length/.19))):
    n=max(1,math.ceil(length/.19));p=start.lerp(end,j/n);q=start.lerp(end,(j+1)/n)
    vs=[tuple(r+Vector((0,0,drop))) for drop in [-.12,.006] for r in [p-side*bridge_width/2,q-side*bridge_width/2,q+side*bridge_width/2,p+side*bridge_width/2]]
    mesh('Bridge | continuous metal tread',vs,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],panel,BRIDGE,.003)
for sign in [-1,1]:
    p=start+side*sign*(bridge_width/2-.025);q=end+side*sign*(bridge_width/2-.025)
    for h in [.20,.43]:beam('Bridge | joined steel rail',p+Vector((0,0,h)),q+Vector((0,0,h)),.014,dark,BRIDGE)
    beam('Bridge | outer side girder',p-Vector((0,0,.13)),q-Vector((0,0,.13)),.07,dark,BRIDGE)
    for j in range(math.ceil(length/.48)+1):
        r=p.lerp(q,j/math.ceil(length/.48));beam('Bridge | fitted post',r,r+Vector((0,0,.445)),.023,dark,BRIDGE)

# The outer railing terminates against the forward cave return. No stairs.
rail_end=Vector((*lp[6],Z))
rail_direction=(Vector((*lp[6],Z))-Vector((*lp[7],Z))).normalized()
for h in [.20,.43]:
    beam('Garage | rail socket into right wall',rail_end+Vector((0,0,h)),rail_end+rail_direction*{.20:.065,.43:.225}[h]+Vector((0,0,h)),.018,dark,LOW)

# Dry depth cues: dark backing, cool focused cave practicals, and restrained haze.
for ob in bpy.data.collections['04 | Presentation cameras and studio lights'].objects:
    if ob.type=='LIGHT':ob.data.energy*=.62
S.world.node_tree.nodes['Background'].inputs[0].default_value=(.011,.018,.024,1);S.world.node_tree.nodes['Background'].inputs[1].default_value=.17
area('upper rock reveal',(5,-1,14),(8,5,10),540,5.0,size_y=4)
area('lower cliff soft fill',(6,-7,5),(8,1,4),390,6.0,size_y=5)
area('central ceiling pool',(-1,0,13),(0,0,F),600,3.4,size_y=2)
mist=mat('dry cave haze',(.02,.03,.04),0,.9);nt=mist.node_tree;nt.nodes.clear();out=nt.nodes.new('ShaderNodeOutputMaterial');vol=nt.nodes.new('ShaderNodeVolumePrincipled');vol.inputs['Density'].default_value=.008;vol.inputs['Color'].default_value=(.22,.32,.42,1);vol.inputs['Anisotropy'].default_value=.25;nt.links.new(vol.outputs['Volume'],out.inputs['Volume'])
box('Atmosphere | dry cave volume',(4,8,7),(42,52,35),mist,RIG,bevel=0)

# Finish the local rock bearing and engineered lower-deck connections.
sys.path.insert(0,str(P))
from refine_platform_supports import apply_support_revision, render_support_closeup
support_report=apply_support_revision(S,{'lower_floor_polygon':[list(p) for p in lp],'lower_floor_height':Z})
bpy.context.view_layer.update()
assert protected=={n:fingerprint(bpy.data.objects[n]) for n in protected},'Finished central pillar changed'
bpy.data.orphans_purge(do_local_ids=True,do_linked_ids=False,do_recursive=True)
# Use the available local GPU; keep a CPU fallback for other machines.
prefs=bpy.context.preferences.addons['cycles'].preferences
try:
    prefs.compute_device_type='METAL';prefs.get_devices()
    for device in prefs.devices:device.use=(device.type=='METAL')
    S.cycles.device='GPU' if any(device.type=='METAL' for device in prefs.devices) else 'CPU'
except Exception:S.cycles.device='CPU'
S.cycles.samples=a.samples;S.cycles.use_denoising=True;S.cycles.max_bounces=8;S.cycles.volume_bounces=1
S.view_settings.exposure=.10;S.render.resolution_x=a.width;S.render.resolution_y=round(a.width*654/1199);S.render.resolution_percentage=100;S.render.image_settings.file_format='PNG'
S['right_bay_geometry']=json.dumps({'start':list(start),'end':list(end),'bridge_width':bridge_width,'lower_floor':Z,'upper_floor':H})
tag='right-bays' if a.final else 'preview-%02d'%a.stage;outpath=OUTPUT if a.final else P/(tag+'.blend')
S.render.filepath=str(P/(tag+'-overview.png'))
text=bpy.data.texts.new('build_right_bays.py');text.write(Path(__file__).read_text())
text=bpy.data.texts.new('refine_platform_supports.py');text.write((P/'refine_platform_supports.py').read_text())
S['revision']='Approved middle island, wide 32mm perspective, two deep bays excavated into one right wall. Dry cave, no vehicles or stairs; right wall reaches the apron railing.'
bpy.ops.wm.save_as_mainfile(filepath=str(outpath),compress=True);bpy.ops.render.render(write_still=True)
audit={'source':str(SOURCE),'output':str(outpath),'protected_center_meshes':len(protected),'camera_lens_mm':32,'camera_horizontal_fov_degrees':math.degrees(cam.data.angle_x),'lower_floor_height':Z,'upper_floor_height':H,'lower_floor_polygon':[list(p) for p in lp],'upper_floor_polygon':[list(p) for p in hp],'turntable_center':list(center),'turntable_outer_radius':2.218*.90,'turntable_projection':project(center),'upper_floor_center_projection':project(jetcenter),'bridge_start':list(start),'bridge_end':list(end),'bridge_world_length':length,'terrain_source':'Evaluated mesh produced by build_balanced_mound.py, reused by four connected cave masses, including the forward right return, with two excavated bay volumes','water_added':False,'vehicles_added':False,'stairs_added':False,'right_wall_extended_toward_camera':True}
audit['vehicles']=[]
audit['engineered_supports']=support_report
(P/(tag+'-audit.json')).write_text(json.dumps(audit,indent=2));print('RIGHT_RESULT',json.dumps(audit),flush=True)
if a.final:
    # A native Blender crop retains the calibrated perspective in the detail.
    S.render.resolution_x=2400;S.render.resolution_y=round(2400*654/1199)
    S.render.use_border=True;S.render.use_crop_to_border=True
    S.render.border_min_x=.667;S.render.border_max_x=1.0
    S.render.border_min_y=.06;S.render.border_max_y=.99
    S.render.filepath=str(P/'right-bays-detail.png')
    bpy.ops.render.render(write_still=True)
    S.render.use_border=False;S.render.use_crop_to_border=False
    S.render.resolution_x=a.width;S.render.resolution_y=round(a.width*654/1199)
    S.render.filepath=str(P/'right-bays-overview.png')
    render_support_closeup(S,P/'right-bays-supports.png',a.samples)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(outpath),compress=True)
