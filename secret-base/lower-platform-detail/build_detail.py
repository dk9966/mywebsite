"""Fit the unfurnished lower workshop to the camera reference in the live scene.

Run in Blender after opening before-detail.blend. All lengths are in metres.
The source terrain datablock and blockout meshes are retained for recovery.
"""
import bpy, bmesh, math, json, random
from pathlib import Path
from mathutils import Vector, Matrix

P = Path('/Users/danielku/mywebsite/secret-base/lower-platform-detail')
S = bpy.context.scene
FRAME = Matrix.Translation((21.299999237, 0, 0)) @ Matrix.Rotation(-math.atan2(12, 19), 4, 'Z')
INV = FRAME.inverted()
F = 6.824491024
MF = 6.871178627
H = 2.03
ROOF = F + H
if bpy.context.object and bpy.context.object.mode != 'OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')

def collection(name):
    c = bpy.data.collections.get(name)
    if not c:
        c = bpy.data.collections.new(name)
        S.collection.children.link(c)
    return c

ARCH = collection('156 | Lower workshop walls and canopy')
DECK = collection('157 | Lower deck and cliff supports')
BRIDGE = collection('158 | Connected bridge and railings')
CUTTERS = collection('159 | Hidden architectural cutters')
ARCHIVE = collection('Archive | lower platform before reference detail')
ARCHIVE.hide_render = True
ARCHIVE.hide_viewport = True

def material(name, color, metal=0, rough=.5, emission=0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    p = m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value = (*color, 1)
    p.inputs['Metallic'].default_value = metal
    p.inputs['Roughness'].default_value = rough
    if emission:
        p.inputs['Emission Color'].default_value = (*color, 1)
        p.inputs['Emission Strength'].default_value = emission
    return m

steel = bpy.data.materials['Metal | dark structural steel']
alloy = bpy.data.materials['Metal | outer walkway alloy']
edge = bpy.data.materials['Metal | machined edge highlights']
floor = bpy.data.materials['Metal | satin blue steel']
black = bpy.data.materials['Metal | unlit grate recess']
wall = material('Lower | charcoal architectural panels', (.085,.12,.14), .62, .49)
roofmat = material('Lower | matte roof cassette', (.037,.052,.062), .65, .47)
white = material('Lower | cool white practical diffuser', (.63,.83,1), .1, .29, 5)
paint = material('Lower | muted brass floor registration', (.38,.32,.16), .55, .48)

made = []
def mesh(name, verts, faces, mat, col, bevel=0):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(me); bm.free()
    me.materials.append(mat)
    o = bpy.data.objects.new(name, me); col.objects.link(o)
    o.matrix_world = FRAME
    if bevel:
        mod = o.modifiers.new('Fabricated edge radius', 'BEVEL'); mod.width = bevel; mod.segments = 2
        o.modifiers.new('Fabricated normals', 'WEIGHTED_NORMAL')
    made.append(o)
    return o

def prism(name, poly, z0, z1, mat, col, bevel=0):
    n = len(poly)
    verts = [(x,y,z) for z in (z0,z1) for x,y in poly]
    faces = [tuple(reversed(range(n))), tuple(range(n,2*n))]
    faces += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    return mesh(name,verts,faces,mat,col,bevel)

def beam(name, a, b, width, depth, mat, col, bevel=.004):
    a,b = Vector(a),Vector(b)
    axis = (b-a).normalized()
    helper = Vector((0,0,1)) if abs(axis.z)<.95 else Vector((0,1,0))
    u = axis.cross(helper).normalized()*width/2
    v = axis.cross(u).normalized()*depth/2
    verts = [tuple(p+su*u+sv*v) for p in (a,b) for su,sv in [(-1,-1),(1,-1),(1,1),(-1,1)]]
    return mesh(name,verts,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],mat,col,bevel)

