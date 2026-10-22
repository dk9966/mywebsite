"""Replace the front-left blockout with a two-bay bridge and right-turn stairs.

Run in the current Blender scene. The former stairs and entrance posts are
archived; the existing platforms, camera and terrain stay in place.
"""
import bpy
import bmesh
import json
import math
from pathlib import Path
from mathutils import Vector, Matrix

P = Path(__file__).resolve().parent
S = bpy.context.scene
OLD = bpy.data.objects['Front left | descending bridge stairs']
FLOOR = bpy.data.objects['Front left | beveled rectangle landing']
UP = Vector((0, 0, 1))
TAG = 'left_switchback_generated'
COL_NAME = '166 | Left bridge and right-turn steel stairs'
COL = bpy.data.collections.get(COL_NAME)
if COL is None:
    COL = bpy.data.collections.new(COL_NAME)
    S.collection.children.link(COL)
ARCH = bpy.data.collections.get('Archive | front-left straight stair blockout')
if ARCH is None:
    ARCH = bpy.data.collections.new('Archive | front-left straight stair blockout')
    S.collection.children.link(ARCH)
ARCH.hide_viewport = ARCH.hide_render = True

def archive(ob):
    if ob.name not in ARCH.objects:
        ARCH.objects.link(ob)
    for collection in list(ob.users_collection):
        if collection != ARCH:
            collection.objects.unlink(ob)

for ob in list(COL.objects):
    if ob.get(TAG):
        bpy.data.objects.remove(ob, do_unlink=True)
for ob in S.objects:
    for mod in list(ob.modifiers):
        if mod.name == 'Left stair bridge entrance':
            ob.modifiers.remove(mod)

# Reposition the gate without leaving missing posts at its former location.
rail_collection = bpy.data.collections['03 | Uniform slender steel railings']
for ob in list(ARCH.objects):
    if ob != OLD:
        rail_collection.objects.link(ob)
        ARCH.objects.unlink(ob)

# Derive the upper entrance direction from the actual, hand-positioned steps.
points = [OLD.matrix_world @ v.co for v in OLD.data.vertices]
high = max(p.z for p in points)
low = min(p.z for p in points)
tops = [p for p in points if abs(p.z-high) < .001]
bots = [p for p in points if abs(p.z-low) < .001]
old_top = sum(tops, Vector()) / len(tops)
old_bottom = sum(bots, Vector()) / len(bots)
D = old_bottom-old_top
D.z = 0
D.normalize()
RIGHT = Vector((D.y, -D.x, 0))
CENTER = bpy.data.objects['Rig | middle radius'].matrix_world.translation.copy()
CENTER.z = high
H = high
L = max((FLOOR.matrix_world @ v.co).z for v in FLOOR.data.vertices)
MID = (H+L)/2
HALF = .67
BAY = .56
BRIDGE = 2*BAY
COUNT = 14
RUN = 3.06
LAND = HALF*2
A = BRIDGE+RUN
B = A+LAND
CX = A+HALF
END_Y = HALF+RUN
offset = (old_top-CENTER).dot(RIGHT)
# Inset the bridge threshold into the circular rim enough to cover both corners.
radius = 3.705
entrance_distance = math.sqrt(radius**2-(abs(offset)+HALF)**2)-.025
ORIGIN = CENTER+D*entrance_distance+RIGHT*offset
ORIGIN.z = H
# Rotate around this upper attachment point to follow the lower deck's long edge.
floor_points = [FLOOR.matrix_world @ v.co for v in FLOOR.data.vertices]
floor_top = [p for p in floor_points if abs(p.z-L)<.001]
floor_edges = [b-a for a,b in zip(floor_top,floor_top[1:]+floor_top[:1])]
long_edge = max(floor_edges,key=lambda v:v.length).normalized()
if long_edge.dot(RIGHT)<0:
    long_edge = -long_edge
