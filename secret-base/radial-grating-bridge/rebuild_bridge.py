"""Straight radial bridge, open steel grating, and aligned welded guardrails.

Run against the live scene after saving before-bridge-fix.blend. Original bridge
objects are retained in a disabled archive. Existing platform controls survive.
"""
import bpy, bmesh, math, json
from pathlib import Path
from mathutils import Vector, Matrix

P = Path('/Users/danielku/mywebsite/secret-base/radial-grating-bridge')
S = bpy.context.scene
FRAME = Matrix.Translation((21.299999237, 0, 0)) @ Matrix.Rotation(-math.atan2(12, 19), 4, 'Z')
INV = FRAME.inverted()
MF, F = 6.871178627, 6.824491024
d = Vector((1, -.625, 0)).normalized()
n = Vector((-d.y, d.x, 0))
UP = Vector((0, 0, 1))
R, HALF = 3.620207, .67
T = math.sqrt(R*R-HALF*HALF)
COL = bpy.data.collections['158 | Connected bridge and railings']
ARCHIVE = bpy.data.collections.get('Archive | bridge before parallel grating')
if not ARCHIVE:
    ARCHIVE = bpy.data.collections.new('Archive | bridge before parallel grating')
    S.collection.children.link(ARCHIVE)
ARCHIVE.hide_viewport = ARCHIVE.hide_render = True

def archive(o):
    if o.name not in ARCHIVE.objects: ARCHIVE.objects.link(o)
    for c in list(o.users_collection):
        if c != ARCHIVE: c.objects.unlink(o)
    o.hide_render = o.hide_viewport = True

# Measure the user's current apron, rather than repeating its old camera warp.
lower = bpy.data.objects['Lower | plain octagon']
ps = [INV @ lower.matrix_world @ v.co for v in lower.data.vertices]
foot = [p.copy() for p in ps if abs(p.z-F)<.001]
assert len(foot) in (8,11), 'Expected the current apron outline, including its latest octagon edit'
edge_a, edge_b = foot[0], foot[-1]
edge = edge_b-edge_a

def cross(a,b): return a.x*b.y-a.y*b.x
def end_s(u): return cross(edge_a-n*u,edge)/cross(d,edge)
def level(s):
    # Finish the slight descent before the oblique landing, for a flush joint.
    return MF+(F-MF)*min(1,max(0,(s-T)/1.12))
def point(s,u,dz=0):
    p=d*s+n*u; p.z=level(s)+dz
    return p

for o in list(COL.objects):
    if o.get('parallel_bridge_generated'):
        bpy.data.objects.remove(o,do_unlink=True)
        continue
    if 'main rim continuous return' not in o.name: archive(o)
# The boolean gate had left two cut-off posts and large shoes in the walkway.
for suffix in ('.026','.027'):
    for prefix in ('Metal | perimeter post','Metal | post bolted foot'):
        ob=bpy.data.objects.get(prefix+suffix)
        if ob and not ob.hide_viewport: archive(ob)
for name in ('Metal | outer rim reinforcement strap.013','Metal | rim strap bolt.026'):
    ob=bpy.data.objects.get(name)
    if ob and not ob.hide_viewport:archive(ob)

steel=bpy.data.materials['Metal | dark structural steel']
alloy=bpy.data.materials['Metal | outer walkway alloy']
def mat(name,color,metal,rough):
    m=bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.diffuse_color=(*color,1); m.use_nodes=True
    p=m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value=(*color,1)
    p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=rough
    return m
grate=mat('Bridge | graphite open steel grating',(.052,.075,.091),.78,.46)
frame=mat('Bridge | blue gunmetal panel frames',(.11,.15,.18),.76,.38)
fastener=mat('Bridge | restrained silver fasteners',(.24,.29,.32),.8,.35)
made=[]

def mesh(name,vs,fs,material,bevel=0,rail=False):
    me=bpy.data.meshes.new(name);me.from_pydata(vs,[],fs);me.update()
    bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
    ob=bpy.data.objects.new(name,me);COL.objects.link(ob);ob.matrix_world=FRAME
    me.materials.append(material)
    if bevel:
        m=ob.modifiers.new('Small fabricated edge radius','BEVEL');m.width=bevel;m.segments=2
        ob.modifiers.new('Fabricated normals','WEIGHTED_NORMAL')
    ob['parallel_bridge_generated']=True
    ob['bridge_rail_height']=rail
    made.append(ob)
    return ob

