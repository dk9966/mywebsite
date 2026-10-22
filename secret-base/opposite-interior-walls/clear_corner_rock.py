"""Resolve long sculpt polygons spanning the new corner recess."""
import bpy, bmesh, math
from pathlib import Path
P = Path('/Users/danielku/mywebsite/secret-base/opposite-interior-walls')
rock = bpy.data.objects['150 | continuous cave with oblique carved rooms']
rock.data.use_fake_user = True
if 'before_corner_clearance_mesh' not in rock:
    rock['before_corner_clearance_mesh'] = rock.data.name
rock.data = bpy.data.meshes[rock['before_corner_clearance_mesh']].copy()
rock.data.name = 'Cave | continuous sculpt with clear opposite wall recess'
F = 6.824491024
top = F+2.03
bm = bmesh.new(); bm.from_mesh(rock.data)
def intersects(f):
    ps = [v.co for v in f.verts]
    return (max(p.x for p in ps)>8.1 and min(p.x for p in ps)<13.5 and
            max(p.y for p in ps)>-7.55 and min(p.y for p in ps)<.5 and
            max(p.z for p in ps)>F-.75 and min(p.z for p in ps)<top+1.5)
faces = [f for f in bm.faces if len(f.verts)>3 and intersects(f)]
if faces:
    bmesh.ops.poke(bm, faces=faces, center_mode='MEAN_WEIGHTED')
cuts = 0
for _ in range(5):
    edges = list({e for f in bm.faces if intersects(f) for e in f.edges if e.calc_length()>.5})
    if not edges:
        break
    cuts += len(edges)
    bmesh.ops.subdivide_edges(bm, edges=edges, cuts=1, use_grid_fill=True)
    faces = [f for f in bm.faces if len(f.verts)>3 and intersects(f)]
    if faces:
        bmesh.ops.poke(bm, faces=faces, center_mode='MEAN_WEIGHTED')

def smooth(a,b,x):
    t=min(1.,max(0.,(x-a)/(b-a)))
    return t*t*(3-2*t)
changed=0
for v in bm.verts:
    p=v.co
    if not (8.1<p.x<14.2 and -7.55<p.y<.5 and F-.75<p.z<top+1.5):
        continue
    w=(smooth(8.1,9.,p.x)*(1-smooth(13.5,14.2,p.x))*
       smooth(-7.55,-6.60,p.y)*(1-smooth(-.80,.50,p.y))*
       smooth(F-.75,F-.15,p.z)*(1-smooth(top+.40,top+1.5,p.z)))
    boundary=11.676319+min(0.,p.y+5.173139)
    clearance=.87 if p.y>=-5.173139 else .87*math.sqrt(2)
    target=boundary+clearance+.07*math.sin(p.y*3.1+p.z*2.3)
    dx=max(0.,target-p.x)*w
    if dx>1e-7:
        p.x+=dx;changed+=1
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
bm.to_mesh(rock.data);bm.free();rock.data.update()
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=str(P/'extended-interior-walls.blend'),copy=True,compress=True)
result={'long_edges_subdivided':cuts,'corner_vertices_recessed':changed,'vertices':len(rock.data.vertices)}