def strip(name, points, width, depth, mat, col):
    # One welded sweep with mitered corners; no independent floating rail ends.
    ps = [Vector(p) for p in points]; verts=[]
    for i,p in enumerate(ps):
        before=(p-ps[max(0,i-1)]).normalized() if i else (ps[1]-p).normalized()
        after=(ps[min(len(ps)-1,i+1)]-p).normalized() if i<len(ps)-1 else before
        n1=Vector((-before.y,before.x,0)).normalized()
        n2=Vector((-after.y,after.x,0)).normalized()
        n=(n1+n2).normalized()
        n*=width/2/max(.3,n.dot(n1))
        verts += [tuple(p+sg*n+Vector((0,0,z))) for sg,z in [(-1,-depth/2),(1,-depth/2),(1,depth/2),(-1,depth/2)]]
    faces=[(0,3,2,1)]
    for i in range(len(ps)-1):
        for j in range(4): faces.append((4*i+j,4*i+(j+1)%4,4*(i+1)+(j+1)%4,4*(i+1)+j))
    faces.append(tuple(range(4*(len(ps)-1),4*len(ps))))
    return mesh(name,verts,faces,mat,col,.002)

def ring(name,cx,cy,ri,ro,z,mat,col):
    n=128; verts=[];faces=[]
    for r in (ri,ro):
        verts += [(cx+r*math.cos(i*math.tau/n),cy+r*math.sin(i*math.tau/n),z) for i in range(n)]
    for i in range(n):j=(i+1)%n;faces.append((i,j,n+j,n+i))
    return mesh(name,verts,faces,mat,col)

def archive(o):
    ARCHIVE.objects.link(o)
    for c in list(o.users_collection):
        if c != ARCHIVE: c.objects.unlink(o)
    o.hide_render=True; o.hide_viewport=True

def parent_keep(o,p):
    mw=o.matrix_world.copy();o.parent=p;o.matrix_world=mw

# Keep the user-aligned front corners and floor elevation. The back becomes
# the four oblique architectural bays measured from the reference camera.
front=[(4.621191,-5.011547),(5.871193,-6.261546),(8.871193,-6.261546),(10.121193,-5.011547)]
back=[(6.482775,-.089331),(8.141458,-.643934),(9.585233,-1.578686),(10.783675,-2.669809),(11.351686,-3.570891)]
left=(5.52,-.08)
foot=front+[back[-1]]+list(reversed(back[:-1]))+[left,(4.621191,-2.011547)]
lower=bpy.data.objects['Lower | plain octagon']
oldmesh=lower.data;oldmesh.use_fake_user=True;oldmesh.name='Lower | preserved square blockout mesh'
new=prism('Lower | reference-fitted deck',foot,F-.205,F,floor,DECK,.009)
relative=lower.matrix_world.inverted()@FRAME
for v in new.data.vertices:v.co=relative@v.co
lower.data=new.data
for m in list(new.modifiers):
    if m.type=='BEVEL':mod=lower.modifiers.new(m.name,m.type);mod.width=m.width;mod.segments=2
bpy.data.objects.remove(new,do_unlink=True);made.remove(new)
lower['reference_detail']='Square front retained; oblique rear workshop and mitered bridge entrance.'
cube=bpy.data.objects.get('Cube')
if cube: archive(cube)
oldbridge=bpy.data.objects['Bridge | floating rectangle'];archive(oldbridge)

# Main platform gate and matched bridge deck. The lower end is mitered to
# the exact vertical edge of the apron, not a rectangle overlapping it.
d=Vector((1,-.625,0)).normalized();n=Vector((-d.y,d.x,0))
R=3.620207; half=.67
t=math.sqrt(R*R-half*half)
starts=[d*t+s*n*half for s in (-1,1)]
ends=[]
for a in starts:
    ends.append(a+d*((4.621191-a.x)/d.x))
outline=[tuple(starts[0][:2]),tuple(ends[0][:2]),tuple(ends[1][:2]),tuple(starts[1][:2])]
verts=[(p[0],p[1],z) for zoff in (-.09,0) for p,z in [(starts[0],MF+zoff),(ends[0],F+zoff),(ends[1],F+zoff),(starts[1],MF+zoff)]]
bridge=mesh('Bridge | mitered continuous walking deck',verts,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],floor,BRIDGE,.004)

