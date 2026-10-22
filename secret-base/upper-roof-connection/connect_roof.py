"""Fit the complete upper roof and its ribs to one adjustable lamp perimeter."""
import bpy, bmesh, array, hashlib, json, ast, math
from pathlib import Path
from mathutils import Vector, Matrix

P=Path(__file__).resolve().parent
S=bpy.context.scene
assert bpy.context.mode=='OBJECT'
deck=bpy.data.objects['Upper | beveled square gallery']
ctrl=bpy.data.objects['UPPER PLATFORM SLIDERS']
mod=ctrl.modifiers['Upper Platform Sliders']
root=bpy.data.objects['Upper light | adjustable fixture']
ROOF=bpy.data.collections['174 | Upper gallery connected roof']
H,A=float(deck['deck_height_m']),float(deck['side_m'])/2
UP=Vector((0,0,1))
names={'b':'Upper corner bevel (m)','w':'Upper light width (m)','d':'Upper light depth (m)','h':'Upper light height (m)','c':'Upper light corner bevel (m)'}
sockets={k:next(i for i in mod.node_group.interface.items_tree if i.name==n) for k,n in names.items()}
original={k:float(mod[s.identifier]) for k,s in sockets.items()}
updated=[]
FACES=[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
source=ast.parse((P.parent/'upper-gallery-half-light/resize_and_balance.py').read_text())
helpers=[n for n in source.body if isinstance(n,ast.FunctionDef) and n.name in ('mesh','beam','signature')]
exec(compile(ast.Module(body=helpers,type_ignores=[]),'<existing native gallery helpers>','exec'))
protected={o.name:signature(o) for o in S.objects if not o.name.startswith(('Upper roof |','Upper light |')) and o!=ctrl}
mod[sockets['w'].identifier]=2.40
ctrl.update_tag();S.frame_set(S.frame_current);bpy.context.view_layer.update()
base={k:float(mod[s.identifier]) for k,s in sockets.items()}

def outer(p):
    a=A-.10-.57;c=p['b']-.03;end=(a-c-1.25)/2
    return [Vector(v) for v in [(end,-a,0),(a-c,-a,0),(a,-a+c,0),(a,0,0),(a,a-c,0),(a-c,a,0),(end,a,0),(-1.25,a,0)]]

def lamp_outline(p,inset=0):
    a,b=p['w']/2-inset,p['d']/2-inset
    c=p['c']-(2-math.sqrt(2))*inset
    x,y=float(root.location.x),float(root.location.y)
    return [Vector((x+u,y+v,0)) for u,v in [(-a+c,-b),(a-c,-b),(a,-b+c),(a,b-c),(a-c,b),(-a+c,b),(-a,b-c),(-a,-b+c)]]

def inner(p):
    # All panel seams use the actual housing polygon, including its chamfers.
    # The long left wing shares a midpoint on the straight lamp edge.
    q=lamp_outline(p,.025)
    return [q[0],q[1],q[2],q[2].lerp(q[3],.5),q[3],q[4],q[4].lerp(q[5],.5),q[5]]

def roofgeo(p):
    out=[q+UP*(H+2.115) for q in outer(p)]
    ins=[q+UP*(H+p['h']+.105) for q in inner(p)]
    lower=out+ins;vs=lower+[q+UP*.035 for q in lower];fs=[]
    for j in range(7):
        for a,b,c in [(j,j+1,9+j),(j,9+j,8+j)]:fs.extend([(c,b,a),(a+16,b+16,c+16)])
        fs.extend([(j,j+16,j+17,j+1),(9+j,25+j,24+j,8+j)])
    return vs,fs+[(0,8,24,16),(7,23,31,15)]

panel=bpy.data.objects['Upper roof | continuous fitted crown panels'].material_slots[0].material
trim=bpy.data.objects['Upper roof | panel joint 00'].material_slots[0].material
mesh('Upper roof | continuous fitted crown panels',roofgeo,panel,ROOF,('b','w','d','h','c'),0)
for j in range(8):
    mesh('Upper roof | panel joint %02d'%j,
         lambda p,j=j:beam(outer(p)[j]+UP*(H+2.15),inner(p)[j]+UP*(H+p['h']+.132),.045,.04),
         trim,ROOF,('b','w','d','h','c'))
for name,j in [('Upper roof | finished terminal fascia 00',0),('Upper roof | finished terminal fascia 06',7)]:
    mesh(name,lambda p,j=j:beam(outer(p)[j]+UP*(H+2.12),inner(p)[j]+UP*(H+p['h']+.114),.06,.07),trim,ROOF,('b','w','d','h','c'))

def collar(p):
    # A real steel seat beneath the roof/frame junction; the roof embeds 8 mm.
    vs=[q+UP*(H+p['h']+z) for z in (.083,.113) for inset in (-.055,.070) for q in lamp_outline(p,inset)]
    fs=[]
    for i in range(8):
        j=(i+1)%8
        fs.extend([(i,j,16+j,16+i),(8+j,8+i,24+i,24+j),(j,i,8+i,8+j),(16+i,16+j,24+j,24+i)])
    return vs,fs
mesh('Upper roof | continuous light mounting flange',collar,trim,ROOF,('w','d','h','c'),.002)
ctrl.update_tag();S.frame_set(S.frame_current);bpy.context.view_layer.update()
changed=[n for n,h in protected.items() if signature(bpy.data.objects[n])!=h]
assert not changed,changed
for k in ('b','d','h','c'):assert base[k]==original[k]

# Check native resizing keeps the roof's inner edge seated on the housing.
checks=[]
try:
    for width in (2.4,2.64):
        mod[sockets['w'].identifier]=width
        ctrl.update_tag();S.frame_set(S.frame_current);bpy.context.view_layer.update()
        p={k:float(mod[s.identifier]) for k,s in sockets.items()}
        dg=bpy.context.evaluated_depsgraph_get()
        roof=bpy.data.objects['Upper roof | continuous fitted crown panels'].evaluated_get(dg)
        expected=[q+UP*(H+p['h']+.105) for q in inner(p)]
        error=max((roof.data.vertices[8+i].co-q).length for i,q in enumerate(expected))
        assert error<1e-4,error
        bm=bmesh.new();bm.from_mesh(roof.data)
        assert all(e.is_manifold for e in bm.edges)
        assert all(f.calc_area()>1e-9 for f in bm.faces)
        bm.free()
        checks.append({'light_width_m':width,'maximum_frame_fit_error_m':error,'closed_roof_shell':True})
finally:
    mod[sockets['w'].identifier]=base['w']
    ctrl.update_tag();S.frame_set(S.frame_current);bpy.context.view_layer.update()
ROOF['construction']='Complete closed crown shell: all eight roof ribs seat on the same chamfered housing outline and continuous steel mounting flange. Extra left wall and roof retained.'
ctrl['How to resize light']='Modifiers > Upper Platform Sliders > Upper light width / depth. Entire roof, trim and mounting flange follow the fixture.'
report={'before':original,'after':base,'protected_objects_unchanged':len(protected),'updated_objects':updated,'roof_to_housing_overlap_m':.025,'mounting_seat_overlap_m':.008,'slider_checks':checks}
(P/'verification.json').write_text(json.dumps(report,indent=2))
txt=bpy.data.texts.get('upper_roof_connection.py') or bpy.data.texts.new('upper_roof_connection.py')
txt.clear();txt.write(Path(__file__).read_text())
bpy.ops.wm.save_as_mainfile(filepath=str(P/'connected-roof-candidate.blend'),copy=True,compress=True)
result={k:v for k,v in report.items() if k!='updated_objects'}
