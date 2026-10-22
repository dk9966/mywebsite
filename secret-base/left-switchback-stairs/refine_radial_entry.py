"""Make the upper approach radial; preserve the square landing and lower flight.

Run after build_stairs.py in the aligned live scene. The added triangle shares
the existing landing entrance edge, so no landing or lower-flight mesh moves.
"""
import ast
import array
import hashlib
import json
import math
from pathlib import Path
import bpy
import bmesh
from mathutils import Vector, Matrix

P=Path(__file__).resolve().parent
S=bpy.context.scene
COL=bpy.data.collections['166 | Left bridge and right-turn steel stairs']
TAG='left_switchback_generated'
UP=Vector((0,0,1))
base=json.loads((P/'build-report.json').read_text())
fixed_frame=bpy.data.objects['Left stairs | half-height right-turn landing frame'].matrix_world.copy()
fixed_inv=fixed_frame.inverted()
H,MID,L=base['upper_z'],base['mid_z'],base['lower_z']
HALF=.67
BAY=.56
BRIDGE=1.12
OLD_A=4.18
COUNT=14
STEEL=bpy.data.materials['Metal | dark structural steel']
FRAME_MAT=bpy.data.materials['Bridge | blue gunmetal panel frames']
GRATE=bpy.data.materials['Bridge | graphite open steel grating']
WARM=bpy.data.materials['Metal | amber lamp diffusers']
MADE=[]

def signature(ob):
    h=hashlib.sha256(repr([list(r) for r in ob.matrix_world]).encode())
    if ob.type=='MESH':
        values=array.array('f',[0])*(len(ob.data.vertices)*3)
        ob.data.vertices.foreach_get('co',values)
        h.update(values.tobytes())
        h.update(repr([tuple(p.vertices) for p in ob.data.polygons]).encode())
    return h.hexdigest()

def upper_part(ob):
    n=ob.name
    if ob.get('radial_triangle_generated'):
        return True
    if any(n.startswith('Left stairs | '+prefix) for prefix in
           ['upper bridge','bridge cross bearer','bridge underside diagonal',
            'curved entry','first flight','hidden center guardrail entrance cutter']):
        return True
    if n.startswith('Left stairs | continuous '):
        return int(n.rsplit('section ',1)[1])<3
    if n.startswith(('Left stairs | bolted guardrail upright','Left stairs | guardrail mounting shoe')):
        ps=[fixed_inv@ob.matrix_world@v.co for v in ob.data.vertices]
        return sum(p.x for p in ps)/len(ps)<OLD_A-.05
    if any(n.startswith('Left stairs | warm lamp %02d'%i) for i in (0,1)):
        return True
    if any(n.startswith('Left stairs | warm marker %02d'%i) for i in (0,1)):
        return True
    return False

protected={o.name:signature(o) for o in COL.objects if not upper_part(o)}
for n in ['Front left | beveled rectangle landing']:
    protected[n]=signature(bpy.data.objects[n])

# The new foot edge is a chord about the center platform. One endpoint stays
# on the original square corner, and the other forms a small outside triangle.
q0=fixed_frame@Vector((OLD_A,-HALF,MID))
q1=fixed_frame@Vector((OLD_A,HALF,MID))
q0.z=q1.z=MID
center=bpy.data.objects['Rig | middle radius'].matrix_world.translation.copy()
center.z=MID
corner_radius=(q0-center).length
angle=2*math.asin((2*HALF)/(2*corner_radius))
tips=[center+Matrix.Rotation(sign*angle,3,'Z')@(q0-center) for sign in (-1,1)]
tip=min(tips,key=lambda p:(p-q1).length)
assert (fixed_inv@tip).x<OLD_A, 'The added triangle must lie outside the square landing.'
foot=(q0+tip)*.5
D=(foot-center).normalized()
RIGHT=Vector((D.y,-D.x,0))
radius=3.705
distance=math.sqrt(radius**2-HALF**2)-.025
origin=center+D*distance
origin.z=H
FRAME=Matrix(((D.x,RIGHT.x,0,origin.x),
              (D.y,RIGHT.y,0,origin.y),(0,0,1,0),(0,0,0,1)))
INV=FRAME.inverted()
END=(foot-origin).dot(D)
RUN=END-BRIDGE
assert 2.4<RUN<3.5

