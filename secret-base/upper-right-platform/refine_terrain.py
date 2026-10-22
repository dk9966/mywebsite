import bpy,bmesh,math,json
from pathlib import Path
from mathutils import Matrix,Vector
P=Path(__file__).resolve().parent;S=bpy.context.scene
D=json.loads((P/'build-report.json').read_text());F=Matrix(D['frame']);IV=F.inverted();H=D['height'];A=D['side_m']/2
wall=bpy.data.objects['150 | continuous cave with oblique carved rooms']
current=wall.data;current.use_fake_user=True
source=bpy.data.meshes[wall['before_upper_right_mesh']]
assert {k.name for k in current.shape_keys.key_blocks}-{k.name for k in source.shape_keys.key_blocks}=={'Upper-right | fitted shoulder and square recess'}
wall.data=source.copy()
def outline(a,b):return [(-a+b,-a),(a-b,-a),(a,-a+b),(a,a-b),(a-b,a),(-a+b,a),(-a,a-b),(-a,-a+b)]
# Preserve the existing sculpt keys while adding local contour rows and a new sculpt.
source=wall.data;source.use_fake_user=True;wall.data=source.copy();wall.data.name='Cave | fitted upper-right gallery shoulder'
key=wall.shape_key_add(name='Upper-right | fitted shoulder and square recess');key.value=0
bm=bmesh.new();bm.from_mesh(wall.data);layers={name:bm.verts.layers.shape[name] for name in bm.verts.layers.shape.keys()};basis=layers['Basis'];MX=IV@wall.matrix_world;IMX=MX.inverted()
values={k.name:k.value for k in wall.data.shape_keys.key_blocks if k.name not in ('Basis',key.name)}
for v in bm.verts:
 p=v[basis].copy()
 for name,val in values.items():p+=(v[layers[name]]-v[basis])*val
 v.co=MX@p
def overlaps(f):
 return all(min(v.co[i] for v in f.verts)<hi and max(v.co[i] for v in f.verts)>lo for i,lo,hi in [(0,-5.0,5.7),(1,-4.7,5.7),(2,9.62,14.7)])
for _ in range(5):
 local={e for f in bm.faces if overlaps(f) for e in f.edges}
 edges=[e for e in local if e.calc_length()>.46]
 if not edges:break
 bmesh.ops.subdivide_edges(bm,edges=edges,cuts=1,use_grid_fill=True)
for z in (9.67,10.1,10.6,11.1,H-.213,H-.199,H+.015,12.3,13.4,14.45):
 faces=[f for f in bm.faces if min(v.co.z for v in f.verts)<z<max(v.co.z for v in f.verts) and overlaps(f)]
 edges={e for f in faces for e in f.edges};verts={v for f in faces for v in f.verts}
 if faces:bmesh.ops.bisect_plane(bm,geom=list(verts)+list(edges)+faces,plane_co=(0,0,z),plane_no=(0,0,1),dist=1e-6,clear_inner=False,clear_outer=False)
def smooth(t):t=max(0,min(1,t));return t*t*(3-2*t)
anchor=Vector((-8,-8));support=outline(A-.12,.24);recess=outline(A+.16,.32)
def ray_interval(p,poly):
 d=Vector((p.x,p.y))-anchor;lo=0.;hi=100.
 for a,b in zip(poly,poly[1:]+poly[:1]):
  ex,ey=b[0]-a[0],b[1]-a[1];s=ex*(anchor.y-a[1])-ey*(anchor.x-a[0]);q=ex*d.y-ey*d.x
  if abs(q)<1e-9:
   if s<0:return None
  elif q>0:lo=max(lo,-s/q)
  else:hi=min(hi,-s/q)
 return (lo,hi) if hi>=lo else None
# Bisect/subdivide do not consistently interpolate shape coordinates. Reconcile
# the interpolated live surface before storing the new additive sculpt delta.
for v in bm.verts:
 current=v[basis].copy()
 for name,val in values.items():current+=(v[layers[name]]-v[basis])*val
 correction=IMX@v.co-current
 for layer in layers.values():v[layer]+=correction
changed=0;maxdelta=0
for v in bm.verts:
 p=v.co.copy();new=p.copy();x,y,z=p
 if -5.2<x<5.8 and -4.9<y<5.8 and 9.67<z<14.45:
  hit=ray_interval(p,support);opening=ray_interval(p,recess)
  if opening:
   lo,hi=hit if hit else (1.,1.);ole,ohi=opening
   if z<=H-.213:
    weight=smooth((z-9.67)/.92);t=min(1.,lo)
    rough=(.048*math.sin(y*3.4+z*2.1)+.035*math.sin(x*4.1-z*2.3))*smooth((H-.38-z)/.5)
    t+=rough/max(1.,(Vector((x,y))-anchor).length)
   elif z<H-.199:
    f=(z-(H-.213))/.014;t=min(1.,lo)*(1-f)+max(1.,ohi)*f;weight=1
   else:t=max(1.,ohi);weight=1-smooth((z-13.35)/1.10)
   # Blend only in a narrow margin around this wall patch.
   weight*=smooth((5.8-max(x,y))/1.05)*smooth((min(x,y)+5.1)/1.0)
   d=Vector((x,y))-anchor;new.x=anchor.x+d.x*(1+(t-1)*weight);new.y=anchor.y+d.y*(1+(t-1)*weight)
 delta=IMX.to_3x3()@(new-p)
 v[layers[key.name]]=v[basis]+delta;v.co=v[basis]
 if delta.length>1e-7:changed+=1;maxdelta=max(maxdelta,delta.length)
bmesh.ops.triangulate(bm,faces=[f for f in bm.faces if len(f.verts)>3]);bm.to_mesh(wall.data);bm.free();wall.data.update();key=wall.data.shape_keys.key_blocks[key.name];key.value=1
# The upper bearing must not be lowered by the separate workshop-roof slider.
ks=wall.data.shape_keys.key_blocks;basis_key=ks['Basis'];attr=wall.data.attributes['roof_clearance_follow']
for i,v in enumerate(wall.data.vertices):
 if (key.data[i].co-basis_key.data[i].co).length>1e-6:
  co=basis_key.data[i].co.copy()
  for k in ks:
   if k!=basis_key:co+=(k.data[i].co-k.relative_key.data[i].co)*k.value
  if (MX@co).z>9.67:attr.data[i].value=0
wall.data.update()
wall['before_upper_right_mesh']=source.name;wall['upper_right_support']='Continuous local faceted shoulder; top bears against beveled square deck; square gallery recess. Reversible shape key.'

bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=str(P/'upper-right-platform-candidate.blend'),copy=True)
result={'changed':changed,'maxdelta':maxdelta,'vertices':len(wall.data.vertices)}
