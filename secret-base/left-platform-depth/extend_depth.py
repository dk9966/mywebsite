"""Extend the existing left bay into its rock wall by 1.5 m, preserving the stair connection."""
import bpy,bmesh,json,math,hashlib
import numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent
S=bpy.context.scene
F=Matrix(json.loads((P.parent/'left-platform-display-bay/verification.json').read_text())['frame']); IV=F.inverted()
FLOOR=bpy.data.objects['Front left | beveled rectangle landing']
ROCK=bpy.data.objects['150 | continuous cave with oblique carved rooms']
KEY='Left bay | 1.5 m deeper platform recess'
assert not ROCK.data.shape_keys or KEY not in ROCK.data.shape_keys.key_blocks
assert bpy.context.mode=='OBJECT'
DIST=1.5
bpy.ops.wm.save_as_mainfile(filepath=str(P/'before-extension.blend'),copy=True,compress=True)

def signature(o):
 h=hashlib.sha256(repr(([list(r) for r in o.matrix_world],o.hide_render,o.hide_get(),o.parent.name if o.parent else None)).encode())
 if o.type=='MESH':
  a=np.empty(len(o.data.vertices)*3,dtype=np.float32);o.data.vertices.foreach_get('co',a);h.update(a.tobytes())
  h.update(repr([tuple(p.vertices) for p in o.data.polygons]).encode())
 return h.hexdigest()
before={o.name:signature(o) for o in S.objects}
changed=set();added=[]
def edit(o,fn):
 old=o.data;old.use_fake_user=True;o.data=old.copy()
 mx=IV@o.matrix_world;imx=mx.inverted()
 for v in o.data.vertices:v.co=imx@fn(mx@v.co)
 o.data.update();changed.add(o.name)
def shift(o,dx):
 o.matrix_world=Matrix.Translation(F.to_3x3()@Vector((dx,0,0)))@o.matrix_world
 changed.add(o.name)
def sm(t):
 t=max(0.,min(1.,t));return t*t*(3-2*t)
def recess_x(x):return DIST*(1-sm((x-.0)/4.4))
def deform(p):
 q=p.copy();q.x-=recess_x(p.x);return q
# Only the rear pair of slab corners moves; the original front outline and bevel remain.
def slab(p):
 q=p.copy()
 if p.x<.01:q.x-=DIST
 return q
edit(FLOOR,slab)
# Tall supports, wall skirts, their light fixtures and return wall details move rigidly.
for o in bpy.data.collections['169 | Left platform display bay'].all_objects:
 if 'floor line' not in o.name and 'quiet fitted metal floor panels' not in o.name:shift(o,-DIST)
# Extend both side rail ends; all existing posts keep their original steel dimensions.
rails=bpy.data.collections['167 | Left platform matching steel railings']
for o in rails.objects:
 if 'continuous' in o.name or 'perimeter curb' in o.name:
  def end(p):
   q=p.copy()
   if q.x<.1:q.x-=DIST
   return q
  edit(o,end)
 elif any('post %02d '%n in o.name for n in [1,44]):shift(o,-DIST)
# Three matching posts on each elongated edge retain sub-0.57 m spacing.
for end_number,neighbor in [(1,2),(44,43)]:
 for suffix in ['upright','foot']:
  src=bpy.data.objects['Front left | perimeter post %02d %s'%(end_number,suffix)]
  near=bpy.data.objects['Front left | perimeter post %02d %s'%(neighbor,suffix)]
  def center(ob):return sum((IV@ob.matrix_world@v.co for v in ob.data.vertices),Vector())/len(ob.data.vertices)
  a=center(src);b=center(near)
  for n in range(1,4):
   ob=src.copy();ob.name='Front left | recessed side %02d extra post %d %s'%(end_number,n,suffix);rails.objects.link(ob)
   shift(ob,(b.x-a.x)*n/4);added.append(ob.name)
# Extend the side beams and let the inner underside brackets follow the local rock deformation.
for o in bpy.data.collections['167 | Left platform cliff supports'].objects:
 if o.type!='MESH' or o.hide_render:continue
 ps=[IV@o.matrix_world@v.co for v in o.data.vertices]
 if min(p.x for p in ps)<4.4:edit(o,deform)
# Add deck panels behind the old wall edge, using the existing grid, finish and gap.
tiles=bpy.data.objects['Left bay | quiet fitted metal floor panels']
vs=[];fs=[];mis=[]
TOP=2.536750555038452;DECK=TOP+.014
for ix,(x0,x1) in enumerate([(-DIST,-1.0077),(-1.0077,0)]):
 for iy in range(14):
  ya=iy*.979+.008;yb=min((iy+1)*.979-.008,13.701388-.008)
  xa=x0+.008;xb=x1-.008;off=len(vs)
  vs.extend([(x,y,z) for z in [TOP+.001,DECK] for x,y in [(xa,ya),(xb,ya),(xb,yb),(xa,yb)]])
  fs.extend([tuple(off+i for i in face) for face in [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]])
  mis.extend([(ix+iy*2)%3]*6)
