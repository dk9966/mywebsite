"""Recess only the obstructing cave overhang above the lower roof.

Keep the previous terrain datablock, topology, lower walls and upper platform.
Fit clearance for the full supported 0.35–2.10 m height adjustment.
"""
import bpy, json, math
from mathutils import Vector
from pathlib import Path

P = Path('/Users/danielku/mywebsite/secret-base/circular-roof-light')
rock = bpy.data.objects['150 | continuous cave with oblique carved rooms']
lower = bpy.data.objects['Lower | plain octagon']
root = bpy.data.objects['Lower | circular roof assembly']
assert 'before_circular_roof_clearance_mesh' not in rock
old = rock.data
old.use_fake_user = True
rock['before_circular_roof_clearance_mesh'] = old.name
rock.data = old.copy()
rock.data.name = 'Cave | local clearance over four-slope circular crown'
foot = [lower.matrix_world@v.co for v in list(lower.data.vertices)[8:]]
center = sum(foot,Vector())/8
wall_z = root['wall_top_world_z']
inv = rock.matrix_world.inverted()

def cross(a,b):
    return a.x*b.y-a.y*b.x

def boundary_radius(unit):
    hits=[]
    for a,b in zip(foot,foot[1:]+foot[:1]):
        aa = a-center
        edge = b-a
        den = cross(unit,edge)
        if abs(den)<1e-7:
            continue
        r = cross(aa,edge)/den
        t = cross(aa,unit)/den
        if r>0 and -.0001<=t<=1.0001:
            hits.append(r)
    return min(hits)

changed=[]
max_shift=0
for v in rock.data.vertices:
    p=rock.matrix_world@v.co
    # The wall panels end below this datum. Only the hanging roof is recessed.
    if not wall_z-.005 < p.z < wall_z+2.37:
        continue
    delta=Vector((p.x-center.x,p.y-center.y,0))
    radius=delta.length
    bound=boundary_radius(delta.normalized()) if radius>1e-5 else 4.0
    if radius>=bound+.12:
        continue
    # Flat clearance above the circular housing blends into the wall-top rim.
    w=max(0.,min(1.,(bound+.12-radius)/(bound+.12-1.64)))
    ceiling=wall_z+.22+2.10*w
    if p.z<ceiling:
        max_shift=max(max_shift,ceiling-p.z)
        p.z=ceiling
        v.co=inv@p
        changed.append(v.index)
rock.data.update()
rock['circular_roof_clearance']='Local overhang lifted above the four roof slopes and crown; lower walls, topology, and upper platform retained.'
ctrl=bpy.data.objects['SCENE SLIDERS']
for s in ctrl.modifiers['Scene Sliders'].node_group.interface.items_tree:
    if s.item_type=='SOCKET' and s.name=='Light height above walls (m)':
        s.max_value=2.10
report={'changed_vertices':len(changed),'max_vertical_shift':max_shift,
        'preserved_vertex_count':len(old.vertices),'max_supported_light_rise':2.10,
        'ceiling_max_z':wall_z+2.32,'source_mesh':old.name}
(P/'ceiling-fit.json').write_text(json.dumps(report,indent=2))
bpy.context.view_layer.update()
result=report
