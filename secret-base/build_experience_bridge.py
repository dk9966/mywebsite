"""Resize Experience and rebuild the sloped detailed bridge. One-shot migration.

Dimensions derive from the saved Project/empty-island scene. Run in Blender;
pre-change snapshot is base.before-experience-bridge.blend.
"""
import bpy, bmesh, math
from mathutils import Vector, Matrix

CX=21.299999237060547
CY=-9.300000190734863
F=6.871178627
DROP=.5
S=.82
H=.65*.65                 # 35 percent narrower between fence centers
W=1.42*.65                # exact 35 percent reduction in outer deck width
RP=2.712
RE=RP*S
YP=-math.sqrt(RP*RP-H*H)
YE=CY+math.sqrt(RE*RE-H*H)
L=YP-YE
GRADE=DROP/L
ANGLE=math.atan(GRADE)
ZSHAFT=6.7351784706
ZS=(ZSHAFT-DROP)/ZSHAFT
project=bpy.data.objects['island_pillar_project']
experience=bpy.data.objects['island_pillar_empty']
experience.name='island_pillar_experience'
experience['station_role']='Experience'
ec=bpy.data.collections['deck_empty']; ec.name='deck_experience'
pc=bpy.data.collections['deck_project']
bc=bpy.data.collections['bridge_project_empty']; bc.name='bridge_project_experience'

# Snapshot world transforms before touching the parent hierarchy.
worlds={o:o.matrix_world.copy() for o in [experience,*experience.children_recursive]}
origin=Vector((CX,CY,0))
for ob,mw in worlds.items():
    if ob.type=='MESH':
        isshaft=ob==experience or 'veins' in ob.name
        T=Matrix.Translation(origin) @ Matrix.Diagonal((S,S,ZS if isshaft else 1,1)) @ Matrix.Translation(-origin)
        if not isshaft: T=Matrix.Translation((0,0,-DROP))@T
        ob.matrix_world=T@mw
    elif ob.type=='LIGHT':
        p=mw.translation
        p.x=CX+(p.x-CX)*S; p.y=CY+(p.y-CY)*S
        p.z=p.z*ZS if 'shaft' in ob.name or 'vein' in ob.name else p.z-DROP
        mw.translation=p; ob.matrix_world=mw
        ob.data.energy*=.85
    if ob!=experience: ob.name=ob.name.replace('_empty','_experience')
bpy.context.view_layer.update()

# Replace only bridge meshes and the two affected rim objects.
for ob in list(bc.objects): bpy.data.objects.remove(ob,do_unlink=True)
for name in ['deck_railing_b','deck_parapet_b','deck_railing_experience','deck_parapet_experience']:
    ob=bpy.data.objects.get(name)
    if ob and name not in ('deck_railing_b',): bpy.data.objects.remove(ob,do_unlink=True)

def mesh(name,vs,fs,mat,coll=bc,parent=project,bevel=0):
    old=bpy.data.objects.get(name)
    if old:bpy.data.objects.remove(old,do_unlink=True)
    me=bpy.data.meshes.new(name); me.from_pydata(vs,[],fs); me.update()
    bm=bmesh.new(); bm.from_mesh(me); bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces)); bm.to_mesh(me); bm.free()
    ob=bpy.data.objects.new(name,me); coll.objects.link(ob); me.materials.append(bpy.data.materials[mat])
    ob.parent=parent; ob.matrix_parent_inverse=parent.matrix_world.inverted()
    if bevel:
        mod=ob.modifiers.new('Small edge chamfer','BEVEL'); mod.width=bevel; mod.segments=2
    return ob

def addbox(vs,fs,p,dims,rz=0):
    start=len(vs); x,y,z=p; sx,sy,sz=dims
    for dx,dy,dz in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]:
        a,b=dx*sx/2,dy*sy/2
        vs.append((x+a*math.cos(rz)-b*math.sin(rz),y+a*math.sin(rz)+b*math.cos(rz),z+dz*sz/2))
    fs.extend([tuple(start+k for k in f) for f in [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]])

def box(name,p,dims,mat='graphite',coll=bc,parent=project,bevel=.004,slope=False,rz=0):
    vs=[];fs=[]; addbox(vs,fs,p,dims,rz)
    if slope: vs=[(x,y,z+GRADE*(y-YP)) for x,y,z in vs]
    return mesh(name,vs,fs,mat,coll,parent,bevel)

