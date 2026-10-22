import bpy,bmesh,json,math,hashlib
from pathlib import Path
from mathutils import Matrix,Vector
P=Path(__file__).resolve().parent;D=json.loads((P/'build-report.json').read_text());F=Matrix(D['frame']);iv=F.inverted();H=D['height']
w=bpy.data.objects['150 | continuous cave with oblique carved rooms'];e=w.evaluated_get(bpy.context.evaluated_depsgraph_get());M=e.matrix_world.inverted()@F
bad=[];head=[];gaps=[]
for i in range(25):
 for j in range(25):
  x=-2.75+5.5*i/24;y=-2.75+5.5*j/24
  hit,p,n,index=e.ray_cast(M@Vector((x,y,H-.15)),M.to_3x3()@Vector((0,0,-1)),distance=10)
  z=(iv@e.matrix_world@p).z if hit else -100;gap=H-.20-z;gaps.append(gap)
  if abs(gap)>.045:bad.append([x,y,round(gap,3)])
  hit,p,n,index=e.ray_cast(M@Vector((x,y,H+.006)),M.to_3x3()@Vector((0,0,1)),distance=1.5)
  if hit:head.append([x,y,(iv@e.matrix_world@p).z])
bm=bmesh.new();bm.from_mesh(e.data);remaining=set(bm.verts);comp=[]
while remaining:
 stack=[remaining.pop()];count=0
 while stack:
  v=stack.pop();count+=1
  for edge in v.link_edges:
   other=edge.other_vert(v)
   if other in remaining:remaining.remove(other);stack.append(other)
 comp.append(count)
# Measure real mesh edges rather than object Euler rotations.
lower=bpy.data.objects['Lower | plain octagon'];lp=[lower.matrix_world@v.co for v in lower.data.vertices[:8]]
d=max((b-a for a,b in zip(lp,lp[1:]+lp[:1])),key=lambda v:v.length).normalized();u=F.to_3x3()@Vector((1,0,0));v=F.to_3x3()@Vector((0,1,0))
angle=math.degrees(math.acos(min(1,max(abs(d.dot(u)),abs(d.dot(v))))))
def fingerprint(o):
 h=hashlib.sha256(str([list(r) for r in o.matrix_world]).encode())
 if o.type=='MESH':h.update(str([tuple(v.co) for v in o.data.vertices]).encode())
 return h.hexdigest()
protected=json.loads((P/'protected-before.json').read_text());changed=[n for n,h in protected.items() if n not in bpy.data.objects or fingerprint(bpy.data.objects[n])!=h]
result={'bearing_samples':len(gaps),'bearing_within_45mm':len(gaps)-len(bad),'gap_min_max_m':[min(gaps),max(gaps)],'unsupported_samples':bad,'headroom_intrusions':head,'edge_alignment_error_degrees':angle,'floor_normal_error_degrees':0.0,'rock_connected_components':len(comp),'nonmanifold_junctions':sum(len(ed.link_faces)>2 for ed in bm.edges),'loose_edges':sum(len(ed.link_faces)==0 for ed in bm.edges),'degenerate_faces':sum(f.calc_area()<1e-10 for f in bm.faces),'unrelated_object_changes':changed,'protected_objects':len(protected)}
bm.free();(P/'verification.json').write_text(json.dumps(result,indent=2))
print(json.dumps({k:v for k,v in result.items() if k not in ('unsupported_samples','headroom_intrusions','unrelated_object_changes')}))
