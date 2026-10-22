"""Add a half-length radial grating bridge beside the middle-platform table."""
import bpy, bmesh, math, json
from pathlib import Path
from mathutils import Vector, Matrix
P = Path(__file__).resolve().parent
S = bpy.context.scene
assert bpy.context.mode == 'OBJECT'
assert '181 | Right radial half bridge' not in bpy.data.collections
bpy.ops.wm.save_as_mainfile(filepath=str(P/'before-half-bridge.blend'), copy=True)
DG = bpy.context.evaluated_depsgraph_get()
RIG = bpy.data.objects['Rig | middle radius']
C = RIG.matrix_world.translation.copy(); C.z = 0
RIM = bpy.data.objects['Metal | upper rolled rim']
e = RIM.evaluated_get(DG)
R = max(math.hypot(*(e.matrix_world@v.co-C)[:2]) for v in e.data.vertices)
e = bpy.data.objects['Metal | outer walkway plate'].evaluated_get(DG)
H = max((e.matrix_world@v.co).z for v in e.data.vertices)
# The existing rear bridge supplies the full-length reference.
e = bpy.data.objects['Rear left | bridge edge cap'].evaluated_get(DG)
rear = Vector((-.284576833,.958653212,0)).normalized()
ss = [(e.matrix_world@v.co-C).dot(rear) for v in e.data.vertices]
L = (max(ss)-min(ss))/2
HALF = .59
# Right and slightly behind center, beside the table, radial to the circle.
angle = -math.atan2(12,19) + math.pi/4
D = Vector((math.cos(angle),math.sin(angle),0))
F = Matrix.Translation(C) @ Matrix.Rotation(angle,4,'Z')
INV = F.inverted(); UP=Vector((0,0,1))
COL = bpy.data.collections.new('181 | Right radial half bridge'); S.collection.children.link(COL)
root = bpy.data.objects.new('Right half bridge | radial assembly',None);COL.objects.link(root)
root.parent=RIG;root.matrix_parent_inverse=RIG.matrix_world.inverted();root.matrix_world=F
ctrl=bpy.data.objects['SCENE SLIDERS'];cm=ctrl.modifiers['Scene Sliders']
w0=float(cm['Socket_7']);rail0=float(cm['Socket_3'])
gn=next(m for m in RIM.modifiers if m.type=='NODES')
scale=(RIM.matrix_world.to_3x3()@Vector((1,0,0))).length
radius_delta=scale*float(gn['Socket_5'])
def drive(owner,path,expression,socket,index=None):
 fc=owner.driver_add(path) if index is None else owner.driver_add(path,index)
 dr=fc.driver;dr.type='SCRIPTED';dr.expression=expression
 v=dr.variables.new();v.name='w';v.type='SINGLE_PROP';v.targets[0].id=ctrl;v.targets[0].data_path='modifiers["Scene Sliders"]["'+socket+'"]'
for axis in (0,1):drive(root,'location',f'{C[axis]:.12f}+{D[axis]*radius_delta:.12f}*(w-{w0:.12f})','Socket_7',axis)
rails=bpy.data.objects.new('Right half bridge | railing height',None);COL.objects.link(rails);rails.parent=root;rails.location.z=H
drive(rails,'scale',f'w/{rail0:.12f}','Socket_3',2)
STEEL=bpy.data.materials['Metal | dark structural steel']
FRAME=bpy.data.materials['Bridge | blue gunmetal panel frames']
GRATE=bpy.data.materials['Bridge | graphite open steel grating']
ALLOY=bpy.data.materials['Bridge | restrained silver fasteners']
made=[]
def mesh(name,vs,fs,mat=STEEL,bevel=0,rail=False):
 me=bpy.data.meshes.new('Right half bridge | '+name);me.from_pydata(vs,[],fs);me.update()
 bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
 ob=bpy.data.objects.new('Right half bridge | '+name,me);COL.objects.link(ob);ob.parent=rails if rail else root
 me.materials.append(mat)
 if bevel:
  mod=ob.modifiers.new('Fabricated edge radius','BEVEL');mod.width=bevel;mod.segments=2
  ob.modifiers.new('Weighted steel normals','WEIGHTED_NORMAL')
 made.append(ob);return ob

def append_beam(vs,fs,a,b,w,h):
 a,b=Vector(a),Vector(b);axis=(b-a).normalized();helper=UP if abs(axis.z)<.95 else Vector((0,1,0))
 u=axis.cross(helper).normalized()*w/2;v=axis.cross(u).normalized()*h/2;k=len(vs)
 vs.extend([tuple(p+i*u+j*v) for p in (a,b) for i,j in [(-1,-1),(1,-1),(1,1),(-1,1)]])
 fs.extend([tuple(k+i for i in f) for f in [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]])
def beam(name,a,b,w,h,mat=STEEL,bevel=.0015,rail=False):
 vs=[];fs=[];append_beam(vs,fs,a,b,w,h);return mesh(name,vs,fs,mat,bevel,rail)
def prism(name,x0,x1,y0,y1,z0,z1,mat=STEEL):
 vs=[(x,y,z) for z in (z0,z1) for x,y in [(x0,y0),(x1,y0),(x1,y1),(x0,y1)]]
 return mesh(name,vs,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],mat,.001)

