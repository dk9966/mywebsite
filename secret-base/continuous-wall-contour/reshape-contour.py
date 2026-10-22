import bpy
import bmesh
import numpy as np
from math import pi, sin, cos
from mathutils import Vector

wall = bpy.data.objects['150 | continuous cave with oblique carved rooms']
source = bpy.data.meshes[wall['contour_source_mesh']]
wall.data = source.copy()
wall.data.name = 'Cave wall | continuous camera contour'
mesh = wall.data
assert len(source.vertices) == 5880
coords = np.array([v.co[:] for v in source.vertices], dtype=float)
n = len(coords)
uv = np.zeros((n, 2), dtype=float)
for i in range(96):
    uv[i] = (i, 0)
    uv[215-i] = (i, 1)
for j in range(1, 25):
    uv[95+j] = (95, j/25)
    uv[240-j] = (0, j/25)
for u in range(1, 95):
    for j in range(1, 25):
        uv[240 + (u-1)*24 + j-1] = (u, j/25)
edges = np.array([e.vertices[:] for e in source.edges])
src = np.concatenate([edges[:,0], edges[:,1]])
dst = np.concatenate([edges[:,1], edges[:,0]])
degree = np.bincount(dst, minlength=n)
for _ in range(350):
    sums = np.zeros_like(uv)
    np.add.at(sums, dst, uv[src])
    candidate = sums[2496:] / degree[2496:,None]
    err = np.max(np.abs(candidate-uv[2496:]))
    uv[2496:] = candidate
    if err < 1e-9:
        break

platform = bpy.data.objects['Front left | beveled rectangle landing']
inv = wall.matrix_world.inverted()
corner = inv @ platform.matrix_world @ platform.data.vertices[4].co
corner.z -= 0.06
outer = inv @ platform.matrix_world @ platform.data.vertices[7].co
outer.z = corner.z
edge_start = outer.lerp(corner, .218)

# The lip follows the user's U-shaped annotation, with one uninterrupted
# surface from the left platform, around the fixed camera, to the right bay.
knots = [
    (40, coords[175]),
    (44, (-14.1, 0.3, 8.0)),
    (48, tuple(edge_start)),
    (54, tuple(corner)),
    (58, (-4.8, -10.0, 5.0)),
    (64, (-3.3, -14.0, 9.0)),
    (69, (-2.05, -17.5, 12.0)),
    (72, (-1.5, -19.1, 12.1)),
    (75, (0.0, -19.9, 12.1)),
    (78, (1.65, -19.0, 12.1)),
    (83, (3.8, -17.0, 12.0)),
    (89, (5.5, -12.0, 11.0)),
    (95, (7.1, -8.0, 10.6)),
    (98, (8.8, -6.0, 10.5)),
    (103, coords[207]),
    (105, coords[205]),
]
kt = np.array([k[0] for k in knots], dtype=float)
kp = np.array([k[1] for k in knots], dtype=float)
slopes = np.zeros_like(kp)
slopes[0] = (kp[1]-kp[0])/(kt[1]-kt[0])
slopes[-1] = (kp[-1]-kp[-2])/(kt[-1]-kt[-2])
for i in range(1,len(kt)-1):
    a = (kp[i]-kp[i-1])/(kt[i]-kt[i-1])
    b = (kp[i+1]-kp[i])/(kt[i+1]-kt[i])
    for ax in range(3):
        slopes[i,ax] = 0 if a[ax]*b[ax] <= 0 else 2*a[ax]*b[ax]/(a[ax]+b[ax])

def lip(t):
    i = max(0,min(len(kt)-2,int(np.searchsorted(kt,t)-1)))
    h = kt[i+1]-kt[i]
    f = (t-kt[i])/h
    return (2*f**3-3*f*f+1)*kp[i] + (f**3-2*f*f+f)*h*slopes[i] + (-2*f**3+3*f*f)*kp[i+1] + (f**3-f*f)*h*slopes[i+1]

def smoothstep(t):
    t = max(0,min(1,t))
    return t*t*(3-2*t)

bottom = coords[:96].copy()
bottom[0] = bottom[-1] = (bottom[0]+bottom[-1])*.5
changed = 0
for i,(u,v) in enumerate(uv):
    t = u if u>=40 else u+95
    if not 40 < t < 105:
        continue
    blend = smoothstep((t-40)/8)*smoothstep((105-t)/7)
    j = min(94,int(u)); f=u-j
    low = bottom[j]*(1-f)+bottom[j+1]*f
    top = lip(t)
    new = low*(1-v)+top*v
    # Retain small flat rock facets without global smoothing or subdivision.
    theta=2*pi*u/95
    radial=np.array([top[0],top[1]+5,0.0]); radial/=max(.01,np.linalg.norm(radial))
    noise=.28*sin(pi*v)*sin(39*theta+13*v)*cos(17*theta-5*v)
    new += radial*noise
    new[2] += .10*sin(pi*v)*sin(53*theta+9*v)
    mesh.vertices[i].co=coords[i]*(1-blend)+new*blend
    changed+=1

# Close the original duplicated longitudinal seam where it crosses the new
# contour. This does not introduce any cutout, detached piece, or new hole.
path_attr=mesh.attributes.new('wall_path_t','FLOAT','POINT')
height_attr=mesh.attributes.new('wall_height_v','FLOAT','POINT')
for i,(u,v) in enumerate(uv):
    path_attr.data[i].value=float(u if u>=40 else u+95)
    height_attr.data[i].value=float(v)
bm=bmesh.new(); bm.from_mesh(mesh)
bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=0.00002)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
bm.to_mesh(mesh); bm.free()
for face in mesh.polygons:
    face.use_smooth=False
mesh.update()
wall['contour_description']='Continuous faceted U-shaped wall lip follows red annotation and contacts front-left platform. Camera and platforms unchanged.'
bpy.context.view_layer.update()
result={'changed_vertices':changed,'vertex_count':len(mesh.vertices),'face_count':len(mesh.polygons),'uv_error':float(err),'contact_corner':list(corner)}
