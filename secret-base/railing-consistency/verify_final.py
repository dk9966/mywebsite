"""Verify all active railing assemblies against evaluated geometry and save."""
import bpy
import json
import math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

P=Path(__file__).resolve().parent
S=bpy.context.scene
DG=bpy.context.evaluated_depsgraph_get()
UP=Vector((0,0,1))

def points(o):
    e=o.evaluated_get(DG)
    return [e.matrix_world@v.co for v in e.data.vertices]

def center(o):
    v=points(o)
    return sum(v,Vector())/len(v)

posts=[o for o in S.objects if o.visible_get() and 'railing_profile_mm' in o]
feet=[o for o in S.objects if o.visible_get() and 'railing_foot_mm' in o]
assert len(posts)==len(feet) and len(posts)>=169,(len(posts),len(feet))
errors=[]
for o in posts:
    p=center(o)
    f=min(feet,key=lambda f:(center(f).x-p.x)**2+(center(f).y-p.y)**2)
    q=center(f)
    if math.hypot(q.x-p.x,q.y-p.y)>.00025:errors.append(('off_center',o.name,f.name))
    if max(v.z for v in points(o))-min(v.z for v in points(o))<.34:errors.append(('clipped_post',o.name))
    edges=[f.matrix_world.to_3x3()@(f.data.vertices[e.vertices[1]].co-f.data.vertices[e.vertices[0]].co) for e in f.data.edges]
    x=max((d for d in edges if abs(d.z)<.0001),key=lambda d:d.length).normalized()
    vs=points(f)
    sizes=[max(v.dot(a) for v in vs)-min(v.dot(a) for v in vs) for a in (x,UP.cross(x),UP)]
    if max(abs(a-b) for a,b in zip(sizes,(.052,.052,.024)))>.0002:errors.append(('foot_size',f.name,sizes))

vs=[];fs=[]
rails=[o for o in S.objects if o.visible_get() and o.type=='MESH' and
       ('continuous' in o.name and any(k in o.name for k in ['guardrail','rail','rim']) or 'triangle outer rail return' in o.name)]
for o in rails:
    e=o.evaluated_get(DG);offset=len(vs)
    vs.extend(e.matrix_world@v.co for v in e.data.vertices)
    fs.extend(tuple(offset+i for i in p.vertices) for p in e.data.polygons)
tree=BVHTree.FromPolygons(vs,fs)
for o in posts:
    p=center(o);p.z=max(v.z for v in points(o))-.009
    distance=tree.find_nearest(p)[3]
    if distance>.026:errors.append(('rail_contact',o.name,distance))

positions=[(o.name,center(o)) for o in posts]
nearest=sorted(((a-b).length,n,m) for i,(n,a) in enumerate(positions) for m,b in positions[i+1:])
if nearest[0][0]<.4:errors.append(('crowded',nearest[:5]))
invalid=[(o.name,f.data_path) for o in S.objects if o.animation_data for f in o.animation_data.drivers if not f.driver.is_valid]
assert not errors,errors
assert not invalid,invalid
report=json.loads(P.joinpath('verification.json').read_text())
report.update({'active_posts':len(posts),'compact_feet':len(feet),'minimum_post_center_spacing_m':nearest[0][0],
               'closest_pairs':nearest[:8],'foot_centering_checks_passed':len(posts),'top_rail_contact_checks_passed':len(posts),
               'unclipped_upright_checks_passed':len(posts),'invalid_drivers':invalid})
P.joinpath('verification.json').write_text(json.dumps(report,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath,compress=True)
result={k:report[k] for k in ['active_posts','compact_feet','minimum_post_center_spacing_m','top_rail_contact_checks_passed','invalid_drivers']}
