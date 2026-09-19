"""Continuous cyan inlays routed on welded pillar edges; safe to run independently."""
import bpy
import bmesh
import math
import heapq
from mathutils import Matrix


def build_pillar_veins(host, collection, suffix='', phase=0):
    bm = bmesh.new()
    bm.from_mesh(host.data)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-5)
    bm.verts.ensure_lookup_table()
    bm.verts.index_update()
    bm.normal_update()
    points = [v.co.copy() for v in bm.verts]
    angles = [math.atan2(p.y, p.x) for p in points]
    def ad(a, b):
        return abs((a-b+math.pi) % math.tau-math.pi)
    graph = [[] for p in points]
    for e in bm.edges:
        i, j = (v.index for v in e.verts)
        p, q = points[i], points[j]
        if max(p.z, q.z) > 7.37 or min(p.xy.length, q.xy.length) < 0.6:
            continue
        # Prefer longitudinal edges and level ledges over triangle diagonals.
        da, dz = ad(angles[i], angles[j]), abs(p.z-q.z)
        penalty = 12 if da > 0.008 and dz > 0.015 else 1
        cost = (p-q).length * penalty
        graph[i].append((j, cost)); graph[j].append((i, cost))
    def nearest(a, z):
        return min((i for i in range(len(points)) if graph[i]),
                   key=lambda i: (points[i].z-z)**2+9*ad(angles[i],a)**2)
    def route(start, end, angle):
        queue = [(0, start)]; distances = {start: 0}; prev = {}
        while queue:
            cost, i = heapq.heappop(queue)
            if cost != distances[i]: continue
            if i == end: break
            for j, length in graph[i]:
                # Keep each trace in its own narrow sector and progressing upward.
                if points[j].z < points[i].z-0.001: continue
                candidate = cost + length*(1+3*ad(angles[j], angle))
                if candidate < distances.get(j, float('inf')):
                    distances[j] = candidate; prev[j] = i
                    heapq.heappush(queue,(candidate,j))
        if end not in distances: raise RuntimeError('No connected surface route')
        path = [end]
        while path[-1] != start: path.append(prev[path[-1]])
        return list(reversed(path))
    curves = {}
    for key in ['neonCyan','neonCyanFaint']:
        curve = bpy.data.curves.new('pillar_edge_routes_'+key+suffix, 'CURVE')
        curve.dimensions = '3D'; curve.resolution_u = 1
        curve.bevel_depth = 0.010 if key == 'neonCyan' else 0.008
        curve.bevel_resolution = 0; curve.resolution_u = 1
        curve.use_fill_caps = True
        curves[key] = curve
    report = []
    for i in range(15):
        angle = math.tau*(i+0.2)/15 + phase
        band = i % 3
        low = [0, 2.2+0.16*(i%4), 4.55+0.12*(i%3)][band]
        length = [1.65,2.55,2.1,1.4,2.85][i//3]
        high = min(7.23, low+length)
        start = nearest(angle,low)
        end = nearest(angle + (math.tau/65)*(1 if i%2 else -1), high)
        ids = route(start,end,angle)
        key = 'neonCyanFaint' if i%4 == 1 else 'neonCyan'
        def project(p):
            angle = math.atan2(p.y,p.x) + 0.006
            radial = p.copy(); radial.x=math.cos(angle); radial.y=math.sin(angle); radial.z=0
            origin = radial*5; origin.z = max(0.00001,p.z + 0.000003)
            hit, loc, normal, face = host.ray_cast(origin,-radial)
            if not hit: raise RuntimeError('Surface projection missed')
            return loc + radial*0.002
        # Follow the visible envelope: layered stone can cover underlying edges.
        # Refine each ledge crossing to avoid bridging or floating over recesses.
        samples = []
        def follow(a,b,pa,pb,depth=0):
            if (pb-pa).length > 0.035 and depth < 16:
                mid = a.lerp(b,0.5); pm = project(mid)
                follow(a,mid,pa,pm,depth+1); follow(mid,b,pm,pb,depth+1)
            else: samples.append(pb)
        for ia,ib in zip(ids,ids[1:]):
            a,b=points[ia],points[ib]
            count=max(1,math.ceil((b-a).length/0.015))
            for k in range(count):
                p=a.lerp(b,k/count); q=a.lerp(b,(k+1)/count)
                pp,pq=project(p),project(q)
                if not samples: samples.append(pp)
                follow(p,q,pp,pq)
        clean=[]
        for p in samples:
            if clean and (p-clean[-1]).length < 1e-6: continue
            while len(clean)>1:
                ab=p-clean[-2]; ac=clean[-1]-clean[-2]
                if ab.length and ac.cross(ab).length/ab.length < 0.000015 and ac.dot(ab)>0:
                    clean.pop()
                else: break
            clean.append(p)
        spline = curves[key].splines.new('POLY')
        spline.points.add(len(clean)-1)
        for target,p in zip(spline.points,clean): target.co=(*p,1)
        report.append({'bottom':round(points[start].z,3),'top':round(points[end].z,3),'vertices':len(ids)})
    for key, curve in curves.items():
        name = 'deck_pillar_veins_'+key+suffix
        old = bpy.data.objects.get(name)
        temp = bpy.data.objects.new(name+'_route',curve)
        collection.objects.link(temp)
        bpy.context.view_layer.update()
        mesh = bpy.data.meshes.new_from_object(temp.evaluated_get(bpy.context.evaluated_depsgraph_get()))
        weld = bmesh.new(); weld.from_mesh(mesh)
        bmesh.ops.remove_doubles(weld, verts=list(weld.verts), dist=1e-6)
        weld.to_mesh(mesh); weld.free()
        mesh.name = name+'_connected'
        mesh.materials.clear(); mesh.materials.append(bpy.data.materials[key])
        if old:
            old.data.use_fake_user = True
            old.data = mesh
            obj = old
        else:
            obj = bpy.data.objects.new(name,mesh); collection.objects.link(obj)
        obj.parent = host
        obj.matrix_parent_inverse = Matrix.Identity(4)
        obj.matrix_basis = Matrix.Identity(4)
        obj['vein_style'] = 'Continuous surface-edge inlays, 15 varied routes, 5 rooted at base'
        bpy.data.objects.remove(temp,do_unlink=True)
        bpy.data.curves.remove(curve)
    bm.free()
    return report

if __name__ == '__main__':
    result = {}
    for host_name, coll_name, suffix, phase in [
        ('island_pillar_huge','deck_huge','',0),
        ('island_pillar_workshop','deck_workshop','_b',math.tau/30),
    ]:
        result[host_name] = build_pillar_veins(bpy.data.objects[host_name],bpy.data.collections[coll_name],suffix,phase)