original_d = D.copy()
RIGHT = Vector((long_edge.x,long_edge.y,0)).normalized()
D = Vector((-RIGHT.y,RIGHT.x,0))
alignment_angle = math.degrees(math.atan2(original_d.cross(D).z,original_d.dot(D)))
FRAME = Matrix(((D.x, RIGHT.x, 0, ORIGIN.x),
                (D.y, RIGHT.y, 0, ORIGIN.y),
                (0, 0, 1, 0), (0, 0, 0, 1)))
INV = FRAME.inverted()
STEEL = bpy.data.materials['Metal | dark structural steel']
FRAME_MAT = bpy.data.materials['Bridge | blue gunmetal panel frames']
GRATE = bpy.data.materials['Bridge | graphite open steel grating']
BOLT = bpy.data.materials['Bridge | restrained silver fasteners']
WARM = bpy.data.materials['Metal | amber lamp diffusers']
MADE = []

def mesh(name, vs, fs, material, bevel=0):
    me = bpy.data.meshes.new('Left stairs | '+name)
    me.from_pydata(vs, [], fs)
    me.update()
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new('Left stairs | '+name, me)
    COL.objects.link(ob)
    ob.matrix_world = FRAME
    me.materials.append(material)
    ob[TAG] = True
    if bevel:
        mod = ob.modifiers.new('Soft fabricated edges', 'BEVEL')
        mod.width = bevel
        mod.segments = 2
        ob.modifiers.new('Weighted steel normals', 'WEIGHTED_NORMAL')
    MADE.append(ob)
    return ob

def append_beam(vs, fs, a, b, width, depth):
    a, b = Vector(a), Vector(b)
    axis = (b-a).normalized()
    helper = UP if abs(axis.z)<.95 else Vector((0,1,0))
    u = axis.cross(helper).normalized()*width/2
    v = axis.cross(u).normalized()*depth/2
    k = len(vs)
    vs.extend([tuple(p+su*u+sv*v) for p in (a,b)
               for su,sv in [(-1,-1),(1,-1),(1,1),(-1,1)]])
    fs.extend([tuple(k+i for i in f) for f in
               [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]])

def beam(name, a, b, width, depth, material=STEEL, bevel=.002):
    vs, fs = [], []
    append_beam(vs, fs, a, b, width, depth)
    return mesh(name, vs, fs, material, bevel)

def grate_panel(name, x0, x1, y0, y1, z, tread=False):
    vs, fs = [], []
    # Individually framed open-grid steel cassettes, matching the existing bridge.
    thick = .032 if tread else .046
    border = .018 if tread else .035
    for a,b in [((x0,y0,z-thick/2),(x1,y0,z-thick/2)),
                ((x0,y1,z-thick/2),(x1,y1,z-thick/2)),
                ((x0,y0,z-thick/2),(x0,y1,z-thick/2)),
                ((x1,y0,z-thick/2),(x1,y1,z-thick/2))]:
        append_beam(vs,fs,a,b,border,thick)
    mesh(name+' frame',vs,fs,FRAME_MAT,.0015)
    vs,fs=[],[]
    nx=max(2,round((x1-x0)/.035))
    ny=max(2,round((y1-y0)/.034))
    for i in range(1,nx):
        x=x0+(x1-x0)*i/nx
        append_beam(vs,fs,(x,y0+border/2,z-.015),(x,y1-border/2,z-.015),.0042,.028)
    for i in range(1,ny):
        y=y0+(y1-y0)*i/ny
        append_beam(vs,fs,(x0+border/2,y,z-.01),(x1-border/2,y,z-.01),.0032,.014)
    ob=mesh(name+' open grating',vs,fs,GRATE)
    ob['walking_surface_z']=z
    return ob

archive(OLD)
for i in range(2):
    grate_panel('upper bridge bay %02d'%(i+1),i*BAY,(i+1)*BAY,-HALF,HALF,H)
for y in (-HALF,HALF):
    beam('upper bridge edge girder',(0,y,H-.085),(BRIDGE,y,H-.085),.055,.16)
for x in (0,BAY,BRIDGE):
    beam('bridge cross bearer',(x,-HALF,H-.09),(x,HALF,H-.09),.045,.1)
for sign in (-1,1):
    beam('bridge underside diagonal',(0,sign*(HALF-.06),H-.115),(BRIDGE,-sign*(HALF-.06),H-.115),.035,.04)