# Carve the correct aperture after the original rail sizing nodes. Preserve
# the original rail meshes and their controls; the cutter stays editable.
cutpoly=[tuple((d*r+n*s)[:2]) for r,s in [(3.05,-.695),(4.05,-.695),(4.05,.695),(3.05,.695)]]
cutter=prism('Bridge | editable gate aperture',cutpoly,MF+.022,MF+.7,black,CUTTERS)
cutter.display_type='WIRE';cutter.hide_render=True;cutter.hide_set(True)
for o in bpy.data.collections['03 | Uniform slender steel railings'].objects:
    if o.type=='MESH':
        mod=o.modifiers.new('Connected lower bridge opening','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cutter

# The prior opening was at the wrong azimuth. Close it with the same radius,
# heights and bar sections, meeting the new bridge's rear handrail exactly.
rearangle=math.atan2(starts[1].y,starts[1].x)
for height in (.190,.345):
    ps=[(R*math.cos(a),R*math.sin(a),MF+height) for a in [rearangle+(math.radians(4.35)-rearangle)*i/36 for i in range(37)]]
    strip('Bridge | main rim continuous return %.3f'%height,ps,.024,.0178,steel,BRIDGE)
for a in [rearangle,math.radians(-10),math.radians(1.5)]:
    p=Vector((R*math.cos(a),R*math.sin(a),MF))
    beam('Bridge | main rim return stanchion',p,p+Vector((0,0,.35)),.029,.029,steel,BRIDGE)

# A single swept rail on each side continues from the circle, over the
# bridge, around the exposed platform, and terminates at an architectural jamb.
paths=[
    [(starts[0].x,starts[0].y,MF),(ends[0].x,ends[0].y,F)]+[(x,y,F) for x,y in front]+[(back[-1][0],back[-1][1],F)],
    [(starts[1].x,starts[1].y,MF),(ends[1].x,ends[1].y,F),(4.621191,-2.011547,F),(left[0],left[1]-.05,F)]
]
for side,ps in enumerate(paths):
    for h in (.19,.345):strip('Lower | continuous %s rail %.3f'%(side,h),[(x,y,z+h) for x,y,z in ps],.024,.018,steel,BRIDGE)
    strip('Lower | continuous edge curb %s'%side,[(x,y,z-.005) for x,y,z in ps],.043,.055,steel,BRIDGE)
    for j in range(len(ps)-1):
        a,b=Vector(ps[j]),Vector(ps[j+1]); count=max(1,math.ceil((b-a).length/.62))
        for k in range(count):
            p=a.lerp(b,k/count)
            beam('Lower | welded railing stanchion',p,p+Vector((0,0,.351)),.027,.03,steel,BRIDGE,.002)
            beam('Lower | railing base shoe',p+Vector((0,0,-.025)),p+Vector((0,0,.019)),.069,.065,alloy,BRIDGE,.002)

# Shallow deck seams, a recessed circular service pad and restrained rings.
cx,cy=7.52,-3.52
ring('Lower | circular recessed service track',cx,cy,1.95,2.08,F+.003,black,DECK)
ring('Lower | outer circular machined lip',cx,cy,2.06,2.092,F+.006,alloy,DECK)
ring('Lower | inner circular machined lip',cx,cy,1.913,1.952,F+.006,alloy,DECK)
ring('Lower | thin brass registration circle',cx,cy,1.874,1.899,F+.005,paint,DECK)
ring('Lower | center service plate seam',cx,cy,.68,.692,F+.005,black,DECK)
for i in range(16):
    a=i*math.tau/16
    p=(cx+.70*math.cos(a),cy+.70*math.sin(a),F+.003)
    q=(cx+1.868*math.cos(a),cy+1.868*math.sin(a),F+.003)
    beam('Lower | radial plate joint',p,q,.007,.003,black,DECK,0)
for i in range(len(foot)):
    a,b=foot[i],foot[(i+1)%len(foot)]
    beam('Lower | load bearing perimeter fascia',(*a,F-.18),(*b,F-.18),.13,.24,steel,DECK)
    beam('Lower | edge highlight',(*a,F-.062),(*b,F-.062),.04,.025,alloy,DECK,.002)
for x in [5.6,6.7,7.8,8.9,9.7]:
    beam('Lower | structural floor plate seam',(x,-6.23 if 5.87<x<8.87 else -5.60,F+.003),(x,-5.65 if 5.87<x<8.87 else -5.13,F+.003),.009,.003,black,DECK,0)

# Actual lattice under the bridge, with paired stringers and transverse beams.
for side in range(2):
    a=Vector((*starts[side][:2],MF));b=Vector((*ends[side][:2],F))
    for drop in (.10,.36):beam('Bridge | longitudinal steel chord',a-Vector((0,0,drop)),b-Vector((0,0,drop)),.08,.08,steel,BRIDGE)
    for j in range(4):
        p=a.lerp(b,j/4);q=a.lerp(b,(j+1)/4)
        beam('Bridge | diagonal truss web',p-Vector((0,0,.34 if j%2 else .1)),q-Vector((0,0,.1 if j%2 else .34)),.034,.044,steel,BRIDGE)
        beam('Bridge | vertical truss web',p-Vector((0,0,.10)),p-Vector((0,0,.36)),.035,.045,steel,BRIDGE)
for i in range(9):
    a=Vector((*starts[0][:2],MF)).lerp(Vector((*ends[0][:2],F)),i/8)
    b=Vector((*starts[1][:2],MF)).lerp(Vector((*ends[1][:2],F)),i/8)
    beam('Bridge | transverse deck bearer',a-Vector((0,0,.08)),b-Vector((0,0,.08)),.055,.10,steel,BRIDGE)
    if 0<i<8:beam('Bridge | flush transverse tread seam',a+Vector((0,0,.003)),b+Vector((0,0,.003)),.012,.003,black,BRIDGE,0)
for j in range(1,6):
    a=Vector((*starts[0][:2],MF)).lerp(Vector((*starts[1][:2],MF)),j/6)
    b=Vector((*ends[0][:2],F)).lerp(Vector((*ends[1][:2],F)),j/6)
    beam('Bridge | recessed longitudinal grate joint',a+Vector((0,0,.002)),b+Vector((0,0,.002)),.007,.003,black,BRIDGE,0)

# Deep V brackets seated into the cliff. All upper members terminate at the
# same perimeter girder, with anchor pads and gussets at the load junctions.
for x in (5.95,7.42,8.87):
    anchor=Vector((x,-4.03,F-1.80))
    topa=Vector((x,-6.17,F-.27));topb=Vector((x,-1.80,F-.27))
    beam('Lower | radial underfloor girder',topa,topb,.12,.18,steel,DECK)
    beam('Lower | cliff anchored diagonal brace',anchor,topa,.11,.14,steel,DECK)
    beam('Lower | rear diagonal brace',anchor,topb,.09,.12,steel,DECK)
    beam('Lower | vertical load leg',anchor,Vector((x,-4.03,F-.27)),.11,.15,steel,DECK)
    beam('Lower | embedded foundation shoe',anchor-Vector((0,0,.07)),anchor+Vector((0,0,.07)),.29,.28,alloy,DECK)
    beam('Lower | front girder gusset',topa-Vector((0,0,.11)),topa+Vector((0,.08,.06)),.20,.065,alloy,DECK)
beam('Lower | foundation cross tie',(5.95,-4.03,F-1.80),(8.87,-4.03,F-1.80),.095,.14,steel,DECK)

# Four angled wall bays, tilted pier faces and stepped lintels. These are
# architecture only: no desks, machinery, cabinets, vehicle or loose props.
wallline=[left]+back
for j,(aa,bb) in enumerate(zip(wallline,wallline[1:])):
    a=Vector((*aa,F));b=Vector((*bb,F));u=(b-a).normalized();out=Vector((u.y,-u.x,0))
    if out.y>0:out=-out
    length=(b-a).length
    a2=a+Vector((0,.075,H));b2=b+Vector((0,.075,H))
    panelverts=[tuple(p+out*t) for t in (-.16,0) for p in (a,b,b2,a2)]
    mesh('Lower | recessed wall bay %02d'%j,panelverts,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],wall,ARCH,.008)
    for h in (.06,H-.26,H-.08):
        beam('Lower | bay horizontal frame',a+out*.04+Vector((0,0,h)),b+out*.04+Vector((0,0,h)),.095,.073,steel,ARCH)
    for t in (.25,.5,.75):
        p=a.lerp(b,t)+out*.008
        beam('Lower | vertical panel seam',p+Vector((0,0,.09)),p+Vector((0,.065,H-.3)),.009,.012,black,ARCH,0)
    # High, linear practicals like the reference wall lights.
    if j>0:
        p=a.lerp(b,.24)+out*.06+Vector((0,0,1.31));q=a.lerp(b,.76)+out*.06+Vector((0,0,1.31))
        beam('Lower | wall light armored housing',p,q,.09,.082,steel,ARCH)
        beam('Lower | wall linear diffuser',p+out*.049,q+out*.049,.029,.027,white,ARCH,.003)