def arc(vs,fs,cy,r0,r1,z0,z1,a0,a1,n=192):
    j=len(vs)
    for i in range(n+1):
        a=a0+(a1-a0)*i/n
        for r,z in [(r0,z0),(r1,z0),(r1,z1),(r0,z1)]:vs.append((CX+r*math.cos(a),cy+r*math.sin(a),z))
    for i in range(n):
        for k in range(4):fs.append((j+4*i+k,j+4*i+(k+1)%4,j+4*(i+1)+(k+1)%4,j+4*(i+1)+k))
    fs.extend([(j+3,j+2,j+1,j),(j+4*n,j+4*n+1,j+4*n+2,j+4*n+3)])

def beam(name,a,b,width,depth,mat='graphite'):
    a,b=Vector(a),Vector(b); mid=(a+b)/2; q=(b-a).to_track_quat('Z','Y')
    vs=[];fs=[];addbox(vs,fs,(0,0,0),(width,depth,(b-a).length))
    vs=[tuple(mid+q@Vector(p)) for p in vs]
    return mesh(name,vs,fs,mat,bevel=.008)

# Restore continuous Project rim outside the tighter entrance, preserving lamps.
src=bpy.data.objects['deck_railing_b']; bm=bmesh.new();bm.from_mesh(src.data);unseen=set(bm.verts)
postvs=[];postfs=[]
while unseen:
    v=unseen.pop(); comp={v}; todo=[v]
    while todo:
        p=todo.pop()
        for e in p.link_edges:
            q=e.other_vert(p)
            if q in unseen:unseen.remove(q);comp.add(q);todo.append(q)
    if len(comp)>24:continue
    pts=[src.matrix_world@v.co for v in comp]; mid=sum(pts,Vector())/len(pts)
    if mid.y<-2.3 and abs(mid.x-CX)<H+.15:continue
    idx={v:len(postvs)+i for i,v in enumerate(comp)}
    postvs += [tuple(src.matrix_world@v.co) for v in comp]
    postfs += [tuple(idx[v] for v in f.verts) for f in {f for v in comp for f in v.link_faces}]
bm.free()
exp_posts=[]
for cy,r,f,theta,suffix,coll,parent in [(0,RP,F,-math.pi/2,'b',pc,project),(CY,RE,F-DROP,math.pi/2,'experience',ec,experience)]:
    gap=math.asin(H/r); a0=theta+gap; a1=theta+math.tau-gap
    vs=[];fs=[]
    for z0,z1 in [(f+.28282,f+.30052),(f+.41542,f+.43312)]:arc(vs,fs,cy,r-.019,r+.019,z0,z1,a0,a1)
    if suffix=='b':
        j=len(vs);vs+=postvs;fs += [tuple(j+k for k in face) for face in postfs]
    else:
        bays=26
        for i in range(1,bays):
            a=a0+(a1-a0)*i/bays;x=CX+r*math.cos(a);y=cy+r*math.sin(a)
            addbox(vs,fs,(x,y,f+.24584),(.05,.05,.41173),a)
            if i in (2,6,10,14,18,22):exp_posts.append((x,y,f+.4517))
    mesh('deck_railing_'+suffix,vs,fs,'mcWood',coll,parent)
    vs=[];fs=[]
    arc(vs,fs,cy,r-.07,r+.08,f-.016,f+.065,a0,a1)
    mesh('deck_parapet_'+suffix,vs,fs,'stationFloorSatin',coll,parent)

# The old mouth lamp is removed as a complete assembly; four new lamps sit on
# the new structural entrance piers. No unsupported lamp survives the resize.
for name in ['deck_lantern_posts_b','deck_lantern_glass_b']:
    ob=bpy.data.objects[name];bm=bmesh.new();bm.from_mesh(ob.data);unseen=set(bm.verts)
    while unseen:
        v=unseen.pop();comp={v};todo=[v]
        while todo:
            p=todo.pop()
            for e in p.link_edges:
                q=e.other_vert(p)
                if q in unseen:unseen.remove(q);comp.add(q);todo.append(q)
        mid=sum((ob.matrix_world@v.co for v in comp),Vector())/len(comp)
        if mid.y<-2.4 and abs(mid.x-(CX+.65))<.08:bmesh.ops.delete(bm,geom=list(comp),context='VERTS')
    bm.to_mesh(ob.data);bm.free()
old=bpy.data.objects.get('deckLight_lantern_4_b')
if old:bpy.data.objects.remove(old,do_unlink=True)

