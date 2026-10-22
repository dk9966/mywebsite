import bpy, bmesh, math, json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent
S=bpy.context.scene
ctrl=bpy.data.objects.get('UPPER PLATFORM SLIDERS') or bpy.data.objects['SCENE SLIDERS']
mod=ctrl.modifiers.get('Upper Platform Sliders') or ctrl.modifiers['Scene Sliders']
deck=bpy.data.objects['Upper | beveled square gallery'];F=deck.matrix_world;IV=F.inverted();H=deck['deck_height_m'];A=deck['side_m']/2
terrain=bpy.data.objects['150 | continuous cave with oblique carved rooms']
COL=bpy.data.collections['173 | Upper gallery architecture']
LIGHT=bpy.data.collections['173 | Adjustable beveled rectangular light']
names={'b':'Upper corner bevel (m)','w':'Upper light width (m)','d':'Upper light depth (m)','h':'Upper light height (m)','c':'Upper light corner bevel (m)'}
ids={k:next(i.identifier for i in mod.node_group.interface.items_tree if i.name==v) for k,v in names.items()}
original={k:float(mod[i]) for k,i in ids.items()}

def update(vals):
    for k,v in vals.items():mod[ids[k]]=v
    ctrl.update_tag();S.frame_set(S.frame_current);bpy.context.view_layer.update()

def shape_driver(key,var,base):
    fc=key.driver_add('value');d=fc.driver;d.type='SCRIPTED';d.expression=var+'-'+str(base)
    v=d.variables.new();v.name=var;v.type='SINGLE_PROP';v.targets[0].id=ctrl
    v.targets[0].data_path='modifiers["'+mod.name+'"]["'+ids[var]+'"]'

# Two narrow arms visibly carry the light from the structural wall crowns.
# Ends track the native sliders while wall-side anchors remain on the ribs.
def armgeometry(p,index):
    cut=p['b']-.03
    a=A-.10-.59
    if index==0:
        start=Vector((a,0,H+2.15));end=Vector((-.35+p['w']/2-.11,-.10,H+p['h']+.145))
        across=Vector((0,1,0))
    else:
        start=Vector(((a-cut-1.25)/2,a,H+2.15));end=Vector((start.x,-.10+p['d']/2-.11,H+p['h']+.145))
        across=Vector((1,0,0))
    # Preserve constant XY and vertical cross sections during dimension changes.
    vs=[p+across*x*.035+Vector((0,0,z*.025)) for p in [start,end] for x,z in [(-1,-1),(1,-1),(1,1),(-1,1)]]
    return vs,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]

for index in range(2):
    name='Upper light | wall-mounted suspension arm %d'%index
    if bpy.data.objects.get(name):continue
    vs,fs=armgeometry(original,index)
    me=bpy.data.meshes.new(name);me.from_pydata(vs,[],fs);me.materials.append(bpy.data.materials['Metal | dark structural steel'])
    bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
    o=bpy.data.objects.new(name,me);LIGHT.objects.link(o);o.parent=deck;o.matrix_world=F
    o.shape_key_add(name='Basis')
    for var in ['b','w','d','h']:
        p=dict(original);p[var]+=1;alt,_=armgeometry(p,index)
        if max((a-b).length for a,b in zip(vs,alt))<1e-7:continue
        key=o.shape_key_add(name='Follow '+var);key.slider_min=-4;key.slider_max=4
        for k,v in zip(key.data,alt):k.co=v
        shape_driver(key,var,original[var])
    bevel=o.modifiers.new('Machined arm edges','BEVEL');bevel.width=.005;bevel.segments=2
    o.modifiers.new('Weighted steel normals','WEIGHTED_NORMAL')

def bounds(o,dg):
    e=o.evaluated_get(dg);pts=[IV@e.matrix_world@v.co for v in e.data.vertices]
    return [[min(v[k] for v in pts),max(v[k] for v in pts)] for k in range(3)]

def terrain_tree(dg):
    e=terrain.evaluated_get(dg);me=e.to_mesh()
    tree=BVHTree.FromPolygons([IV@e.matrix_world@v.co for v in me.vertices],[list(p.vertices) for p in me.polygons])
    e.to_mesh_clear();return tree

cases=[original,
       dict(original,w=2.4,d=1.4,h=1.8,c=.3,b=.1),
       dict(original,w=4.5,d=3.1,h=2.8,c=.65,b=1.5),
       dict(original,w=4.5,d=1.4,h=2.8,c=.65,b=.3),
       dict(original,w=2.4,d=3.1,h=1.8,c=.3,b=1.5),
       dict(original,b=.8),dict(original,h=2.8),dict(original,h=1.8)]
records=[]
try:
    for p in cases:
        update(p);dg=bpy.context.evaluated_depsgraph_get();tree=terrain_tree(dg)
        o=bpy.data.objects['Upper light | broad chamfered housing'];bb=bounds(o,dg)
        errs=[abs(bb[0][1]-bb[0][0]-p['w']),abs(bb[1][1]-bb[1][0]-p['d']),abs(bb[2][0]-(H+p['h']+.018))]
        assert max(errs)<.001,(p,errs)
        ld=bpy.data.lights['Upper light | rectangular downlight']
        assert abs(ld.size-(p['w']-.3))<.001 and abs(ld.size_y-(p['d']-.3))<.001
        clearance=[]
        for xi in range(9):
            for yi in range(7):
                x=-.35-p['w']/2+xi*p['w']/8;y=-.1-p['d']/2+yi*p['d']/6
                if abs(x+.35)+abs(y+.1)>p['w']/2+p['d']/2-p['c']+.001:continue
                hit=tree.ray_cast(Vector((x,y,H+1.5)),Vector((0,0,1)),9)
                if hit[0]:clearance.append(hit[0].z-(H+p['h']+.16))
        assert min(clearance)>.10,('Light intersects ceiling',p,min(clearance))
        invalid=[]
        for obj in COL.all_objects:
            owners=[obj,obj.data]+([obj.data.shape_keys] if obj.type=='MESH' and obj.data.shape_keys else [])
            for owner in owners:
                if owner and owner.animation_data:
                    invalid += [obj.name+': '+fc.data_path for fc in owner.animation_data.drivers if not fc.driver.is_valid]
        assert not invalid,invalid
        records.append({'settings':p,'dimension_errors_m':errs,'minimum_ceiling_clearance_m':min(clearance),'invalid_drivers':invalid})
finally:
    update(original)

nonmanifold=[]
for o in COL.all_objects:
    if o.type!='MESH':continue
    bm=bmesh.new();bm.from_mesh(o.data)
    if any(not e.is_manifold for e in bm.edges):nonmanifold.append(o.name)
    bm.free()
assert not nonmanifold,nonmanifold
report={'cases':records,'nonmanifold_new_meshes':nonmanifold,'all_geometry_native':True,'scene_objects_added':len(COL.all_objects)}
(P/'verification.json').write_text(json.dumps(report,indent=2))
text=bpy.data.texts.get('upper_gallery_finish_and_verify.py') or bpy.data.texts.new('upper_gallery_finish_and_verify.py');text.clear();text.write(Path(__file__).read_text())
bpy.ops.wm.save_as_mainfile(filepath=str(P/'architecture-candidate.blend'),copy=True)
result=report
