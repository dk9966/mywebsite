"""Fit the existing cave to the left landing and add cliff-anchored steel brackets.
Run against before-left-fit.blend; sculpt remains adjustable as a shape key.
"""
import bpy, bmesh, json, math, hashlib
import numpy as np
from pathlib import Path
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

P = Path(__file__).resolve().parent
S = bpy.context.scene
rock = bpy.data.objects['150 | continuous cave with oblique carved rooms']
floor = bpy.data.objects['Front left | beveled rectangle landing']
FRAME = Matrix(json.loads((P/'surface-before.json').read_text())['frame'])
INV = FRAME.inverted()
TOP = max((floor.matrix_world @ v.co).z for v in floor.data.vertices)
BOTTOM = min((floor.matrix_world @ v.co).z for v in floor.data.vertices)
WIDTH, LENGTH = json.loads((P/'surface-before.json').read_text())['dimensions']
if bpy.context.mode != 'OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')

def signature(o):
    h=hashlib.sha256()
    h.update(repr([list(row) for row in o.matrix_world]).encode())
    if o.type=='MESH':
        a=np.empty(len(o.data.vertices)*3,dtype=np.float32)
        o.data.vertices.foreach_get('co',a)
        h.update(a.tobytes())
    return h.hexdigest()
protected={o.name:signature(o) for o in S.objects if o != rock}
old = rock.data
old.use_fake_user = True
rock['before_left_platform_fit_mesh'] = old.name
rock.data = old.copy()
rock.data.name = 'Cave | locally refined left platform shoulder'
mx = INV @ rock.matrix_world
ix = mx.inverted()
bm = bmesh.new(); bm.from_mesh(rock.data)
for vert in bm.verts: vert.co = mx @ vert.co
# Refine only the shoulder, keeping larger facets in the surrounding cliff.
for iteration in range(4):
    edges=[e for e in bm.edges if e.calc_length()>.42 and all(-5.7<v.co.x<2.6 and -2.8<v.co.y<LENGTH+1.3 and -5.7<v.co.z<5.7 for v in e.verts)]
    if not edges: break
    bmesh.ops.subdivide_edges(bm,edges=edges,cuts=1,use_grid_fill=True)
for vert in bm.verts: vert.co=ix @ vert.co
bm.to_mesh(rock.data); bm.free(); rock.data.update()
base=rock.shape_key_add(name='Basis')
key=rock.shape_key_add(name='Left landing | fitted wall and bearing shoulder')
key.value=1

def sm(t):
    t=max(0.,min(1.,t));return t*t*(3-2*t)
changed=[]
for i,vert in enumerate(rock.data.vertices):
    p=mx @ vert.co
    x,y,z=p
    wy=sm((y+2.4)/2.25)*sm((LENGTH+1.25-y)/1.5)
    wz=sm((z+5.5)/1.7)*sm((5.6-z)/1.9)
    wx=sm((x+5.5)/1.7)*sm((2.65-x)/1.1)
    weight=wy*wz*wx
    if weight<1e-7:continue
    # A sloped buttress rises to a flat bearing surface immediately under the slab.
    if z<2.03:
        tx=float(np.interp(z,[-5.5,-3.8,-2,-.2,1.25,2.03],[-.75,-.05,.4,1.1,2.02,2.25]))
        tx+=.065*math.sin(y*1.43+z*.83)+.035*math.sin(y*2.7-z*1.8)
        tz=z
    elif z<2.43:
        t=(z-2.03)/.4
        tx=2.25*(1-t)+.025*t
        tz=BOTTOM+.014
    else:
        tx=float(np.interp(z,[2.43,2.72,3.15,3.8,5.6],[.025,-.012,-.065,-.28,-1.25]))
        tx+=.025*math.sin(y*1.7)*sm((z-2.8)/.7)
        tz=z
    # The shelf rounds into the wall at each end, under the existing footprint.
    end=sm((y+.05)/.8)*sm((LENGTH+.05-y)/.8)
    if tx>0.04:tx=.02+(tx-.02)*end
    target=Vector((x+(tx-x)*weight,y,z+(tz-z)*weight))
    key.data[i].co=ix@target
    changed.append(i)
rock['left_platform_sculpt']='Reversible shape key; flat bearing shoulder at platform underside, tapered foundation below.'
bpy.context.view_layer.update()

def rock_tree():
    ev=rock.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh()
    t=BVHTree.FromPolygons([INV@ev.matrix_world@v.co for v in me.vertices],[list(f.vertices) for f in me.polygons]);ev.to_mesh_clear();return t

tree=rock_tree()
COL=bpy.data.collections.new('167 | Left platform cliff supports');S.collection.children.link(COL)
steel=bpy.data.materials['Metal | dark structural steel']
trim=bpy.data.materials['Lower | aligned architectural trim']
made=[]

