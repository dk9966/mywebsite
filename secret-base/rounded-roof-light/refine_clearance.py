"""Retain sparse local samples where the low-poly cave follows a curved roof."""
import bpy,bmesh,math,json
from mathutils import Vector
from pathlib import Path

P=Path('/Users/danielku/mywebsite/secret-base/rounded-roof-light')
rock=bpy.data.objects['150 | continuous cave with oblique carved rooms']
root=bpy.data.objects['Lower | circular roof assembly']
lower=bpy.data.objects['Lower | plain octagon']
assert not rock.get('rounded_roof_clearance_refined')
old=rock.data;old.use_fake_user=True
rock['before_refined_clearance_mesh']=old.name
rock.data=old.copy()
rock.data.name='Cave | low-poly sculpt with fitted roof patch'
M=rock.matrix_world;center=M.inverted()@root.matrix_world.translation
wall=root['wall_top_world_z']
foot=[M.inverted()@lower.matrix_world@lower.data.vertices[8+i].co for i in range(8)]

def cross(a,b):return a.x*b.y-a.y*b.x

def boundary(p):
    delta=Vector((p.x-center.x,p.y-center.y,0));rho=delta.length
    if rho<1e-7:return 4.,rho
    unit=delta/rho;hits=[]
    for a,b in zip(foot,foot[1:]+foot[:1]):
        aa=a-center;e=b-a;den=cross(unit,e)
        if abs(den)<1e-8:continue
        r=cross(aa,e)/den;t=cross(aa,unit)/den
        if r>0 and -.00001<=t<=1.00001:hits.append(r)
    return min(hits),rho

def patch_face(f):
    ps=[v.co for v in f.verts]
    if min(p.z for p in ps)>wall+2.65 or max(p.z for p in ps)<wall-.08:return False
    x=max(min(p.x for p in ps),min(center.x,max(p.x for p in ps)))
    y=max(min(p.y for p in ps),min(center.y,max(p.y for p in ps)))
    return math.hypot(x-center.x,y-center.y)<4.6

bm=bmesh.new();bm.from_mesh(rock.data)
for _ in range(3):
    fs=[f for f in bm.faces if patch_face(f)]
    edges={e for f in fs for e in f.edges if e.calc_length()>.43}
    if not edges:break
    bmesh.ops.subdivide_edges(bm,edges=list(edges),cuts=1,use_grid_fill=True)
bm.to_mesh(rock.data);bm.free()

attr=rock.data.attributes['roof_clearance_follow']
full=0
for v in rock.data.vertices:
    p=v.co;bound,rho=boundary(p)
    xy=max(0.,min(1.,(bound+.4-rho)/.25))
    if p.z<wall-.01:
        z=0
    elif p.z<wall+.08:
        z=(p.z-wall+.01)/.09
    elif p.z<wall+2.48:
        z=1
    else:
        z=max(0.,min(1.,(wall+2.75-p.z)/.27))
    weight=xy*z
    attr.data[v.index].value=weight
    full+=weight>.99
rock['rounded_roof_clearance_refined']=True
rock.data.update();bpy.context.view_layer.update()
tri=sum(len(p.vertices)-2 for p in rock.data.polygons)
report={'triangles_after_local_roof_fit':tri,'reduction_from_original_percent':100*(1-tri/175365),
        'vertices':len(rock.data.vertices),'fully_fitted_roof_vertices':full,
        'local_max_edge_target_m':.43}
(P/'terrain-fit.json').write_text(json.dumps(report,indent=2))
result=report