# Reuse only geometry helpers; never execute the whole-scene builder here.
tree=ast.parse((P/'build_stairs.py').read_text())
definitions=[n for n in tree.body if isinstance(n,ast.FunctionDef) and
             n.name in ('mesh','append_beam','beam','grate_panel')]
exec(compile(ast.Module(body=definitions,type_ignores=[]),str(P/'build_stairs.py'),'exec'))

for ob in list(COL.objects):
    if upper_part(ob):
        bpy.data.objects.remove(ob,do_unlink=True)
for ob in S.objects:
    for mod in list(ob.modifiers):
        if mod.name=='Left stair bridge entrance':
            ob.modifiers.remove(mod)

# Restore the former rim opening's fixtures before cutting the radial opening.
archive=bpy.data.collections['Archive | front-left straight stair blockout']
rim_collection=bpy.data.collections['03 | Uniform slender steel railings']
for ob in list(archive.objects):
    if ob.name!='Front left | descending bridge stairs':
        rim_collection.objects.link(ob)
        archive.objects.unlink(ob)

for i in range(2):
    grate_panel('upper bridge bay %02d'%(i+1),i*BAY,(i+1)*BAY,-HALF,HALF,H)
for y in (-HALF,HALF):
    beam('upper bridge edge girder',(0,y,H-.085),(BRIDGE,y,H-.085),.055,.16)
for x in (0,BAY,BRIDGE):
    beam('bridge cross bearer',(x,-HALF,H-.09),(x,HALF,H-.09),.045,.1)
for sign in (-1,1):
    beam('bridge underside diagonal',(0,sign*(HALF-.06),H-.115),(BRIDGE,-sign*(HALF-.06),H-.115),.035,.04)

rise=(H-MID)/COUNT
going=RUN/COUNT
for i in range(COUNT):
    x0=BRIDGE+i*going
    z=H-(i+1)*rise
    grate_panel('first flight tread %02d'%(i+1),x0,x0+going,-HALF+.025,HALF-.025,z,True)
    beam('first flight tread %02d nosing'%(i+1),(x0,-HALF+.025,z-.011),(x0,HALF-.025,z-.011),.028,.026,FRAME_MAT,.001)
for y in (-HALF,HALF):
    beam('first flight inclined stringer',(BRIDGE,y,H-.11),(END,y,MID-.11),.048,.19)

# One triangular open-grate cassette, fitted against the unchanged square edge.
triangle=[INV@p for p in (q0,tip,q1)]
for i,(a,b) in enumerate(zip(triangle,triangle[1:]+triangle[:1])):
    beam('triangle edge frame %d'%i,a-UP*.024,b-UP*.024,.035,.046,FRAME_MAT)
    beam('triangle underframe %d'%i,a-UP*.095,b-UP*.095,.043,.14)

def clipped_line(axis,value):
    other=1-axis
    hits=[]
    for a,b in zip(triangle,triangle[1:]+triangle[:1]):
        if abs(a[axis]-b[axis])<1e-8:
            continue
        t=(value-a[axis])/(b[axis]-a[axis])
        if 0<=t<=1:
            hits.append(a[other]+t*(b[other]-a[other]))
    return (min(hits),max(hits)) if len(hits)>=2 else None

vs,fs=[],[]
for axis,spacing,width,depth in [(0,.035,.0042,.028),(1,.034,.0032,.014)]:
    low=min(p[axis] for p in triangle)
    high=max(p[axis] for p in triangle)
    for i in range(1,math.ceil((high-low)/spacing)):
        value=low+i*spacing
        clipped=clipped_line(axis,value)
        if clipped and clipped[1]-clipped[0]>.006:
            a=Vector((0,0,MID-depth/2))
            b=a.copy()
            a[axis]=b[axis]=value
            a[1-axis],b[1-axis]=clipped
            append_beam(vs,fs,a,b,width,depth)
mesh('triangle open grating extension',vs,fs,GRATE)