# Bridge slabs use a linear vertical shear: tops/rails slope, posts stay plumb.
MID=(YP+YE)/2
box('bridge_structural_deck',(CX,MID,F-.075),(W,L,.15),'graphite',slope=True)
N=18
for i in range(N):
    y=YE+L*(i+.5)/N
    for side in (-1,1):
        box('bridge_paver_%02d_%s'%(i,side),(CX+side*.177,y,F-.016),(.344,L/N-.006,.032),'stationFloorSatin',bevel=.003,slope=True)
    # Narrow cross bands and sunk fasteners provide scale without raised trips.
    if i%3==0:
        for side in (-1,1):box('bridge_paver_fastener_%s_%s'%(i,side),(CX+side*.307,y,F+.0005),(.014,.014,.002),'metalDark',bevel=.002,slope=True)
for side in (-1,1):
    x=CX+side*H
    box('bridge_edge_kerb_'+str(side),(x,MID,F+.025),(.075,L,.05),'stationFloorSatin',slope=True)
    box('bridge_main_girder_'+str(side),(x,MID,F-.185),(.09,L+.10,.21),'graphite',slope=True)
    for z in (F+.29167,F+.42427):box('bridge_rail_%s_%s'%(side,z),(x,MID,z),(.038,L,.0177),'mcWood',bevel=.002,slope=True)
    for i in range(1,9):
        y=YE+L*i/9
        box('bridge_post_%s_%02d'%(side,i),(x,y,F+.251),( .05,.05,.402),'mcWood',slope=True)
        box('bridge_post_cap_%s_%02d'%(side,i),(x,y,F+.462),(.07,.07,.02),'metalDark',slope=True)
        box('bridge_post_foot_%s_%02d'%(side,i),(x,y,F+.068),(.074,.095,.04),'metalDark',slope=True)
        # Vertical straps visibly clamp each post to the side beam.
        box('bridge_girder_strap_%s_%02d'%(side,i),(x+side*.05,y,F-.17),(.018,.085,.245),'metalDark',slope=True)
        for z in (F-.25,F-.09):box('bridge_strap_bolt_%s_%s_%s'%(side,i,z),(x+side*.063,y,z),(.013,.021,.021),'stationFloorSatin',slope=True)
    for i in range(9):
        y=YE+L*(i+.5)/9
        box('bridge_light_recess_%s_%02d'%(side,i),(x+side*.047,y,F-.17),(.008,L/9-.14,.047),'metalDark',slope=True)
        box('bridge_cyan_inlay_%s_%02d'%(side,i),(x+side*.052,y,F-.17),(.004,L/9-.19,.014),'neonCyan_workshop_cyan',bevel=.001,slope=True)
        box('bridge_inner_edge_light_%s_%02d'%(side,i),(x-side*.040,y,F+.031),(.004,L/9-.17,.009),'neonCyanFaint_workshop_cyan',bevel=.001,slope=True)
for i in range(10):
    y=YE+L*i/9
    box('bridge_crossbearer_%02d'%i,(CX,y,F-.14),(W,.065,.11),'graphite',slope=True)

# Horizontal landing plates bear inside each original stone deck. Sloped members
# terminate exactly at the shared newel centers, without overhanging up-ramps.
for tag,y,f,cy,r,direction,parent in [('project',YP,F,0,RP,-1,project),('experience',YE,F-DROP,CY,RE,1,experience)]:
    box('bridge_threshold_'+tag,(CX,y-direction*.09,f-.024),(W,.18,.048),'stationFloorSatin')
    for side in (-1,1):
        x=CX+side*H
        for j in range(3):
            box('bridge_abutment_%s_%s_%s'%(tag,side,j),(x,y-direction*(.10+.10*j),f-.15-.16*j),(.20+.045*j,.40+.18*j,.16),'stationFloorSatin',bevel=.007)
        box('bridge_newel_'+tag+'_'+str(side),(x,y,f+.235),(.14,.17,.47),'graphite',bevel=.008)
        box('bridge_newel_base_'+tag+'_'+str(side),(x,y,f+.047),(.19,.21,.094),'stationFloorSatin',bevel=.006)
        box('bridge_newel_cap_'+tag+'_'+str(side),(x,y,f+.505),(.20,.21,.04),'stationFloorSatin',bevel=.006)
        box('bridge_newel_cyan_'+tag+'_'+str(side),(x+side*.073,y,f+.32),(.006,.09,.012),'neonCyan_workshop_cyan',bevel=.001)
        # Diagonal knee bears into the actual shaft, not a hanging decorative peg.
        anchor=(x,cy+direction*(r-.66),f-.96)
        tip=(x,y+direction*.57,f-.25)
        beam('bridge_knee_'+tag+'_'+str(side),anchor,tip,.085,.105)
        box('bridge_anchor_shoe_'+tag+'_'+str(side),anchor,(.21,.21,.26),'metalDark',bevel=.008)
        for dz in (-.075,.075):box('bridge_anchor_bolt_'+tag+'_'+str(side)+'_'+str(dz),(x,anchor[1]+direction*.111,anchor[2]+dz),(.025,.012,.025),'stationFloorSatin')
        if tag == 'experience':
            box('bridge_knee_gusset_'+tag+'_'+str(side),(x,y+direction*.45,f-.22),(.15,.27,.16),'metalDark',slope=False)

