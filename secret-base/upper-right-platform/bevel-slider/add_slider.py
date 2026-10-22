"""Native corner-cut slider. Shape keys and drivers need no Python autorun."""
import bpy,math,json
from pathlib import Path
from mathutils import Vector,Matrix
P=Path(__file__).resolve().parent;S=bpy.context.scene
up=bpy.data.objects['Upper | beveled square gallery'];wall=bpy.data.objects['150 | continuous cave with oblique carved rooms'];ctrl=bpy.data.objects['SCENE SLIDERS'];control=ctrl.modifiers['Scene Sliders']
COL=bpy.data.collections['171 | Upper right square gallery']
assert not any(i.name=='Upper corner bevel (m)' for i in control.node_group.interface.items_tree)
F=up.matrix_world.copy();IV=F.inverted();A=float(up['side_m'])/2;H=float(up['deck_height_m']);BASE=.30
socket=control.node_group.interface.new_socket(name='Upper corner bevel (m)',in_out='INPUT',socket_type='NodeSocketFloat')
socket.default_value=BASE;socket.min_value=.10;socket.max_value=1.50
socket.description='Length cut back along each square edge. Larger values make longer diagonal corners. The floor, rim, guardrails, drains and rock bearing follow. Original: 0.30 m.'
control[socket.identifier]=BASE
PATH='modifiers["Scene Sliders"]["'+socket.identifier+'"]'
KEY='Upper corner bevel | follow slider'

def driver(owner,path,expression='v-0.3'):
 fc=owner.driver_add(path);d=fc.driver;d.type='SCRIPTED';d.expression=expression
 var=d.variables.new();var.name='v';var.type='SINGLE_PROP';var.targets[0].id=ctrl;var.targets[0].data_path=PATH
 return fc

def outline(a,b):return [Vector(p) for p in [(-a+b,-a),(a-b,-a),(a,-a+b),(a,a-b),(a-b,a),(-a+b,a),(-a,a-b),(-a,-a+b)]]

def nearest(q,poly):
 best=None
 for i,(a,b) in enumerate(zip(poly,poly[1:]+poly[:1])):
  d=b-a;t=max(0,min(1,(q-a).dot(d)/d.length_squared));p=a+t*d;dist=(q-p).length_squared
  if best is None or dist<best[0]:best=(dist,i,t,p)
 return best

def bary(q,a,b,c):
 u=b-a;v=c-a;w=q-a;den=u.x*v.y-u.y*v.x
 if abs(den)<1e-10:return None
 t=(w.x*v.y-w.y*v.x)/den;s=(u.x*w.y-u.y*w.x)/den
 return (1-t-s,t,s) if t>=-1e-5 and s>=-1e-5 and t+s<=1.00001 else None

def cage(a,b,inner_a=2.18,inner_b=.10):
 outer=outline(a,b);inner=outline(inner_a,inner_b);end=outline(a,b+1);delta=[p-q for p,q in zip(end,outer)];tri=[]
 for i in range(8):
  j=(i+1)%8
  tri.append(((inner[i],outer[i],outer[j]),(Vector((0,0)),delta[i],delta[j])))
  tri.append(((inner[i],outer[j],inner[j]),(Vector((0,0)),delta[j],Vector((0,0)))))
 def response(q,extend=0):
  for coords,ds in tri:
   weights=bary(q,*coords)
   if weights:return sum((d*w for d,w in zip(ds,weights)),Vector((0,0)))
  if extend:
   ds,i,t,p=nearest(q,outer);dist=math.sqrt(ds)
   if dist<extend:return delta[i].lerp(delta[(i+1)%8],t)*(1-dist/extend)
  return Vector((0,0))
 return response

changed=[]
def add_key(o,offsets,expression='v-0.3'):
 if max((p.length for p in offsets),default=0)<1e-8:return
 if o.data.shape_keys is None:o.shape_key_add(name='Basis',from_mix=False)
 assert o.data.shape_keys.key_blocks.get(KEY) is None
 b=o.data.shape_keys.key_blocks['Basis'];k=o.shape_key_add(name=KEY,from_mix=False);k.relative_key=b;k.slider_min=-2;k.slider_max=2
 for v,p,delta in zip(k.data,b.data,offsets):v.co=p.co+delta
 k.value=0;driver(k,'value',expression);o['upper_corner_slider']='SCENE SLIDERS > Scene Sliders > Upper corner bevel (m)';changed.append(o.name)

