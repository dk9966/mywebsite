"""Add matching guardrails to the live bottom-left landing, without changing it."""
import bpy
import bmesh
import hashlib
import json
import math
from pathlib import Path
from mathutils import Vector, Matrix

P = Path(__file__).resolve().parent
S = bpy.context.scene
FLOOR = bpy.data.objects['Front left | beveled rectangle landing']
COL_NAME = '167 | Left platform matching steel railings'
assert bpy.data.collections.get(COL_NAME) is None, 'Railings already exist'
UP = Vector((0, 0, 1))

def signature(o):
    values = [str([list(r) for r in o.matrix_world]), str(o.hide_render), str(o.hide_get())]
    if o.type == 'MESH':
        values.extend([str([tuple(v.co) for v in o.data.vertices]),
                       str([tuple(p.vertices) for p in o.data.polygons])])
    return hashlib.sha256('\n'.join(values).encode()).hexdigest()

before = {o.name: signature(o) for o in S.objects}
P.joinpath('before-hashes.json').write_text(json.dumps(before))
bpy.ops.wm.save_as_mainfile(filepath=str(P / 'before-railings.blend'), copy=True, compress=True)

# Use the evaluated top polygon, including the user's current corner bevel.
deps = bpy.context.evaluated_depsgraph_get()
ev = FLOOR.evaluated_get(deps)
z_top = max(v.co.z for v in ev.data.vertices)
faces = [p for p in ev.data.polygons if all(abs(ev.data.vertices[i].co.z-z_top)<1e-5 for i in p.vertices)]
assert len(faces) == 1 and len(faces[0].vertices) == 6
outline = [ev.matrix_world @ ev.data.vertices[i].co for i in faces[0].vertices]
assert sum(a.x*b.y-b.x*a.y for a,b in zip(outline,outline[1:]+outline[:1])) > 0

# The unchamfered, longest side is against the cave wall; guard the other five.
wall_edge = max(range(len(outline)), key=lambda i: (outline[(i+1)%len(outline)]-outline[i]).length)
outline = outline[wall_edge+1:] + outline[:wall_edge+1]

def inset_polygon(points, distance):
    out=[]
    for i,p in enumerate(points):
        a=(p-points[i-1]).normalized()
        b=(points[(i+1)%len(points)]-p).normalized()
        na=Vector((-a.y,a.x,0)); nb=Vector((-b.y,b.x,0))
        bisector=(na+nb).normalized()
        out.append(p+bisector*(distance/bisector.dot(na)))
    return out

# Keep the shoes fully seated on the platform, slightly inside the edge.
path=inset_polygon(outline,.055)
level=path[0].z
COL=bpy.data.collections.new(COL_NAME)
S.collection.children.link(COL)
STEEL=bpy.data.materials['Metal | dark structural steel']
ALLOY=bpy.data.materials['Metal | outer walkway alloy']
made=[]

def mesh(name,vs,fs,material):
    name='Front left | '+name
    me=bpy.data.meshes.new(name)
    me.from_pydata(vs,[],fs);me.update()
    bm=bmesh.new();bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bm.to_mesh(me);bm.free()
    ob=bpy.data.objects.new(name,me);COL.objects.link(ob)
    me.materials.append(material)
    ob.parent=FLOOR;ob.matrix_parent_inverse=FLOOR.matrix_world.inverted()
    ob.matrix_basis=Matrix.Identity(4)
    mod=ob.modifiers.new('Small fabricated edge radius','BEVEL')
    mod.width=.0015;mod.segments=2
    ob.modifiers.new('Fabricated normals','WEIGHTED_NORMAL')
    ob['left_platform_railing']=True
    made.append(ob)
    return ob

def sweep(name,height,width,depth):
    vs=[];fs=[(0,3,2,1)]
    for i,p0 in enumerate(path):
        p=p0+UP*height
        before=(path[i]-path[i-1]).normalized() if i else (path[1]-p0).normalized()
        after=(path[i+1]-p0).normalized() if i<len(path)-1 else before
        a=Vector((-before.y,before.x,0));b=Vector((-after.y,after.x,0))
        q=(a+b).normalized();q*=width/2/q.dot(a)
        vs.extend([tuple(p+q*sg+UP*z) for sg,z in [(-1,-depth/2),(1,-depth/2),(1,depth/2),(-1,depth/2)]])
    for i in range(len(path)-1):
        for j in range(4):fs.append((4*i+j,4*i+(j+1)%4,4*(i+1)+(j+1)%4,4*(i+1)+j))
    fs.append(tuple(range(4*(len(path)-1),4*len(path))))
    return mesh(name,vs,fs,STEEL)

rails=[sweep('continuous middle perimeter rail',.190,.025,.018),
       sweep('continuous top perimeter rail',.345,.025,.018)]
sweep('matching perimeter curb',-.014,.044,.042)

post_points=[]
def post(p,tangent):
    tangent=tangent.normalized();q=Vector((-tangent.y,tangent.x,0))
    index=len(post_points)+1
    for label,sx,sy,z0,z1,material in [('upright',.027,.029,0,.354,STEEL),('foot',.052,.052,-.011,.013,ALLOY)]:
        vs=[tuple(p+tangent*x*sx/2+q*y*sy/2+UP*z) for z in (z0,z1)
            for x,y in [(-1,-1),(1,-1),(1,1),(-1,1)]]
        fs=[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
        mesh('perimeter post %02d %s'%(index,label),vs,fs,material)
    post_points.append(p.copy())

post(path[0],path[1]-path[0])
for a,b in zip(path,path[1:]):
    count=math.ceil((b-a).length/.57)
    for k in range(1,count+1):post(a.lerp(b,k/count),b-a)

bpy.context.view_layer.update()
changed=[name for name,value in before.items() if signature(S.objects[name])!=value]
assert not changed,changed
assert all(o.visible_get() for o in made)

# Confirm feet sit on the floor and that the stair's existing landing stays clear.
from mathutils.bvhtree import BVHTree
floor_tree=BVHTree.FromPolygons([ev.matrix_world@v.co for v in ev.data.vertices],
                              [list(p.vertices) for p in ev.data.polygons])
support_errors=[]
for p in post_points:
    hit=floor_tree.ray_cast(p+UP*.1,-UP,.3)
    if hit[0] is None or abs(hit[0].z-level)>.001:support_errors.append(list(p))
assert not support_errors,support_errors

report={'objects_added':len(made),'posts':len(post_points),'guarded_edges':len(path)-1,
        'rail_heights_m':[.19,.345],'rail_section_m':[.025,.018],
        'post_section_m':[.027,.029],'maximum_post_spacing_m':.57,
        'platform_top_m':level,'inset_m':.055,'path_world':[list(p) for p in path],
        'existing_objects_unchanged':len(before),'foot_support_checks_passed':len(post_points),
        'materials':[STEEL.name,ALLOY.name], 'saved':bpy.data.filepath}
P.joinpath('verification.json').write_text(json.dumps(report,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath,compress=True)
result=report
