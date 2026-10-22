"""Exercise native height controls and check fixture geometry and preservation."""
import bpy, bmesh, json, hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

P=Path('/Users/danielku/mywebsite/secret-base/circular-roof-light')
S=bpy.context.scene
C=bpy.data.collections['165 | Circular workshop light and four roof slopes']
root=bpy.data.objects['Lower | circular roof assembly']
ctrl=bpy.data.objects['SCENE SLIDERS']
control=ctrl.modifiers['Scene Sliders']
socket=next(i for i in control.node_group.interface.items_tree if i.name=='Light height above walls (m)')
default=float(control[socket.identifier])
roofs=sorted([o for o in C.objects if 'roof_section' in o],key=lambda o:o['roof_section'])
assert len(roofs)==4
assert len([o for o in C.objects if o.name.startswith('Lower | circular white rim segment')])==12

def refresh():
    ctrl.update_tag()
    S.frame_set(S.frame_current)
    bpy.context.view_layer.update()

def evaluated(o):
    ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get())
    me=ev.to_mesh()
    pts=[ev.matrix_world@v.co for v in me.vertices]
    ev.to_mesh_clear()
    return pts

original=globals().get('preservation_reference') or json.loads((P/'before-mesh-hashes.json').read_text())
changed=[]
for name,expected in original.items():
    o=bpy.data.objects[name]
    if 'preservation_signature' in globals():
        sig=preservation_signature(o)
    else:
        sig=hashlib.sha256(repr(([list(r) for r in o.matrix_world],
            [tuple(v.co) for v in o.data.vertices],
            [tuple(p.vertices) for p in o.data.polygons])).encode()).hexdigest()
    if sig!=expected:
        changed.append(name)
assert changed==['150 | continuous cave with oblique carved rooms'],changed

nonmanifold={}
for o in C.objects:
    if o.type!='MESH':
        continue
    bm=bmesh.new();bm.from_mesh(o.data)
    n=sum(not e.is_manifold for e in bm.edges)
    bm.free()
    if n:
        nonmanifold[o.name]=n
assert not nonmanifold,nonmanifold

rock=bpy.data.objects['150 | continuous cave with oblique carved rooms']
ev=rock.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh()
bvh=BVHTree.FromPolygons([ev.matrix_world@v.co for v in me.vertices],[tuple(p.vertices) for p in me.polygons])
ev.to_mesh_clear()
cover=bpy.data.objects['Lower | circular light upper cover']
tests=[]
try:
    for height in [.35,1.15,2.10]:
        control[socket.identifier]=height
        refresh()
        pts=evaluated(cover)
        mid=Vector(tuple((min(p[i] for p in pts)+max(p[i] for p in pts))/2 for i in range(3)))
        center_error=(Vector((mid.x,mid.y,0))-Vector((root.matrix_world.translation.x,root.matrix_world.translation.y,0))).length
        top_error=abs(max(p.z for p in pts)-(root['wall_top_world_z']+height+.022))
        assert center_error<1e-4 and top_error<1e-4
        anchor_error=0
        crown_error=0
        planarity=0
        near_rock=[]
        for roof in roofs:
            # Sample un-beveled native deformation so attachment points are exact.
            bevel=roof.modifiers['Fabricated edge radius']
            normals=roof.modifiers['Weighted metal normals']
            bevel.show_viewport=False;normals.show_viewport=False
            try:
                bpy.context.view_layer.update()
                p=evaluated(roof)
            finally:
                bevel.show_viewport=True;normals.show_viewport=True
                bpy.context.view_layer.update()
            for i in [0,1,4,5]:
                anchor_error=max(anchor_error,(p[i]-(roof.matrix_world@roof.data.vertices[i].co)).length)
            for i in [2,3,6,7]:
                target=roof.matrix_world@(roof.data.vertices[i].co+Vector((0,0,height-1.15)))
                crown_error=max(crown_error,(p[i]-target).length)
            normal=(p[1]-p[0]).cross(p[3]-p[0]).normalized()
            planarity=max(planarity,abs((p[2]-p[0]).dot(normal)))
            for u in [.1,.3,.5,.7,.9]:
                for v in [.1,.3,.5,.7,.9]:
                    q=p[0].lerp(p[1],u).lerp(p[3].lerp(p[2],u),v)+Vector((0,0,.015))
                    hit=bvh.find_nearest(q)
                    if hit[3]<.05:
                        near_rock.append((roof['roof_section'],u,v,hit[3]))
        assert anchor_error<1e-4 and crown_error<1e-4
        assert planarity<1e-4
        assert not near_rock,near_rock
        light=bpy.data.objects['Lower | circular crown downlight']
        light_error=abs(light.matrix_world.translation.z-(root['wall_top_world_z']+height-.27))
        assert light_error<1e-4
        tests.append({'height':height,'center_error_m':center_error,'top_height_error_m':top_error,
                      'wall_anchor_error_m':anchor_error,'crown_anchor_error_m':crown_error,
                      'roof_planarity_error_m':planarity,'downlight_error_m':light_error,
                      'roof_rock_intersections_at_sample_points':near_rock})
finally:
    control[socket.identifier]=default
    refresh()

invalid=[]
for o in list(C.objects)+[ctrl]:
    if o.animation_data:
        invalid.extend((o.name,fc.data_path) for fc in o.animation_data.drivers if not fc.driver.is_valid)
assert not invalid,invalid
report={'passed':True,'four_roof_planes':len(roofs),'rim_light_segments':12,
        'native_height_control':socket.name,'min_height_m':socket.min_value,
        'max_height_m':socket.max_value,'default_restored':float(control[socket.identifier]),
        'height_tests':tests,'non_manifold_edges':nonmanifold,'invalid_drivers':invalid,
        'original_meshes_changed':changed,'all_other_original_meshes_and_transforms_preserved':True}
(P/'verification.json').write_text(json.dumps(report,indent=2))
result=report