me=bpy.data.meshes.new('Left bay | recessed extension floor panels');mx=tiles.matrix_world.inverted()@F
me.from_pydata([mx@Vector(v) for v in vs],[],fs);me.update()
for mat in tiles.data.materials:me.materials.append(mat)
for face,mi in zip(me.polygons,mis):face.material_index=mi
ob=tiles.copy();ob.data=me;ob.name='Left bay | recessed extension floor panels';tiles.users_collection[0].objects.link(ob);added.append(ob.name)
# The rock deformation is an independent, reversible shape key. It translates the
# fitted wall, then fades into untouched cavern above/below and outside this bay.
old=ROCK.data;old.use_fake_user=True;ROCK.data=old.copy()
keys=ROCK.data.shape_keys.key_blocks;basis=keys[0]
existing_keys=[(k.name,k.value,k.mute,k.relative_key.name) for k in keys]
mixed=[p.co.copy() for p in basis.data]
for k in list(keys)[1:]:
 if k.mute or k.value==0:continue
 assert not k.vertex_group
 for i,p in enumerate(k.data):mixed[i]+=(p.co-k.relative_key.data[i].co)*k.value
key=ROCK.shape_key_add(name=KEY,from_mix=False);key.relative_key=basis;key.value=1
mx=IV@ROCK.matrix_world;imx=mx.inverted();moved=0
for i,co in enumerate(mixed):
 p=mx@co;x,y,z=p
 w=sm((x+6)/2)*sm((y+3)/2)*sm((16.8-y)/2.5)*sm((z+1.6)/3.7)*sm((10.7-z)/3.3)
 dx=-recess_x(x)*w
 if abs(dx)>1e-7:
  key.data[i].co=basis.data[i].co+imx.to_3x3()@Vector((dx,0,0));moved+=1
ROCK.active_shape_key_index=len(keys)-1
changed.add(ROCK.name)
FLOOR['wall_side_extension_m']=DIST
S['left_platform_depth_revision']='Wall side extended 1.5 m, cave and armored bay supports recessed together; stair connection preserved.'
bpy.context.view_layer.update()
assert existing_keys==[(k.name,k.value,k.mute,k.relative_key.name) for k in list(keys)[:-1]]
protected_changes=[name for name,h in before.items() if name not in changed and signature(bpy.data.objects[name])!=h]
assert not protected_changes,protected_changes
# Check every perimeter foot and armored support shoe is still carried by the deck.
ev=FLOOR.evaluated_get(bpy.context.evaluated_depsgraph_get())
floor_tree=BVHTree.FromPolygons([IV@ev.matrix_world@v.co for v in ev.data.vertices],[list(p.vertices) for p in ev.data.polygons])
checks=[]
for o in S.objects:
 if o.type=='MESH' and (o.name in added and 'foot' in o.name or o.name.startswith('Front left | perimeter post') and 'foot' in o.name or o.name.startswith('Left bay | support') and 'bolted floor anchor' in o.name):
  ps=[IV@o.matrix_world@v.co for v in o.data.vertices];c=sum(ps,Vector())/len(ps)
  hit=floor_tree.ray_cast(Vector((c.x,c.y,TOP+.4)),Vector((0,0,-1)),1)[0]
  assert hit is not None,(o.name,list(c));checks.append(o.name)
# Adjacent support ties must still meet the shifted wall.
ev=ROCK.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh()
rt=BVHTree.FromPolygons([IV@ev.matrix_world@v.co for v in me.vertices],[list(p.vertices) for p in me.polygons]);ev.to_mesh_clear()
# Re-seat the return support after the wall's blended deformation.
for suffix in ['', '.001']:
 shoe=bpy.data.objects['Left bay | support 04 embedded rock anchor'+suffix]
 beam=bpy.data.objects['Left bay | support 04 rock standoff'+suffix]
 ps=[IV@shoe.matrix_world@v.co for v in shoe.data.vertices];c=sum(ps,Vector())/len(ps)
 hit=rt.ray_cast(c-Vector((0,1,0)),Vector((0,1,0)),3)[0];assert hit
 shoe.matrix_world=Matrix.Translation(F.to_3x3()@(hit-c))@shoe.matrix_world
 old=beam.data;old.use_fake_user=True;beam.data=old.copy();mx=IV@beam.matrix_world;im=mx.inverted()
 ps=[mx@v.co for v in beam.data.vertices];front=min(p.y for p in ps);rear=max(p.y for p in ps)
 for v,p in zip(beam.data.vertices,ps):
  p.y=front+(p.y-front)/(rear-front)*(hit.y+.065-front);v.co=im@p
 beam.data.update()
bpy.context.view_layer.update()
anchors=[]
for o in bpy.data.collections['169 | Armored channel supports'].objects:
 if 'embedded rock anchor' in o.name:
  ps=[IV@o.matrix_world@v.co for v in o.data.vertices];c=sum(ps,Vector())/len(ps)
  nearest=rt.find_nearest(c);anchors.append({'object':o.name,'distance':nearest[3]})
report={'extension_m':DIST,'middle_landing_width_m':1.34,'landing_widths':DIST/1.34,'changed_existing':sorted(changed & set(before)),'added':added,'terrain_vertices_moved':moved,'shape_key':KEY,'unchanged_other_objects':len(before)-len(changed & set(before)),'floor_support_checks':len(checks),'rock_anchor_distances':anchors,'frame':[list(r) for r in F]}
(P/'verification.json').write_text(json.dumps(report,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(P/'extended-platform.blend'),copy=True,compress=True)
result=report