# The slab's eight defining corners have exact analytic responses.
p0=outline(A,BASE);p1=outline(A,BASE+1);mx=IV@up.matrix_world;inv=mx.inverted().to_3x3();offsets=[]
for v in up.data.vertices:
 q=mx@v.co;i=min(range(8),key=lambda j:(Vector(q[:2])-p0[j]).length_squared);d=p1[i]-p0[i];offsets.append(inv@Vector((d.x,d.y,0)))
add_key(up,offsets)
# A fixed inner floor and a deformable perimeter band keep the central markings square.
floor_response=cage(A-.085,BASE)
rail=outline(A-.075,BASE-.025);rail1=outline(A-.075,BASE-.025+1);rail_delta=[b-a for a,b in zip(rail,rail1)]
rigid_words=('railing upright','railing bolted shoe','recessed edge light housing','cool white edge diffuser')
rail_words=('machined perimeter cap','lower perimeter reveal','continuous guardrail')+rigid_words
for o in COL.objects:
 if o.type!='MESH':continue
 mx=IV@o.matrix_world;inv=mx.inverted().to_3x3();points=[mx@v.co for v in o.data.vertices];offsets=[];expr='v-0.3'
 if 'satin floor plate' in o.name:
  for q in points:
   d=floor_response(Vector(q[:2]));offsets.append(inv@Vector((d.x,d.y,0)))
 elif 'drain' in o.name:
  # At larger bevels, the drain ends stay inside the shortened diagonal corners.
  for q in points:offsets.append(inv@Vector((0,-q.y/2.57,0)))
  expr='max(0.0,v-0.805)'
 elif any(word in o.name for word in rail_words):
  center=sum((Vector(q[:2]) for q in points),Vector((0,0)))/len(points);_,edge,tcenter,_=nearest(center,rail);a,b=rail[edge],rail[(edge+1)%8];vec=b-a
  rigid=any(word in o.name for word in rigid_words)
  for q in points:
   t=tcenter if rigid else max(0,min(1,(Vector(q[:2])-a).dot(vec)/vec.length_squared))
   d=rail_delta[edge].lerp(rail_delta[(edge+1)%8],t);offsets.append(inv@Vector((d.x,d.y,0)))
 else:continue
 add_key(o,offsets,expr)
# Only the upper rock bearing follows the corner cuts; the rest of the cliff retains its sculpt.
dg=bpy.context.evaluated_depsgraph_get();ev=wall.evaluated_get(dg);assert len(ev.data.vertices)==len(wall.data.vertices)
mx=IV@wall.matrix_world;inv=mx.inverted().to_3x3();terrain_response=cage(A-.12,.24,2.12,.10);offsets=[]
def smooth(t):t=max(0,min(1,t));return t*t*(3-2*t)
for vert in ev.data.vertices:
 p=mx@vert.co;d=Vector((0,0))
 if 10.1<p.z<H-.185:
  weight=smooth((p.z-10.1)/1.0);d=terrain_response(Vector(p[:2]),.18)*weight
 offsets.append(inv@Vector((d.x,d.y,0)))
add_key(wall,offsets)
up['corner_bevel_m']=BASE;driver(up,'["corner_bevel_m"]','v');up['shape']='Square with four adjustable short corner cuts'
ctrl['Upper corner bevel help']='Upper corner bevel (m): 0.30 m is the original. Try 0.80 m for longer corners; floor, rails and support follow.'
# Present the existing central slider panel without changing the viewport camera.
for area in bpy.context.screen.areas:
 if area.type=='PROPERTIES':area.spaces.active.pin_id=ctrl;area.spaces.active.context='MODIFIER'
ctrl.update_tag();S.frame_set(S.frame_current);bpy.context.view_layer.update()
result={'slider':socket.name,'identifier':socket.identifier,'range_m':[.10,1.50],'default_m':BASE,'following_objects':len(changed),'objects':changed,'key':KEY,'path':PATH}
(P/'slider.json').write_text(json.dumps(result,indent=2))
t=bpy.data.texts.get('upper_right_add_corner_slider.py') or bpy.data.texts.new('upper_right_add_corner_slider.py');t.clear();t.write(Path(__file__).read_text())
bpy.ops.wm.save_as_mainfile(filepath=str(P/'with-bevel-slider.blend'),copy=True)
result={k:v for k,v in result.items() if k!='objects'}