for j,pt in enumerate(wallline):
    p=Vector((*pt,F)); q=p+Vector((0,.075,H-.17));r=p+Vector((0,.18,H))
    beam('Lower | splayed structural wall jamb',p,q,.115,.17,steel,ARCH,.012)
    beam('Lower | clipped lintel shoulder',q,r,.115,.17,steel,ARCH,.01)
    beam('Lower | exposed jamb edge',p+Vector((-.043,-.091,.09)),q+Vector((-.043,-.091,0)),.017,.024,alloy,ARCH,.003)
    beam('Lower | jamb spread foot',p+Vector((0,-.02,.015)),p+Vector((0,-.15,.25)),.18,.19,steel,ARCH,.01)

# A shallow stepped canopy follows the oblique wall, with the distinctive
# central projecting polygonal light hood and a closed dark soffit.
rear=[(x,y+.30) for x,y in wallline]
lip=[(x,y-.54) for x,y in wallline]
roofpoly=lip+list(reversed(rear))
prism('Lower | continuous folded canopy roof',roofpoly,ROOF-.05,ROOF+.11,roofmat,ARCH,.012)
strip('Lower | deep continuous canopy fascia',[(x,y,ROOF-.075) for x,y in lip],.105,.23,steel,ARCH)
strip('Lower | stepped canopy crown',[(x,y,ROOF+.09) for x,y in lip],.055,.045,alloy,ARCH)
for i in range(len(lip)-1):
    p=Vector((*lip[i],ROOF-.035));q=Vector((*lip[i+1],ROOF-.035))
    for t in (.2,.5,.8):
        a=p.lerp(q,t)
        beam('Lower | roof cassette stiffener',a,a+Vector((0,.79,0)),.045,.065,steel,ARCH)
