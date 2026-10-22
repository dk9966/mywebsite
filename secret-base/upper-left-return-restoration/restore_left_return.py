"""Restore the upper gallery's original extra left bay and roof wing."""
import bpy, bmesh, array, hashlib, json, ast
from pathlib import Path
from mathutils import Vector, Matrix

P=Path(__file__).resolve().parent
S=bpy.context.scene
original_mode=bpy.context.object.mode if bpy.context.object else 'OBJECT'
if original_mode!='OBJECT':bpy.ops.object.mode_set(mode='OBJECT')
deck=bpy.data.objects['Upper | beveled square gallery']
ctrl=bpy.data.objects['UPPER PLATFORM SLIDERS']
mod=ctrl.modifiers['Upper Platform Sliders']
root=bpy.data.objects['Upper light | adjustable fixture']
ROOF=bpy.data.collections['174 | Upper gallery connected roof']
WALLS=bpy.data.collections['173 | Upper gallery wall panels and bent ribs']
RAILS=bpy.data.collections['173 | Upper gallery exposed edge railings']
archive=bpy.data.collections['Archive | upper gallery outer left return before balance']
H,A=float(deck['deck_height_m']),float(deck['side_m'])/2
UP=Vector((0,0,1))
names={'b':'Upper corner bevel (m)','w':'Upper light width (m)','d':'Upper light depth (m)','h':'Upper light height (m)','c':'Upper light corner bevel (m)'}
sockets={k:next(i for i in mod.node_group.interface.items_tree if i.name==n) for k,n in names.items()}
base={k:float(mod[s.identifier]) for k,s in sockets.items()}
original_controls=base.copy()
FACES=[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
updated=[]
source=ast.parse((P.parent/'upper-gallery-half-light/resize_and_balance.py').read_text())
helpers=[node for node in source.body if isinstance(node,ast.FunctionDef) and node.name in ('mesh','beam','box','signature')]
exec(compile(ast.Module(body=helpers,type_ignores=[]),'<existing gallery mesh helpers>','exec'))
restore=[o for o in archive.objects if o.name.startswith(('Upper wall | bay 05 ','Upper wall | rib 06 '))]
assert len(restore)==19, 'Expected original left bay and end support'
target_names={o.name for o in restore}|{'Upper roof | continuous fitted crown panels','Upper roof | finished terminal fascia 06'}
target_names.update(o.name for o in RAILS.objects if o.name.startswith('Upper exposed rail | span 00 '))
protected={o.name:signature(o) for o in S.objects if o.name not in target_names}
for o in restore:
    WALLS.objects.link(o)
    archive.objects.unlink(o)

def outer(p):
    a=A-.10-.57;c=p['b']-.03;end=(a-c-1.25)/2
    return [Vector(v) for v in [(end,-a,0),(a-c,-a,0),(a,-a+c,0),(a,0,0),(a,a-c,0),(a-c,a,0),(end,a,0),(-1.25,a,0)]]

def inner(p):
    x,y=float(root.location.x),float(root.location.y)
    a,b,c=p['w']/2,p['d']/2,p['c']
    return [Vector(v) for v in [(x-a+c,y-b,0),(x+a-c,y-b,0),(x+a,y-b+c,0),(x+a,y,0),(x+a,y+b-c,0),(x+a-c,y+b,0),(x-a+c,y+b,0),(-1.25,y+b,0)]]

def roofgeo(p):
    out=[q+UP*(H+2.115) for q in outer(p)]
    ins=[q+UP*(H+p['h']+.105) for q in inner(p)]
    normals=[Vector(v).normalized() for v in [(0,-1,0),(1,-1,0),(1,-1,0),(1,0,0),(1,1,0),(1,1,0),(0,1,0),(0,1,0)]]
    for j in range(8):ins[j]-=normals[j]*.012
    lower=out+ins;vs=lower+[q+UP*.035 for q in lower];fs=[]
    for j in range(7):
        for a,b,c in [(j,j+1,9+j),(j,9+j,8+j)]:fs.extend([(c,b,a),(a+16,b+16,c+16)])
        fs.extend([(j,j+16,j+17,j+1),(9+j,25+j,24+j,8+j)])
    return vs,fs+[(0,8,24,16),(7,23,31,15)]

panel=bpy.data.objects['Upper roof | continuous fitted crown panels'].material_slots[0].material
trim=bpy.data.objects['Upper roof | panel joint 06'].material_slots[0].material
mesh('Upper roof | continuous fitted crown panels',roofgeo,panel,ROOF,('b','w','d','h','c'),0)
mesh('Upper roof | panel joint 07',lambda p:beam(outer(p)[7]+UP*(H+2.15),inner(p)[7]+UP*(H+p['h']+.147),.045,.04),trim,ROOF,('b','w','d','h','c'))
mesh('Upper roof | finished terminal fascia 06',lambda p:beam(outer(p)[7]+UP*(H+2.12),inner(p)[7]+UP*(H+p['h']+.10),.06,.07),trim,ROOF,('b','w','d','h','c'))

# Return the exposed rail's left endpoint to the restored wall's original end.
def railends(p):
    a=A-.075;c=p['b']-.025
    return Vector((-1.35,a,0)),Vector((-a+c,a,0))
for z in (.190,.345):
    name='Upper exposed rail | span 00 bar %.3f'%z
    mat=bpy.data.objects[name].material_slots[0].material
    mesh(name,lambda p,z=z:beam(railends(p)[0]+UP*(H+z),railends(p)[1]+UP*(H+z),.025,.018),mat,RAILS,bevel=.0015)
for label,z,w,d,h in [('post',.177,.028,.028,.354),('foot',.008,.052,.052,.024)]:
    name='Upper exposed rail | span 00 '+label+' 00'
    mat=bpy.data.objects[name].material_slots[0].material
    mesh(name,lambda p,z=z,w=w,d=d,h=h:box(railends(p)[0]+UP*(H+z),w,d,h),mat,RAILS,bevel=.0015)
    for j in (1,2):
        o=bpy.data.objects.get('Upper exposed rail | span 00 '+label+' %02d'%j)
        if o and o.name in RAILS.objects:
            archive.objects.link(o);RAILS.objects.unlink(o)

ctrl.update_tag();S.frame_set(S.frame_current);bpy.context.view_layer.update()
changed=[n for n,h in protected.items() if signature(bpy.data.objects[n])!=h]
assert not changed,changed
assert original_controls=={k:float(mod[s.identifier]) for k,s in sockets.items()}
roof=bpy.data.objects['Upper roof | continuous fitted crown panels']
bm=bmesh.new();bm.from_mesh(roof.data)
assert all(e.is_manifold for e in bm.edges),'Roof is not a closed shell'
bm.free()
ROOF['construction']='Continuous roof with the original extra left wall and roof wing restored; retains smaller adjustable luminaire and new right return.'
report={'restored_wall_objects':[o.name for o in restore],'protected_objects_unchanged':len(protected),'controls_unchanged':original_controls,'closed_roof_shell':True,'updated':updated}
(P/'verification.json').write_text(json.dumps(report,indent=2))
if original_mode!='OBJECT':bpy.ops.object.mode_set(mode=original_mode)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'left-return-restored.blend'),copy=True,compress=True)
result={'restored_wall_objects':len(restore),'protected_objects_unchanged':len(protected),'roof_closed':True,'mode':bpy.context.mode}