# Upper railings meet the existing landing posts. The short triangle edge gets
# its own return; all square-landing and lower-flight rail meshes stay intact.
entry=math.sqrt(3.625**2-HALF**2)-distance
for side,y in enumerate((-HALF,HALF)):
    path=[Vector((entry,y,H)),Vector((BAY,y,H)),Vector((BRIDGE,y,H)),Vector((END,y,MID))]
    posted=set()
    for section,(a,b) in enumerate(zip(path,path[1:])):
        ah=(.19,.345) if section==0 else (.295,.55)
        bh=(.295,.55)
        for level,label in enumerate(('middle','top')):
            beam('continuous %s rail %d section %d'%(label,side,section),a+UP*ah[level],b+UP*bh[level],.025,.025)
        steps=max(1,math.ceil((b-a).length/.82))
        for j in range(steps+1):
            t=j/steps
            p=a.lerp(b,t)
            key=tuple(round(v,5) for v in p)
            # q0 already has the protected square-corner upright.
            if key in posted or (side==0 and (p-path[-1]).length<.001):
                continue
            posted.add(key)
            height=ah[1]*(1-t)+bh[1]*t
            beam('radial approach guardrail upright',p-UP*.1,p+UP*height,.028,.028)
            beam('radial approach guardrail shoe',p+Vector((-.033,0,-.055)),p+Vector((.033,0,-.055)),.052,.025,FRAME_MAT)
for h in (.295,.55):
    beam('triangle outer rail return',triangle[1]+UP*h,triangle[2]+UP*h,.025,.025)

for i,y in enumerate((-HALF,HALF)):
    x,z=BRIDGE,H
    beam('warm lamp %02d housing'%i,(x,y,z+.055),(x,y,z+.19),.059,.051)
    beam('warm lamp %02d diffuser'%i,(x,y-.028,z+.083),(x,y-.028,z+.166),.026,.014,WARM,.001)
    data=bpy.data.lights.new('Left stairs | warm marker %02d'%i,'POINT')
    data.color=(1,.58,.26)
    data.energy=3
    data.shadow_soft_size=.045
    ob=bpy.data.objects.new(data.name,data)
    COL.objects.link(ob)
    ob.location=FRAME@Vector((x,y,z+.13))
    ob[TAG]=True
    ob['radial_triangle_generated']=True

vs,fs=[],[]
append_beam(vs,fs,(-.45,0,H+.3),(.45,0,H+.3),HALF*2,1.15)
cutter=mesh('hidden center guardrail entrance cutter',vs,fs,STEEL)
cutter.display_type='WIRE'
cutter.hide_render=True
cutter.hide_set(True)
for ob in list(rim_collection.objects):
    if 'guardrail' in ob.name:
        mod=ob.modifiers.new('Left stair bridge entrance','BOOLEAN')
        mod.operation='DIFFERENCE'
        mod.solver='EXACT'
        mod.object=cutter
    elif ob.type=='MESH':
        ps=[INV@ob.matrix_world@v.co for v in ob.data.vertices]
        if ps:
            p=sum(ps,Vector())/len(ps)
            if -.55<p.x<.55 and abs(p.y)<HALF-.02 and (max(v.z for v in ps)>H+.02 or 'post bolted foot' in ob.name):
                archive.objects.link(ob)
                rim_collection.objects.unlink(ob)
for ob in MADE:
    ob['radial_triangle_generated']=True

bpy.context.view_layer.update()
changed=[n for n,h in protected.items() if bpy.data.objects.get(n) is None or signature(bpy.data.objects[n])!=h]
assert not changed,changed
radial=Vector((origin.x-center.x,origin.y-center.y,0)).normalized()
normal_error=math.degrees(math.atan2(radial.cross(D).length,radial.dot(D)))
assert normal_error<.001
triangle_area=abs((triangle[1]-triangle[0]).cross(triangle[2]-triangle[0]).z)/2
assert all(abs(p.z-MID)<1e-5 for p in triangle)
assert ((FRAME@Vector((END,-HALF,MID)))-q0).length<1e-5
assert ((FRAME@Vector((END,HALF,MID)))-tip).length<1e-5
COL['route']='Radial two-bay bridge -> upper stairs -> triangular infill -> fixed square landing -> fixed lower stairs'
COL['radial_bridge_entry']=True
report={'radial_error_degrees':normal_error,'protected_objects':len(protected),
        'protected_objects_unchanged':not changed,'protected_names':list(protected),
        'bridge_origin':list(origin),'bridge_direction':list(D),'upper_run':RUN,
        'upper_steps':COUNT,'upper_going':going,'bridge_bays':2,
        'triangle_world_vertices':[list(p) for p in (q0,tip,q1)],
        'triangle_area':triangle_area,'triangle_height':MID,
        'triangle_depth':OLD_A-(fixed_inv@tip).x,
        'fixed_frame':[list(row) for row in fixed_frame],'upper_frame':[list(row) for row in FRAME]}
(P/'radial-entry-report.json').write_text(json.dumps(report,indent=2))
result=report
