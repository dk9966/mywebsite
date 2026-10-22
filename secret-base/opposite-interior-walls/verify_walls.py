import bpy, bmesh, json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path('/Users/danielku/mywebsite/secret-base/opposite-interior-walls')
s=bpy.context.scene
rock=bpy.data.objects['150 | continuous cave with oblique carved rooms']
ev=rock.evaluated_get(bpy.context.evaluated_depsgraph_get())
me=ev.to_mesh()
tree=BVHTree.FromPolygons([rock.matrix_world@v.co for v in me.vertices],
                         [tuple(p.vertices) for p in me.polygons])
result={'walls':[]}
lower=bpy.data.objects['Lower | plain octagon']
foot=[lower.matrix_world@v.co for v in list(lower.data.vertices)[8:]]
for name in ['Lower | opposite bay 1','Lower | opposite bay 2','Lower | far right beveled bay']:
    o=bpy.data.objects[name]
    a,b,c,d=[o.matrix_world@v.co for v in list(o.data.vertices)[:4]]
    t=(b-a).normalized();up=(d-a).normalized();n=t.cross(up).normalized()
    edge=(foot[2]-foot[3]).normalized() if 'beveled' in name else (foot[3]-foot[4]).normalized()
    clearances=[];intrusions=[]
    for i in range(21):
        for j in range(17):
            p=a.lerp(b,i/20)+(d-a)*(j/16)
            hit,normal,index,distance=tree.ray_cast(p+n*.25,-n,2.)
            if hit is not None:
                gap=distance-.25
                clearances.append(gap)
                if gap<.16:
                    intrusions.append([i,j,round(gap,4)])
    result['walls'].append({'name':name,'min_clearance':min(clearances) if clearances else None,
        'rock_intrusions':intrusions,'samples_hit':len(clearances),
        'vertical_error':abs(1-up.z),'parallel_error':t.cross(edge).length})
ev.to_mesh_clear()
bm=bmesh.new();bm.from_mesh(rock.data)
result['rock']={'vertices':len(bm.verts),'loose_edges':sum(len(e.link_faces)==0 for e in bm.edges),
               'nonmanifold_junctions':sum(len(e.link_faces)>2 for e in bm.edges),
               'boundary_edges':sum(len(e.link_faces)==1 for e in bm.edges)}
unseen=set(bm.verts);components=0
while unseen:
    components+=1
    stack=[unseen.pop()]
    while stack:
        v=stack.pop()
        for e in v.link_edges:
            other=e.other_vert(v)
            if other in unseen:
                unseen.remove(other);stack.append(other)
result['rock']['connected_components']=components
bm.free()
result['passed']=all(not x['rock_intrusions'] and x['parallel_error']<1e-5 and x['vertical_error']<1e-5 for x in result['walls']) and not result['rock']['loose_edges'] and not result['rock']['nonmanifold_junctions'] and components==1
(P/'verification.json').write_text(json.dumps(result,indent=2))