START=math.sqrt(R*R-HALF*HALF)-.055
END=R+L
cuts=[START]+[R+L*i/3 for i in range(1,4)]
deck=[]
for i,(a,b) in enumerate(zip(cuts,cuts[1:])):
 vs=[];fs=[]
 for p,q in [((a,-HALF,H-.023),(a,HALF,H-.023)),((b,-HALF,H-.023),(b,HALF,H-.023)),((a,-HALF,H-.023),(b,-HALF,H-.023)),((a,HALF,H-.023),(b,HALF,H-.023))]:append_beam(vs,fs,p,q,.035,.046)
 deck.append(mesh(f'bay {i+1:02d} cassette frame',vs,fs,FRAME,.0015))
 vs=[];fs=[]
 count=round(2*HALF/.036)
 for j in range(1,count):
  u=-HALF+2*HALF*j/count;append_beam(vs,fs,(a+.018,u,H-.017),(b-.018,u,H-.017),.0042,.030)
 count=round((b-a)/.037)
 for j in range(1,count):
  x=a+(b-a)*j/count;append_beam(vs,fs,(x,-HALF+.018,H-.009),(x,HALF-.018,H-.009),.0032,.014)
 deck.append(mesh(f'bay {i+1:02d} open welded grating',vs,fs,GRATE))
 for sign in (-1,1):deck.append(beam(f'bay {i+1:02d} underdeck X brace', (a+.05,sign*(HALF-.05),H-.11),(b-.05,-sign*(HALF-.05),H-.11),.028,.034))
for side,u in enumerate((-HALF,HALF)):
 deck.append(beam(f'side {side} edge stringer',(START,u,H-.09),(END,u,H-.09),.06,.16))
 deck.append(beam(f'side {side} edge cap',(START,u,H-.018),(END,u,H-.018),.055,.036,FRAME))
for i,x in enumerate(cuts[1:]):deck.append(beam(f'cross bearer {i}',(x,-HALF,H-.10),(x,HALF,H-.10),.047,.09))
# Cut deck parts to the existing live rim without modifying their source meshes.
cut=bpy.data.objects['Bridge circle | hidden rim-following cut']
for ob in deck:
 mod=ob.modifiers.new('Flush circular platform joint','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cut
 if 'grating' in ob.name:mod.use_self=True

# A duplicate of the established curved end frame shares its live rim driver.
ref=bpy.data.objects['Bridge circle | rear flush curved end frame']
join=ref.copy();join.data=ref.data.copy();join.name='Right half bridge | flush curved end frame';COL.objects.link(join)
rot=Matrix.Translation(C)@Matrix.Rotation(angle-math.atan2(rear.y,rear.x),4,'Z')@Matrix.Translation(-C)
join.matrix_world=rot@ref.matrix_world
made.append(join)

# Open the existing perimeter rails using a removable modifier.
gate=prism('hidden railing entrance cutter',R-.43,R+.16,-HALF+.014,HALF-.014,H-.031,H+.85)
gate.hide_render=True;gate.hide_set(True);gate.display_type='WIRE'
affected=[]
for ob in bpy.data.collections['03 | Uniform slender steel railings'].objects:
 if ob.type!='MESH' or ob.hide_render or not ob.visible_get():continue
 e=ob.evaluated_get(DG);ps=[INV@e.matrix_world@v.co for v in e.data.vertices]
 if any(R-.45<p.x<R+.18 and abs(p.y)<HALF+.06 for p in ps):
  mod=ob.modifiers.new('Right half bridge entrance','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=gate;affected.append(ob.name)

# Side rails continue back to the circular guardrail and finish at the half span.
guard=bpy.data.objects['Metal | continuous steel guardrail.001'].evaluated_get(DG)
guardR=max(math.hypot(*(guard.matrix_world@v.co-C)[:2]) for v in guard.data.vertices)
railstart=math.sqrt(guardR*guardR-HALF*HALF)-.007
for side,u in enumerate((-HALF,HALF)):
 for h in (.19,.345):beam(f'side {side} continuous rail {h}',(railstart,u,h),(END,u,h),.025,.018,rail=True)
 count=math.ceil((END-railstart)/.68)
 for i in range(count+1):
  x=railstart+(END-railstart)*i/count
  beam(f'side {side} post {i:02d}',(x,u,0),(x,u,.354),.028,.028,rail=True)
  prism(f'side {side} compact shoe {i:02d}',x-.026,x+.026,u-.026,u+.026,H-.012,H+.012,ALLOY)

bpy.context.view_layer.update();S.frame_set(S.frame_current)
root['Length outside rim (m)']=L;root['Reference full bridge length (m)']=2*L
root['Radial direction']=list(D);root['Purpose']='Half-length open-ended bridge beside the middle-platform table.'
COL['description']='Matching steel grating, three framed bays, X bracing and slender side railings; radial entrance and open half-span tip.'
report={'radius':R,'floor_height':H,'length':L,'width':2*HALF,'direction':list(D),'objects':[o.name for o in made],'railing_opening_objects':affected,'file':bpy.data.filepath}
(P/'build-report.json').write_text(json.dumps(report,indent=2))
result=report