def append_beam(vs,fs,a,b,width,depth):
    a,b=Vector(a),Vector(b);axis=(b-a).normalized()
    helper=UP if abs(axis.z)<.95 else n
    u=axis.cross(helper).normalized()*width/2
    v=axis.cross(u).normalized()*depth/2
    k=len(vs)
    vs.extend([tuple(p+su*u+sv*v) for p in (a,b) for su,sv in [(-1,-1),(1,-1),(1,1),(-1,1)]])
    fs.extend([tuple(k+i for i in f) for f in [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]])

def beam(name,a,b,width,depth,material,bevel=.0015,rail=False):
    vs=[];fs=[];append_beam(vs,fs,a,b,width,depth)
    return mesh(name,vs,fs,material,bevel,rail)

def sweep(name,ps,width,depth,material,rail=False):
    ps=[Vector(p) for p in ps];vs=[];fs=[(0,3,2,1)]
    for i,p in enumerate(ps):
        before=(ps[i]-ps[i-1]).normalized() if i else (ps[1]-p).normalized()
        after=(ps[i+1]-p).normalized() if i<len(ps)-1 else before
        a=Vector((-before.y,before.x,0)).normalized();b=Vector((-after.y,after.x,0)).normalized()
        q=(a+b).normalized();q*=width/2/max(.25,q.dot(a))
        vs.extend([tuple(p+q*sg+UP*z) for sg,z in [(-1,-depth/2),(1,-depth/2),(1,depth/2),(-1,depth/2)]])
    for i in range(len(ps)-1):
        for j in range(4):fs.append((4*i+j,4*i+(j+1)%4,4*(i+1)+(j+1)%4,4*(i+1)+j))
    fs.append(tuple(range(4*(len(ps)-1),4*len(ps))))
    return mesh(name,vs,fs,material,.0015,rail)

# Structural edges stay exactly parallel in plan; only the landing is mitered.
starts=[point(T,u) for u in (-HALF,HALF)]
ends=[point(end_s(u),u) for u in (-HALF,HALF)]
short=min(end_s(-HALF),end_s(HALF))
long=max(end_s(-HALF),end_s(HALF))
stations=[T+.56*i for i in range(math.ceil((long-T)/.56)) if T+.56*i<long-.16]
for side,u in enumerate((-HALF,HALF)):
    ss=sorted(set([T,T+1.12,end_s(u)]))
    sweep('Bridge | parallel edge stringer %d'%side,[point(s,u,-.078) for s in ss],.06,.145,steel)
    sweep('Bridge | steel edge cap %d'%side,[point(s,u,-.015) for s in ss],.065,.04,frame)

# Full-width cross-members and the exact oblique landing sill.
for i,s in enumerate(stations):
    lo,hi=-HALF,HALF
    if s>short:
        cut=lo+(hi-lo)*(s-end_s(lo))/(end_s(hi)-end_s(lo))
        if end_s(lo)>end_s(hi):hi=cut
        else:lo=cut
    beam('Bridge | transverse panel frame %02d'%i,point(s,lo,-.022),point(s,hi,-.022),.046,.05,frame)
    beam('Bridge | deck cross bearer %02d'%i,point(s,lo,-.094),point(s,hi,-.094),.047,.09,steel)
beam('Bridge | mitered flush landing sill',ends[0]-UP*.022,ends[1]-UP*.022,.05,.05,frame)
for i,u in enumerate((-.22,.22)):
    sweep('Bridge | longitudinal panel divider %d'%i,[point(s,u,-.022) for s in (T,T+1.12,end_s(u))],.023,.045,frame)

# Real open bar grating; no painted tile lines or opaque slab underneath.
vs=[];fs=[]
inner=HALF-.04
count=round(inner*2/.026)
for i in range(1,count):
    u=-inner+2*inner*i/count
    ss=[T+.027,T+1.12,end_s(u)-.027]
    for a,b in zip(ss,ss[1:]):append_beam(vs,fs,point(a,u,-.02),point(b,u,-.02),.0042,.032)
# Transverse bars clipped analytically to the oblique landing boundary.
step=.034
for i in range(1,math.ceil((long-T)/step)):
    s=T+i*step
    if any(abs(s-v)<.028 for v in stations):continue
    lo,hi=-inner,inner
    e0,e1=end_s(lo),end_s(hi)
    if s>max(e0,e1)-.028:continue
    if s>min(e0,e1)-.028:
        cut=lo+(hi-lo)*(s+.028-e0)/(e1-e0)
        if e0>e1:hi=cut
        else:lo=cut
    if hi-lo>.01:append_beam(vs,fs,point(s,lo,-.012),point(s,hi,-.012),.0032,.014)