def mesh(name,verts,faces,material,bevel=.004):
    me=bpy.data.meshes.new('Left platform | '+name);me.from_pydata(verts,[],faces);me.materials.append(material);me.update()
    bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
    ob=bpy.data.objects.new('Left platform | '+name,me);COL.objects.link(ob)
    ob.parent=floor;ob.matrix_world=FRAME
    if bevel:
        mod=ob.modifiers.new('Small fabricated edge','BEVEL');mod.width=bevel;mod.segments=2
        ob.modifiers.new('Weighted surface normals','WEIGHTED_NORMAL')
    made.append(ob);return ob

faces=[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
def beam(name,a,b,width=.12,depth=.15,mat=steel):
    a,b=Vector(a),Vector(b);axis=(b-a).normalized();helper=Vector((0,0,1)) if abs(axis.z)<.95 else Vector((0,1,0))
    u=axis.cross(helper).normalized()*width/2;v=axis.cross(u).normalized()*depth/2
    return mesh(name,[tuple(p+su*u+sv*v) for p in (a,b) for su,sv in [(-1,-1),(1,-1),(1,1),(-1,1)]],faces,mat)

def plate(name,center,u,v,normal,mat):
    center,u,v,normal=map(Vector,(center,u,v,normal))
    return mesh(name,[tuple(center+normal*d+u*su+v*sv) for d in (-.045,.045) for su,sv in [(-1,-1),(1,-1),(1,1),(-1,1)]],faces,mat)

# Recess the continuous perimeter bearer into the slab's underside.
deps=bpy.context.evaluated_depsgraph_get();ev=floor.evaluated_get(deps);me=ev.to_mesh()
top_poly=[INV@ev.matrix_world@v.co for v in me.vertices if abs((ev.matrix_world@v.co).z-TOP)<.001];ev.to_mesh_clear()
center=sum(top_poly,Vector())/len(top_poly)
poly=sorted(top_poly,key=lambda p:math.atan2(p.y-center.y,p.x-center.x))
for i,a in enumerate(poly):
    b=poly[(i+1)%len(poly)]
    if max(a.x,b.x)<.05: continue
    d=(b-a).normalized();inside=Vector((-d.y,d.x,0))
    aa=a+inside*.07;bb=b+inside*.07;aa.z=bb.z=BOTTOM-.065
    beam('perimeter underside bearer %02d'%(i+1),aa,bb,.12,.17)

anchors=[]
# Paired splayed struts repeat the right platform's rock-to-rim bracket language.
for number,y in enumerate([1.65,5.05,8.45,11.8],1):
    z=-1.08+.12*math.sin(y*.7)
    hit,normal,idx,distance=tree.ray_cast(Vector((5,y,z)),Vector((-1,0,0)),10)
    assert hit is not None
    # The rock solid lies to negative X; seat the rear half of each shoe in it.
    n=normal.normalized()
    if n.x<0:n=-n
    u=Vector((0,1,0));u=(u-n*u.dot(n)).normalized()*.19
    v=n.cross(u).normalized()*.24
    anchor=hit+n*.025
    plate('rock anchor shoe %02d'%number,anchor,u,v,n,trim)
    ends=[]
    for j,dy in enumerate([-.63,.63]):
        ey=y+dy
        clip=1.6207
        rim=WIDTH-max(0,clip-ey)-max(0,ey-(LENGTH-clip))
        end=Vector((rim-.15,ey,BOTTOM-.075))
        beam('splayed diagonal bracket %02d%s'%(number,'AB'[j]),anchor+n*.025,end)
        beam('underside cross bearer %02d%s'%(number,'AB'[j]),(1.55,end.y,BOTTOM-.045),(end.x+.03,end.y,BOTTOM-.045),.115,.16)
        plate('rim connection plate %02d%s'%(number,'AB'[j]),(end.x-.055,end.y,BOTTOM-.005),(.19,0,0),(0,.15,0),(0,0,1),trim)
        ends.append(list(end))
    anchors.append({'shoe_center':list(anchor),'surface_point':list(hit),'upper_connections':ends})

bpy.context.view_layer.update()
assert all(signature(bpy.data.objects[n])==h for n,h in protected.items()),'Unrelated object changed'
report={'sculpted_vertices':len(changed),'total_rock_vertices':len(rock.data.vertices),'new_parts':len(made),'paired_supports':len(anchors),'anchors':anchors,'platform_underside':BOTTOM,'unrelated_objects_preserved':True,'shape_key':key.name}
(P/'build-report.json').write_text(json.dumps(report,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(P/'left-fit-preview.blend'),copy=True,compress=True)
result=report
