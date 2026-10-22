"""Lengthen the upper flight toward the recessed wall and shorten the parallel lower flight."""
import bpy,ast,bmesh,json,math,hashlib
import numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent;S=bpy.context.scene
COL=bpy.data.collections['166 | Left bridge and right-turn steel stairs']
assert not COL.get('rebalanced_for_deeper_wall')
assert bpy.context.mode=='OBJECT'
bpy.ops.wm.save_as_mainfile(filepath=str(P/'before-rebalance.blend'),copy=True,compress=True)
UP=Vector((0,0,1));TAG='left_switchback_generated';MADE=[]
UF=bpy.data.objects['Left stairs | first flight tread 01 frame'].matrix_world.copy()
LF=bpy.data.objects['Left stairs | half-height right-turn landing frame'].matrix_world.copy()
UIV=UF.inverted();LIV=LF.inverted()
BF=Matrix(json.loads((P.parent/'left-platform-display-bay/verification.json').read_text())['frame']);BIV=BF.inverted()
base=json.loads((P.parent/'left-switchback-stairs/radial-entry-report.json').read_text())
H=float(COL['upper_elevation']);L=float(COL['lower_elevation']);OLDMID=float(COL['landing_elevation'])
RISE=(H-L)/28;UGOING=base['upper_run']/14;LGOING=3.06/14
NU=22;NL=6;BRIDGE=1.12;HALF=.67;A=4.18;B=5.52
NEWMID=H-NU*RISE;DZMID=NEWMID-OLDMID
OLDEND=BRIDGE+base['upper_run'];NEWEND=BRIDGE+NU*UGOING
DXY=UF.to_3x3()@Vector(((NU-14)*UGOING,0,0));DXY.z=0
DELTA=DXY+UP*DZMID;NLF=Matrix.Translation(DXY)@LF
STEEL=bpy.data.materials['Metal | dark structural steel'];FRAME_MAT=bpy.data.materials['Bridge | blue gunmetal panel frames'];GRATE=bpy.data.materials['Bridge | graphite open steel grating'];ALLOY=bpy.data.materials['Metal | outer walkway alloy']
FRAME=UF
# Use the existing fabrication helpers, without running the original scene builder.
tree=ast.parse((P.parent/'left-switchback-stairs/build_stairs.py').read_text())
funcs=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('mesh','append_beam','beam')]
exec(compile(ast.Module(body=funcs,type_ignores=[]),'stair_fabrication_helpers','exec'))
def signature(o):
 h=hashlib.sha256(repr(([list(r) for r in o.matrix_world],o.hide_render,o.hide_get(),o.parent.name if o.parent else None, [c.name for c in o.users_collection])).encode())
 if o.type=='MESH':
  a=np.empty(len(o.data.vertices)*3,dtype=np.float32);o.data.vertices.foreach_get('co',a);h.update(a.tobytes());h.update(repr([tuple(p.vertices) for p in o.data.polygons]).encode())
 return h.hexdigest()
before={o.name:signature(o) for o in S.objects};original=list(COL.objects);changed=set();archived=[]
ARCH=bpy.data.collections.new('Archive | stairs before longer upper flight');S.collection.children.link(ARCH);ARCH.hide_render=True;ARCH.hide_viewport=True
# Keep the old fabricated tread meshes as templates so every grate and frame retains its proportions.
templates={(flight,part):bpy.data.objects['Left stairs | %s flight tread 01 %s'%(flight,part)] for flight in ['first','second'] for part in ['frame','open grating','nosing']}
def center(o,iv):
 return sum((iv@o.matrix_world@v.co for v in o.data.vertices),Vector())/len(o.data.vertices)
def archive(o):
 oldname=o.name;changed.add(oldname);archived.append(oldname)
 for c in list(o.users_collection):c.objects.unlink(o)
 ARCH.objects.link(o);o.name='Archive stair rebalance | '+oldname