# Curved grating infill closes the small wedge at the rotated circular entrance.
circle = INV @ CENTER
def rim_x(y,r):
    return circle.x+math.sqrt(max(0,r*r-(y-circle.y)**2))
vs,fs=[],[]
for i in range(51):
    y=-HALF+2*HALF*i/50
    start=min(0,rim_x(y,radius)-.016)
    if start<-.01:
        append_beam(vs,fs,(start,y,H-.017),(.02,y,H-.017),.0042,.032)
for i in range(17):
    x=-.48+i*.03
    ys=[-HALF+2*HALF*j/200 for j in range(201)]
    inside=[y for y in ys if rim_x(y,radius)-.016<=x]
    if inside:
        append_beam(vs,fs,(x,min(inside),H-.01),(x,max(inside)+.0001,H-.01),.0032,.014)
mesh('curved entry open grating infill',vs,fs,GRATE)
for y in (-HALF,HALF):
    start=min(0,rim_x(y,radius)-.02)
    if start<-.01:
        beam('curved entry side frame',(start,y,H-.023),(0,y,H-.023),.035,.046,FRAME_MAT)

rise=(H-L)/(COUNT*2)
going=RUN/COUNT
for i in range(COUNT):
    x0=BRIDGE+i*going
    z=H-(i+1)*rise
    grate_panel('first flight tread %02d'%(i+1),x0,x0+going,-HALF+.025,HALF-.025,z,True)
    beam('first flight tread %02d nosing'%(i+1),(x0,-HALF+.025,z-.011),(x0,HALF-.025,z-.011),.028,.026,FRAME_MAT,.001)
    y0=HALF+i*going
    z2=MID-(i+1)*rise
    grate_panel('second flight tread %02d'%(i+1),A+.025,B-.025,y0,y0+going,z2,True)
    beam('second flight tread %02d nosing'%(i+1),(A+.025,y0,z2-.011),(B-.025,y0,z2-.011),.028,.026,FRAME_MAT,.001)
for y in (-HALF,HALF):
    beam('first flight inclined stringer',(BRIDGE,y,H-.11),(A,y,MID-.11),.048,.19)
for x in (A,B):
    beam('second flight inclined stringer',(x,HALF,MID-.11),(x,END_Y,L-.11),.048,.19)

grate_panel('half-height right-turn landing',A,B,-HALF,HALF,MID)
for a,b in [((A,-HALF,MID-.09),(B,-HALF,MID-.09)),
            ((B,-HALF,MID-.09),(B,HALF,MID-.09)),
            ((A,HALF,MID-.09),(B,HALF,MID-.09)),
            ((A,-HALF,MID-.09),(A,HALF,MID-.09))]:
    beam('landing edge girder',a,b,.055,.16)
for sign in (-1,1):
    beam('landing underside X brace',(A+.04,sign*(HALF-.04),MID-.12),(B-.04,-sign*(HALF-.04),MID-.12),.035,.05)

# Four corner supports with matching feet and bracing under the landing.
for x in (A+.08,B-.08):
    for y in (-HALF+.07,HALF-.07):
        beam('landing support leg',(x,y,L),(x,y,MID-.15),.065,.065)
        beam('landing support foot',(x-.08,y,L+.008),(x+.08,y,L+.008),.15,.022,FRAME_MAT)
        inner_x=x+(.42 if x<CX else -.42)
        beam('landing knee brace',(x,y,MID-.62),(inner_x,y,MID-.15),.044,.048)
    beam('landing support diagonal',(x,-HALF+.07,L+.14),(x,HALF-.07,MID-.2),.035,.04)

# The inside corner remains open through the full width of both flights.
def rail_heights(x):
    blend=min(1,max(0,x/BAY))
    return (.19+(.295-.19)*blend,.345+(.55-.345)*blend)

paths=[[(rim_x(-HALF,3.625),-HALF,H),(BAY,-HALF,H),(BRIDGE,-HALF,H),(A,-HALF,MID),(B,-HALF,MID),(B,HALF,MID),(B,END_Y,L)],
       [(rim_x(HALF,3.625),HALF,H),(BAY,HALF,H),(BRIDGE,HALF,H),(A,HALF,MID),(A,END_Y,L)]]
