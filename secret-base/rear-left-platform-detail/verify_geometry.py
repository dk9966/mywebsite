import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent
r=json.loads((P/'verification.json').read_text());F=Matrix(r['frame']);iv=F.inverted();H=r['floor_height']
bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();w=bpy.data.objects['150 | continuous cave with oblique carved rooms'];e=w.evaluated_get(dg)
tree=BVHTree.FromPolygons([iv@e.matrix_world@v.co for v in e.data.vertices],[list(p.vertices) for p in e.data.polygons])
def inside(x,y,poly):return all((b[0]-a[0])*(y-a[1])-(b[1]-a[1])*(x-a[0])>0.035 for a,b in zip(poly,poly[1:]+poly[:1]))
hits=[];samples=0
for poly,z,label in [(r['upper_polygon'],8.7,'upper'),(r['landing_polygon'],H,'landing')]:
 for i in range(81):
  x=-2.3+i*.06
  for j in range(155):
   y=-2.4+j*.06
   if not inside(x,y,poly):continue
   samples+=1;hit,*_=tree.ray_cast(Vector((x,y,z+.006)),Vector((0,0,1)),.25)
   if hit:hits.append((label,x,y,list(hit)))
for i in range(18):
 z=H+(8.7-H)*(i+1)/18;y=(i+.5)*r['stair_run']/18
 for j in range(51):
  x=-1.86+j*3.72/50;samples+=1;hit,*_=tree.ray_cast(Vector((x,y,z+.006)),Vector((0,0,1)),.18)
  if hit:hits.append(('stairs',x,y,list(hit)))
r['walking_surface_rock_clearance_samples']=samples;r['rock_surface_intrusions']=hits
r['closed_mesh_checks']={}
for n in ['Rear left | connected broad stair body','Rear left | one-piece chamfered T landing','Rear left | upper connected platform','Rear left | curved flush center threshold']:
 bm=bmesh.new();bm.from_mesh(bpy.data.objects[n].data);r['closed_mesh_checks'][n]={'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),'zero_area_faces':sum(f.calc_area()<1e-10 for f in bm.faces)};bm.free()
# Check the evaluated original guardrails after the entrance cutter.
rail_hits=[];BF=Matrix(r['bridge_frame']);bb=(F@BF).inverted()
for name in r['aperture_objects']:
 o=bpy.data.objects[name].evaluated_get(dg)
 pts=[bb@o.matrix_world@v.co for v in o.data.vertices]
 if any(abs(p.x)<.54 and r['bridge_start']-.2<p.y<r['bridge_start']+.18 and H+.05<p.z<H+.33 for p in pts):rail_hits.append(name)
r['bridge_clearance_guardrail_intrusions']=rail_hits
(P/'verification.json').write_text(json.dumps(r,indent=2))
result={'rock_clearance_samples':samples,'rock_intrusions':len(hits),'first_hits':hits[:3],'guardrail_intrusions':rail_hits,'closed_mesh_checks':r['closed_mesh_checks']}