def translate(o,delta):
 o.matrix_world=Matrix.Translation(delta)@o.matrix_world;changed.add(o.name)
for o in original:
 n=o.name
 if o.hide_render:continue
 replace=('flight tread' in n or 'flight inclined stringer' in n or 'landing support diagonal' in n)
 if 'continuous ' in n and ' rail ' in n:
  side=int(n.split(' rail ')[1].split()[0]);sec=int(n.rsplit('section ',1)[1]);replace=sec==2 or (side==0 and sec==5) or (side==1 and sec==3)
 if 'radial approach guardrail' in n:replace=center(o,UIV).x>BRIDGE+.001
 if 'bolted guardrail upright' in n or 'guardrail mounting shoe' in n:replace=center(o,LIV).y>HALF+.001
 if replace:archive(o);continue
 if any(s in n for s in ['half-height right-turn landing','landing edge girder','landing underside X brace','landing knee brace','triangle ']):translate(o,DELTA)
 elif 'landing support foot' in n:translate(o,DXY)
 elif 'landing support leg' in n:
  old=o.data;old.use_fake_user=True;o.data=old.copy();mx=o.matrix_world;im=mx.inverted();zs=[(mx@v.co).z for v in o.data.vertices];lo=min(zs);hi=max(zs)
  for v in o.data.vertices:
   p=mx@v.co;p+=DXY;p.z+=DZMID*((p.z-lo)/(hi-lo));v.co=im@p
  o.data.update();changed.add(o.name)
 elif ('continuous ' in n and 'section' in n and int(n.rsplit('section ',1)[1])>=3) or 'bolted guardrail upright' in n or 'guardrail mounting shoe' in n:translate(o,DELTA)
 elif any(n.startswith('Left stairs | '+s+'%02d'%i) for s in ['warm lamp ','warm marker '] for i in [2,3]):translate(o,DELTA)
 elif any(n.startswith('Left stairs | '+s+'%02d'%i) for s in ['warm lamp ','warm marker '] for i in [4,5]):translate(o,DXY+LF.to_3x3()@Vector((0,NL*LGOING-3.06,0)))
# Repeat actual templates with the exact existing rise and going; no stretched steps.
for flight,count,going,direction,frame,base_delta in [('first',NU,UGOING,Vector((1,0,0)),UF,Vector()),('second',NL,LGOING,Vector((0,1,0)),NLF,Vector((0,0,DZMID)))]:
 for i in range(count):
  delta=base_delta+direction*(i*going)-UP*(i*RISE)
  for part in ['frame','open grating','nosing']:
   src=templates[(flight,part)];o=src.copy();o.name='Left stairs | %s flight tread %02d %s'%(flight,i+1,part);COL.objects.link(o);o.matrix_world=frame@Matrix.Translation(delta);o['rebalanced_stair_tread']=True;MADE.append(o)
# Inclined beams and handrails are rebuilt with their original thin profiles.
FRAME=UF
for side,y in enumerate([-HALF,HALF]):
 beam('first flight inclined stringer',(BRIDGE,y,H-.11),(NEWEND,y,NEWMID-.11),.048,.19)
 for label,height in [('middle',.295),('top',.55)]:beam('continuous %s rail %d section 2'%(label,side),(BRIDGE,y,H+height),(NEWEND,y,NEWMID+height),.025,.018)
FRAME=NLF
for side,x in enumerate([B,A]):
 beam('second flight inclined stringer',(x,HALF,NEWMID-.11),(x,HALF+NL*LGOING,L-.11),.048,.19)
 sec=5 if side==0 else 3
 for label,height in [('middle',.295),('top',.55)]:beam('continuous %s rail %d section %d'%(label,side,sec),(x,HALF,NEWMID+height),(x,HALF+NL*LGOING,L+height),.025,.018)
for x in [A+.08,B-.08]:beam('landing support diagonal',(x,-HALF+.07,L+.14),(x,HALF-.07,NEWMID-.2),.035,.04)