def lantern(tag,x,y,z,coll,parent):
    box(tag+'_foot',(x,y,z+.01),(.11,.11,.02),'mcWood',coll,parent)
    box(tag+'_glass',(x,y,z+.08),(.075,.075,.12),'lampWarm',coll,parent,.001)
    for dx in (-.043,.043):
        for dy in (-.043,.043):box(tag+'_frame_%s_%s'%(dx,dy),(x+dx,y+dy,z+.08),(.012,.012,.13),'metalDark',coll,parent,.001)
    box(tag+'_roof',(x,y,z+.153),(.125,.125,.026),'mcWood',coll,parent)
    box(tag+'_finial',(x,y,z+.177),(.046,.046,.022),'metalDark',coll,parent)
    ld=bpy.data.lights.new(tag+'_light','POINT');ld.energy=7;ld.color=(1,.62,.22);ld.shadow_soft_size=.08
    ob=bpy.data.objects.new(tag+'_light',ld);coll.objects.link(ob);ob.location=(x,y,z+.08)
    mw=ob.matrix_world.copy();ob.parent=parent;ob.matrix_world=mw
for i,(x,y,z) in enumerate(exp_posts):lantern('experience_lantern_%02d'%i,x,y,z,ec,experience)
for tag,y,f,parent in [('project',YP,F,project),('experience',YE,F-DROP,experience)]:
    for side in (-1,1):lantern('bridge_lantern_%s_%s'%(tag,side),CX+side*H,y,f+.525,bc,parent)

# Reuse the exact concentric inlaid light geometry/material, scaled with paving.
src=bpy.data.objects['deck_runes_b'];ob=src.copy();ob.data=src.data.copy();ob.name='deck_runes_experience';ec.objects.link(ob)
T=Matrix.Translation((CX,CY,-DROP))@Matrix.Diagonal((S,S,1,1))@Matrix.Translation((-CX,0,0))
mw=T@src.matrix_world;ob.parent=experience;ob.matrix_world=mw
for src in list(pc.objects):
    if src.type=='LIGHT' and any(k in src.name for k in ('floor_glow','floor_sheen','rune_')):
        ob=src.copy();ob.data=src.data.copy();ob.name=src.name.replace('_b','_experience');ec.objects.link(ob)
        mw=src.matrix_world.copy();p=mw.translation;p.x=CX+(p.x-CX)*S;p.y=CY+p.y*S;p.z-=DROP;mw.translation=p
        ob.parent=experience;ob.matrix_world=mw;ob.data.energy*=.85

ld=bpy.data.lights.new('bridge_soft_fill','AREA');ld.energy=80;ld.shape='DISK';ld.size=4;ld.color=(.48,.69,1)
ob=bpy.data.objects.new('bridge_soft_fill',ld);bc.objects.link(ob);ob.location=(CX,MID,10.3)
bpy.context.view_layer.update()
bpy.context.scene['experience_bridge_specs']={'width':W,'width_reduction':.35,'experience_radius_scale':S,'drop':DROP,'slope_degrees':math.degrees(ANGLE),'project_end_y':YP,'experience_end_y':YE}
scene=bpy.context.scene;cam=scene.camera
scene.render.resolution_x=1600;scene.render.resolution_y=1200;scene.render.resolution_percentage=100
for view in ('overview','detail','supports'):
    if view=='overview':pos=(37.3,-18,18);target=(CX,-4.65,4.45);scale=16.5
    elif view=='detail':pos=(30,-9.7,12.5);target=(CX,-4.9,6.55);scale=7.8
    else:pos=(31,-5,7.4);target=(CX,-4.9,6.1);scale=7.3
    cam.location=pos;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale
    scene.render.filepath='/Users/danielku/mywebsite/secret-base/bridge-review/experience-1-'+view+'.png'
    bpy.ops.render.render(write_still=True)