mesh('Bridge | fine open welded grating',vs,fs,grate)

# One legible X brace below the final bay, visible through the fine grating.
brace_start=T+1.12+.04
for sign in (-1,1):
    a=point(brace_start,sign*(HALF-.075),-.11)
    b=point(end_s(-sign*(HALF-.075))-.07,-sign*(HALF-.075),-.11)
    beam('Bridge | underdeck diagonal X brace',a,b,.048,.045,steel)

# Narrow curved infill follows the circular rim without exposing a gap.
vs=[];fs=[]
for i in range(49):
    u=-HALF+2*HALF*i/48;s0=math.sqrt(R*R-u*u)-.006
    vs.extend([tuple(point(s,u,-.004)) for s in (T-.008,s0)])
for i in range(48):fs.append((2*i,2*i+1,2*i+3,2*i+2))
mesh('Bridge | curved circle threshold',vs,fs,frame)

# Welded handrail runs use the exact same path as their vertical posts.
if len(foot)==8:
    # Terminate at the confirmed rear and diagonal-wall jambs of the octagon.
    front_path=foot[:5]
    rear_path=[foot[-1],foot[-2]]
else:
    front_path=foot[:5]
    rear_path=[foot[-1],Vector((6.3319,-.0252,F))]
paths=[
    [starts[0],point(T+1.12,-HALF),ends[0]]+front_path,
    [starts[1],point(T+1.12,HALF),ends[1]]+rear_path
]
post_records=[]
def post(name,p,tangent):
    tangent=Vector((tangent.x,tangent.y,0)).normalized()
    q=Vector((-tangent.y,tangent.x,0))
    # Both shoes and posts share the rail's tangent and normal.
    for label,sx,sy,z0,z1,material in [('upright',.027,.029,0,.354,steel),('foot',.052,.052,-.011,.013,alloy)]:
        vs=[tuple(p+tangent*x*sx/2+q*y*sy/2+UP*z) for z in (z0,z1) for x,y in [(-1,-1),(1,-1),(1,1),(-1,1)]]
        fs=[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
        mesh(name+' '+label,vs,fs,material,.0015,label=='upright')
    post_records.append({'name':name,'point':list(p)})

for side,path in enumerate(paths):
    for h in (.19,.345):sweep('Lower | aligned continuous rail %d %.3f'%(side,h),[p+UP*h for p in path],.025,.018,steel,True)
    # Curb on the apron only, keeping the open bridge edge light.
    sweep('Lower | aligned perimeter curb %d'%side,[p-UP*.014 for p in path[2:]],.044,.042,steel)
    u=(-HALF,HALF)[side]
    ss=[s for s in stations if s<end_s(u)-.15]+[end_s(u)]
    for j,s in enumerate(ss):post('Bridge | aligned post %d %02d'%(side,j),point(s,u),d)
    for j,(a,b) in enumerate(zip(path[2:],path[3:])):
        count=max(1,math.ceil((b-a).length/.57))
        # The landing already has a bridge post; no doubled joints.
        for k in range(1,count+1):
            post('Lower | aligned perimeter post %d %02d %02d'%(side,j,k),a.lerp(b,k/count),b-a)

# Close the two remaining rim-return supports; entrance supports are shared.
for i,a in enumerate((math.radians(-10),math.radians(1.5))):
    p=Vector((R*math.cos(a),R*math.sin(a),MF))
    post('Bridge | aligned circle return post %d'%i,p,Vector((-math.sin(a),math.cos(a),0)))

# Native controls: translate only along the span, so a width change cannot
# flare either side of the bridge. The octagon end remains anchored.
ctrl=bpy.data.objects['SCENE SLIDERS'];cm=ctrl.modifiers['Scene Sliders']
w0,h0=float(cm['Socket_7']),float(cm['Socket_3'])
g=bpy.data.node_groups.new('Bridge | straight radial endpoint control','GeometryNodeTree')
g.interface.new_socket(name='Geometry',in_out='INPUT',socket_type='NodeSocketGeometry')
g.interface.new_socket(name='Geometry',in_out='OUTPUT',socket_type='NodeSocketGeometry')
rd=g.interface.new_socket(name='Radial entrance shift',in_out='INPUT',socket_type='NodeSocketFloat')
hs=g.interface.new_socket(name='Railing height delta',in_out='INPUT',socket_type='NodeSocketFloat')
nodes,links=g.nodes,g.links
gi=nodes.new('NodeGroupInput');go=nodes.new('NodeGroupOutput')
wa=nodes.new('GeometryNodeInputNamedAttribute');wa.data_type='FLOAT';wa.inputs['Name'].default_value='main_connection'
ha=nodes.new('GeometryNodeInputNamedAttribute');ha.data_type='FLOAT';ha.inputs['Name'].default_value='rail_height'
mul=nodes.new('ShaderNodeMath');mul.operation='MULTIPLY';links.new(wa.outputs['Attribute'],mul.inputs[0]);links.new(gi.outputs[rd.name],mul.inputs[1])
shift=nodes.new('ShaderNodeVectorMath');shift.operation='SCALE';shift.inputs[0].default_value=d;links.new(mul.outputs[0],shift.inputs['Scale'])
hm=nodes.new('ShaderNodeMath');hm.operation='MULTIPLY';links.new(ha.outputs['Attribute'],hm.inputs[0]);links.new(gi.outputs[hs.name],hm.inputs[1])
z=nodes.new('ShaderNodeCombineXYZ');links.new(hm.outputs[0],z.inputs['Z'])
add=nodes.new('ShaderNodeVectorMath');add.operation='ADD';links.new(shift.outputs[0],add.inputs[0]);links.new(z.outputs[0],add.inputs[1])
sp=nodes.new('GeometryNodeSetPosition');links.new(gi.outputs['Geometry'],sp.inputs['Geometry']);links.new(add.outputs[0],sp.inputs['Offset']);links.new(sp.outputs['Geometry'],go.inputs['Geometry'])
for ob in made:
    iscircle='circle return' in ob.name
    wa=ob.data.attributes.new('main_connection','FLOAT','POINT');ha=ob.data.attributes.new('rail_height','FLOAT','POINT')
    for i,v in enumerate(ob.data.vertices):
        s,u=v.co.dot(d),v.co.dot(n)
        weight=max(0,min(1,(end_s(u)-s)/max(.05,end_s(u)-T))) if abs(u)<HALF+.08 and s>=T-.08 else 0
        wa.data[i].value=1 if iscircle else weight
        base=level(s) if weight>0 else (MF if 'circle return' in ob.name else F)
        ha.data[i].value=max(0,v.co.z-base) if ob['bridge_rail_height'] else 0
    mod=ob.modifiers.new('Keep bridge straight and rail height linked','NODES')
    if iscircle:
        mod.node_group=bpy.data.node_groups['Lower bridge | preserve live connections']
        ins={s.name:s.identifier for s in mod.node_group.interface.items_tree if s.item_type=='SOCKET' and s.in_out=='INPUT'}
        radial_socket=ins['Main radial shift'];height_socket=ins['Railing height delta']
        radial_expression=f'(v-{w0})*3.549'
    else:
        mod.node_group=g;radial_socket=rd.identifier;height_socket=hs.identifier
        radial_expression=f'sqrt(max(0.01,({R}+(v-{w0})*3.549)**2-{HALF**2}))-{T}'
    for sock,key,expression in [(radial_socket,'Socket_7',radial_expression),(height_socket,'Socket_3',f'v/{h0}-1')]:
        mod[sock]=0.
        dr=mod.driver_add('["'+sock+'"]').driver;dr.expression=expression
        var=dr.variables.new();var.name='v';var.type='SINGLE_PROP';var.targets[0].id=ctrl;var.targets[0].data_path='modifiers["Scene Sliders"]["'+key+'"]'
ctrl.update_tag();S.frame_set(S.frame_current);bpy.context.view_layer.update()
report={'width':2*HALF,'radial_axis':list(d),'starts':[list(p) for p in starts],'ends':[list(p) for p in ends],'edge_parallel_error':abs(cross(ends[0]-starts[0],ends[1]-starts[1])),'radial_error':abs(cross((starts[0]+starts[1])/2,d)),'post_count':len(post_records),'posts':post_records,'generated_objects':len(made),'grating_has_open_holes':True}
P.joinpath('geometry-report.json').write_text(json.dumps(report,indent=2))
S['bridge_revision']='Constant-width radial steel grating bridge, exact apron intersection, aligned welded rails.'
result={k:v for k,v in report.items() if k!='posts'}