def post(name,p):
 beam(name+' upright',p-UP*.1,p+UP*.55,.028,.028)
 # Match the normalized 52 x 52 x 24 mm mounting feet.
 beam(name+' foot',p-UP*.055-UP*.012,p-UP*.055+UP*.012,.052,.052,ALLOY,.001)
FRAME=UF
for side,y in enumerate([-HALF,HALF]):
 a=Vector((BRIDGE,y,H));b=Vector((NEWEND,y,NEWMID));intervals=math.ceil((b-a).length/.82)
 for i in range(1,intervals):post('extended upper flight guardrail %d %02d'%(side,i),a.lerp(b,i/intervals))
FRAME=NLF
for side,x in enumerate([B,A]):
 a=Vector((x,HALF,NEWMID));b=Vector((x,HALF+NL*LGOING,L));intervals=math.ceil((b-a).length/.82)
 for i in range(1,intervals+1):post('short lower flight guardrail %d %02d'%(side,i),a.lerp(b,i/intervals))
COL['rebalanced_for_deeper_wall']=True;COL['route']='Fixed radial bridge -> 22 upper steps -> lowered square near wall supports -> 6 parallel lower steps'
COL['landing_elevation']=NEWMID;COL['upper_step_count']=NU;COL['lower_step_count']=NL;COL['steps_per_flight']='22 upper, 6 lower';COL['bottom_flight_parallel_to_long_edge']=True
bpy.context.view_layer.update()
protected_changes=[n for n,h in before.items() if n not in changed and signature(bpy.data.objects[n])!=h]
assert not protected_changes,protected_changes
assert abs(H-NU*RISE-NEWMID)<1e-6 and abs(NEWMID-NL*RISE-L)<1e-6
lower_dir=(BIV.to_3x3()@NLF.to_3x3()@Vector((0,1,0))).normalized();assert abs(lower_dir.x)<1e-5
# The square stays rigid and its four legs still sit on the deck.
FLOOR=bpy.data.objects['Front left | beveled rectangle landing'];ev=FLOOR.evaluated_get(bpy.context.evaluated_depsgraph_get())
ft=BVHTree.FromPolygons([ev.matrix_world@v.co for v in ev.data.vertices],[list(p.vertices) for p in ev.data.polygons]);feet=[]
for o in COL.objects:
 if 'landing support foot' in o.name:
  c=center(o,Matrix.Identity(4));hit=ft.ray_cast(c+UP*.5,-UP,1)[0];assert hit is not None;feet.append(o.name)
report={'upper_steps':NU,'lower_steps':NL,'upper_run_before_m':14*UGOING,'upper_run_after_m':NU*UGOING,'lower_run_before_m':3.06,'lower_run_after_m':NL*LGOING,'rise_m':RISE,'upper_going_m':UGOING,'lower_going_m':LGOING,'landing_z_before':OLDMID,'landing_z_after':NEWMID,'landing_shift_world':list(DELTA),'landing_shift_bay':list(BIV.to_3x3()@DELTA),'lower_run_direction_in_platform_frame':list(lower_dir),'frame':[list(r) for r in BF],'upper_frame':[list(r) for r in UF],'lower_frame':[list(r) for r in NLF],'changed_original':sorted(changed),'archived':archived,'created':[o.name for o in MADE],'unchanged_other_objects':len(before)-len(changed),'landing_feet_checked':len(feet),'protected_changes':protected_changes}
(P/'verification.json').write_text(json.dumps(report,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(P/'rebalanced-stairs.blend'),copy=True,compress=True)
result={k:report[k] for k in ['upper_steps','lower_steps','upper_run_before_m','upper_run_after_m','lower_run_before_m','lower_run_after_m','landing_z_after','landing_shift_bay','lower_run_direction_in_platform_frame','landing_feet_checked','unchanged_other_objects']}