hood=[(7.55,-1.18),(7.89,-1.66),(8.78,-1.96),(9.48,-1.97),(9.92,-1.67),(9.56,-1.36),(8.22,-.45),(7.55,-.45)]
prism('Lower | faceted projecting roof light hood',hood,ROOF-.18,ROOF+.08,roofmat,ARCH,.009)
strip('Lower | hood front armor',[(x,y,ROOF-.16) for x,y in hood[:5]],.075,.20,steel,ARCH)
for a,b in [((7.94,-1.68),(8.36,-1.82)),((8.90,-1.977),(9.35,-1.977))]:
    beam('Lower | roof inset light recess',(*a,ROOF-.257),(*b,ROOF-.257),.066,.033,black,ARCH,.002)
    beam('Lower | roof inset cool white strip',(*a,ROOF-.273),(*b,ROOF-.273),.039,.014,white,ARCH,.002)
def area(name,loc,target,power,size):
    data=bpy.data.lights.new(name,'AREA');data.energy=power;data.color=(.66,.82,1);data.shape='DISK';data.size=size
    o=bpy.data.objects.new(name,data);ARCH.objects.link(o);o.location=FRAME@Vector(loc)
    o.rotation_euler=(FRAME.to_3x3()@(Vector(target)-Vector(loc))).to_track_quat('-Z','Y').to_euler();made.append(o)