post_keys=set()
for side,path in enumerate(paths):
    for index,(a,b) in enumerate(zip(path,path[1:])):
        a,b=Vector(a),Vector(b)
        ah=(.19,.345) if index==0 else (.295,.55)
        bh=(.295,.55)
        for level in range(2):
            beam('continuous %s rail %d section %d'%('top' if level else 'middle',side,index),a+UP*ah[level],b+UP*bh[level],.025,.025)
        intervals=max(1,math.ceil((b-a).length/.82))
        for j in range(intervals+1):
            t=j/intervals
            p=a.lerp(b,t)
            key=tuple(round(v,5) for v in p)
            if key in post_keys:
                continue
            post_keys.add(key)
            height=ah[1]*(1-t)+bh[1]*t
            beam('bolted guardrail upright',p-UP*.1,p+UP*height,.028,.028)
            beam('guardrail mounting shoe',p+Vector((-.033,0,-.055)),p+Vector((.033,0,-.055)),.052,.025,FRAME_MAT)

# Restrained warm caged marker lamps at the bridge, landing and stair foot.
for i,(x,y,z) in enumerate([(BRIDGE,-HALF,H),(BRIDGE,HALF,H),
                           (B,-HALF,MID),(B,HALF,MID),(A,END_Y,L),(B,END_Y,L)]):
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

# Keep a smooth entrance through the center platform's existing guardrails.
vs,fs=[],[]
append_beam(vs,fs,(-.7,0,H+.30),(.7,0,H+.30),LAND,1.15)
cutter=mesh('hidden center guardrail entrance cutter',vs,fs,STEEL)
cutter.display_type='WIRE'
cutter.hide_render=True
cutter.hide_set(True)
changed=[]
for ob in list(bpy.data.collections['03 | Uniform slender steel railings'].objects):
    if 'guardrail' in ob.name:
        mod=ob.modifiers.new('Left stair bridge entrance','BOOLEAN')
        mod.operation='DIFFERENCE'
        mod.solver='EXACT'
        mod.object=cutter
        changed.append(ob.name)
    elif ob.type=='MESH':
        ps=[INV@ob.matrix_world@v.co for v in ob.data.vertices]
        if ps:
            p=sum(ps,Vector())/len(ps)
            if -.8<p.x<.8 and abs(p.y)<HALF-.02 and (max(v.z for v in ps)>H+.02 or 'post bolted foot' in ob.name):
                archive(ob)
                changed.append(ob.name)

# Bridge and landing metadata make the intended route straightforward to inspect.
COL['route']='Two level bridge bays -> half-height stairs -> 90 degree right landing -> lower deck'
COL['bridge_bays']=2
COL['bridge_length']=BRIDGE
COL['landing_elevation']=MID
COL['upper_elevation']=H
COL['lower_elevation']=L
COL['steps_per_flight']=COUNT
COL['turn_degrees_clockwise']=90
COL['landing_support_count']=4
COL['bottom_flight_parallel_to_long_edge']=True
bpy.context.view_layer.update()
report={'upper_origin':list(ORIGIN),'first_direction':list(D),'right_direction':list(RIGHT),
        'bridge_bays':2,'bay_length':BAY,'bridge_length':BRIDGE,'width':LAND,
        'upper_z':H,'mid_z':MID,'lower_z':L,'steps_per_flight':COUNT,'rise':rise,'going':going,
        'landing_center':list(FRAME@Vector((CX,0,MID))),
        'lower_endpoint':list(FRAME@Vector((CX,END_Y,L))),
        'changed_existing':changed,'frame':[list(r) for r in FRAME],
        'made_meshes':len(MADE),'active_file':bpy.data.filepath,
        'landing_support_count':4,'alignment_rotation_degrees':alignment_angle,
        'platform_long_direction':list(long_edge)}
(P/'build-report.json').write_text(json.dumps(report,indent=2))
result=report
