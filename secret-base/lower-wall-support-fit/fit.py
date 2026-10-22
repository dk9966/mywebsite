import bpy, math, json, hashlib
from pathlib import Path
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
P=Path('/Users/danielku/mywebsite/secret-base/lower-wall-support-fit')
original=bpy.data.filepath
mode=bpy.context.mode
if mode!='OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.wm.save_as_mainfile(filepath=str(P/'before-fit.blend'),copy=True,compress=True)
frame=Matrix.Translation((21.299999237,0,0))@Matrix.Rotation(-math.atan2(12,19),4,'Z')
inv=frame.inverted()
rock=bpy.data.objects['150 | continuous cave with oblique carved rooms']
brackets=sorted([o for o in bpy.data.objects if o.name.startswith('Lower | reference large diagonal bracket')],key=lambda o:o.name)
feet=sorted([o for o in bpy.data.objects if o.name.startswith('Lower | reference bracket foot')],key=lambda o:o.name)
changed=[rock]+brackets+feet
def sig(o): return hashlib.sha256(repr(([list(r) for r in o.matrix_world],[tuple(v.co) for v in o.data.vertices])).encode()).hexdigest()
protected={o.name:sig(o) for o in bpy.context.scene.objects if o.type=='MESH' and o not in changed}
for o in changed:
    old=o.data;old.use_fake_user=True;o['before_wall_support_fit_mesh']=old.name;o.data=old.copy()
mx=inv@rock.matrix_world;ix=mx.inverted()
def smooth(t):
    t=max(0,min(1,t));return t*t*(3-2*t)
count=0
for v in rock.data.vertices:
    p=mx@v.co
    w=smooth((p.x-3.8)/1.4)*smooth((11.8-p.x)/1.6)
    w*=smooth((p.z-1.7)/2.3)*smooth((6.60-p.z)/.65)
    w*=smooth((p.y+6)/2)*smooth((2.5-p.y)/2)
    if w>0:
        p.y-=1.8*w;v.co=ix@p;count+=1
rock.data.update();bpy.context.view_layer.update()
# Evaluate displacement too, so the shoes contact the visible rock surface.
deps=bpy.context.evaluated_depsgraph_get();ev=rock.evaluated_get(deps);me=ev.to_mesh()
tree=BVHTree.FromPolygons([inv@ev.matrix_world@v.co for v in me.vertices],[list(f.vertices) for f in me.polygons])
ev.to_mesh_clear()
def points(o):return [inv@o.matrix_world@v.co for v in o.data.vertices]
anchors=[]
for foot in feet:
    ps=points(foot);old=sum(ps,Vector())/len(ps)
    desired=Vector((old.x,-3.7,old.z))
    hit,normal,idx,distance=tree.find_nearest(desired)
    assert hit is not None
    # Small embed makes the pad visibly bear on the faceted wall.
    target=hit-normal*.035
    anchors.append((old,target))
    local=(inv@foot.matrix_world).inverted()
    for v,p in zip(foot.data.vertices,ps):v.co=local@(p+target-old)
    foot.data.update()
for o in brackets:
    ps=points(o);a=sum(ps[:4],Vector())/4;b=sum(ps[4:],Vector())/4
    end=0 if a.z<b.z else 1
    old,target=min(anchors,key=lambda pair:((a if end==0 else b)-pair[0]).length)
    if end==0:a=target
    else:b=target
    axis=(b-a).normalized();u=axis.cross(Vector((0,0,1))).normalized()*.06
    v=axis.cross(u).normalized()*.075
    local=(inv@o.matrix_world).inverted()
    out=[p+su*u+sv*v for p in (a,b) for su,sv in [(-1,-1),(1,-1),(1,1),(-1,1)]]
    for vert,p in zip(o.data.vertices,out):vert.co=local@p
    o.data.update()
bpy.context.view_layer.update()
assert all(sig(bpy.data.objects[n])==s for n,s in protected.items())
report={'pulled_wall_vertices':count,'anchors':[{'before':list(a),'after':list(b),'surface_distance':tree.find_nearest(b)[3]} for a,b in anchors], 'unrelated_meshes_preserved':True}
assert all(a['surface_distance']<.06 for a in report['anchors'])
(P/'verification.json').write_text(json.dumps(report,indent=2))
if mode=='SCULPT':bpy.ops.object.mode_set(mode='SCULPT')
bpy.ops.wm.save_as_mainfile(filepath=original,compress=True)
result=report