area('Lower | canopy downlight',(8.5,-1.55,ROOF-.29),(7.55,-3.52,F),95,1.35)
for a,b in zip(back,back[1:]):
    p=Vector((*a,F)).lerp(Vector((*b,F)),.5)
    area('Lower | wall practical pool',(p.x,p.y-.20,F+1.27),(p.x,p.y-.7,F+.1),18,.75)

# Recess the existing connected terrain around the architecture, preserving
# its topology and every vertex outside the local workshop/roof envelope.
terrain=bpy.data.objects['150 | continuous cave with oblique carved rooms']
terrain.data.use_fake_user=True
terrain.data=terrain.data.copy();terrain.data.name='Cave | fitted lower workshop recess'
toframe=INV@terrain.matrix_world;fromframe=toframe.inverted()
def back_y(x):
    pts=[(4.95,-.10)]+back+[(12.20,-4.35)]
    for a,b in zip(pts,pts[1:]):
        if a[0]<=x<=b[0]:return a[1]+(b[1]-a[1])*(x-a[0])/(b[0]-a[0])
    return pts[0][1] if x<pts[0][0] else pts[-1][1]
changed=0
for v in terrain.data.vertices:
    p=toframe@v.co;old=p.copy()
    if 5.05<p.x<12.18 and -7.1<p.y<1.4 and F-.38<p.z<ROOF+.70:
        target=back_y(p.x)+.40
        # Floor and roof transitions live behind their visible metal edges.
        wz=min(1,max(0,(p.z-(F-.38))/.28),max(0,(ROOF+.70-p.z)/.55))
        wx=min(1,max(0,(p.x-5.05)/.45),max(0,(12.18-p.x)/.50))
        if p.y<target:p.y+=(target-p.y)*wz*wx
    # A rock ledge under the V shoes, connected to the original cliff skin.
    if 5.4<p.x<9.4 and F-2.2<p.z<F-.72 and -4.1<p.y<.4:
        w=math.sin(math.pi*(p.z-(F-2.2))/1.48)**2
        w*=min(1,(p.x-5.4)/.6,(9.4-p.x)/.6)
        p.y-=max(0,p.y+4.13)*max(0,w)*.85
    if (p-old).length>1e-7:v.co=fromframe@p;changed+=1
terrain.data.update()
terrain['lower_workshop_detail']='Local recess fitted behind four angled wall bays; roof lip and foundation ledge blended into original connected rock.'

# Keep lower architectural pieces attached to the existing platform slider.
for o in list(ARCH.objects)+list(DECK.objects):
    if o!=lower:parent_keep(o,lower)

bpy.context.view_layer.update()
S.camera.data.show_background_images=False
for o in bpy.context.selected_objects:o.select_set(False)
lower.select_set(True);bpy.context.view_layer.objects.active=lower
S['lower_platform_reference']='images/batcave-railings-no-car-v2.png; architecture pass, intentionally unfurnished.'
P.joinpath('build-report.json').write_text(json.dumps({'generated_objects':len(made),'terrain_vertices_adjusted':changed,'floor_height':F,'bridge_width':2*half,'rail_height':.345,'roof_height':ROOF,'bridge_main_ends':[list(p) for p in starts],'bridge_lower_ends':[list(p) for p in ends],'wall_polyline':back,'furniture_added':False},indent=2))
bpy.ops.wm.save_as_mainfile(filepath='/Users/danielku/mywebsite/secret-base/platform-controls/cave-platform-sliders.blend',compress=True)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'detailed-workshop.blend'),copy=True,compress=True)
result={'saved':bpy.data.filepath,'generated_objects':len(made),'terrain_vertices_adjusted':changed,'report':str(P/'build-report.json')}
