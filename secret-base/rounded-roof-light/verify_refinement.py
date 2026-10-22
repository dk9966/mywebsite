"""Check both native sliders, rounded joins, rock clearance, and reduced topology."""
import bpy,bmesh,math,json,hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

P=Path('/Users/danielku/mywebsite/secret-base/rounded-roof-light')
S=bpy.context.scene
ctrl=bpy.data.objects['SCENE SLIDERS'];control=ctrl.modifiers['Scene Sliders']
root=bpy.data.objects['Lower | circular roof assembly']
C=bpy.data.collections['165 | Circular workshop light and four roof slopes']
rock=bpy.data.objects['150 | continuous cave with oblique carved rooms']
roofs=sorted((o for o in C.objects if 'roof_section' in o),key=lambda o:o['roof_section'])
assert len(roofs)==4
hs=next(i.identifier for i in control.node_group.interface.items_tree if i.name=='Light height above walls (m)')
rs=next(i.identifier for i in control.node_group.interface.items_tree if i.name=='Light radius (m)')
defaults=(float(control[hs]),float(control[rs]))

def refresh():
    ctrl.update_tag();S.frame_set(S.frame_current);bpy.context.view_layer.update()

def points(o):
    ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh()
    pts=[ev.matrix_world@v.co for v in me.vertices]
    ev.to_mesh_clear();return pts

bad={}
for o in C.objects:
    if o.type!='MESH':continue
    bm=bmesh.new();bm.from_mesh(o.data)
    n=sum(not e.is_manifold for e in bm.edges);bm.free()
    if n:bad[o.name]=n
assert not bad,bad
mod_settings=[]
for o in roofs:
    for mod in o.modifiers:
        if mod.type in ['BEVEL','WEIGHTED_NORMAL']:
            mod_settings.append((mod,mod.show_viewport));mod.show_viewport=False
tests=[]
try:
    for h in [.35,defaults[0],2.10]:
        for radius in [.85,defaults[1],2.10]:
            control[hs]=h;control[rs]=radius;refresh()
            anchor_err=0;arc_err=0;join_err=0
            roof_samples=[]
            for o in roofs:
                pp=points(o);inv=o.matrix_world.inverted()
                for idx in o['wall_top_indices']:
                    anchor_err=max(anchor_err,(pp[idx]-o.matrix_world@o.data.vertices[idx].co).length)
                for idx in o['inner_top_indices']:
                    q=inv@pp[idx]
                    arc_err=max(arc_err,abs(math.hypot(q.x,q.y)-radius))
                    join_err=max(join_err,abs(q.z-(h-.075)))
                n=o['arc_segments']+1
                for idx in range(len(o.data.vertices)//2):
                    t=o['roof_rows'][idx//n];j=idx%n
                    if .15<=t<=.97 and 1<j<n-2:
                        roof_samples.append(pp[idx])
            assert anchor_err<1e-4 and arc_err<1e-4 and join_err<1e-4
            # Verify the fixture itself scales to the same circular boundary.
            fixture=bpy.data.objects['Lower | circular light stepped rim']
            fixture_points=[root.matrix_world.inverted()@p for p in points(fixture)]
            housing_radius=max(math.hypot(p.x,p.y) for p in fixture_points)
            assert abs(housing_radius-radius)<.006
            ld=bpy.data.lights['Lower | circular crown downlight']
            assert abs(ld.size-2.50*radius/1.46)<1e-4

            dg=bpy.context.evaluated_depsgraph_get();ev=rock.evaluated_get(dg);me=ev.to_mesh()
            bvh=BVHTree.FromPolygons([ev.matrix_world@v.co for v in me.vertices],[tuple(p.vertices) for p in me.polygons])
            ev.to_mesh_clear()
            gaps=[]
            for p in roof_samples:
                q,normal,index,distance=bvh.ray_cast(p+Vector((0,0,.003)),Vector((0,0,1)),4)
                if q is not None:gaps.append(distance)
            assert gaps and min(gaps)>.025,(h,radius,min(gaps))
            crown_gaps=[]
            for fraction in [0,.4,.75,.94,1.]:
                for i in range(32):
                    p=root.matrix_world@Vector((radius*fraction*math.cos(i*math.tau/32),
                        radius*fraction*math.sin(i*math.tau/32),h+.026))
                    q,normal,index,distance=bvh.ray_cast(p+Vector((0,0,.5)),Vector((0,0,-1)),1.)
                    if q is not None:crown_gaps.append(q.z-p.z)
            assert crown_gaps and min(crown_gaps)>.03,(h,radius,min(crown_gaps))
            tests.append({'height':h,'radius':radius,'wall_anchor_error_m':anchor_err,
                          'rounded_edge_radius_error_m':arc_err,'light_join_height_error_m':join_err,
                          'minimum_sampled_roof_clearance_m':min(gaps),
                          'minimum_sampled_fixture_clearance_m':min(crown_gaps)})
finally:
    control[hs],control[rs]=defaults
    for mod,value in mod_settings:mod.show_viewport=value
    refresh()

invalid=[]
for o in list(C.objects)+[ctrl,rock,bpy.data.lights['Lower | circular crown downlight']]:
    if o.animation_data:
        invalid.extend((o.name,f.data_path) for f in o.animation_data.drivers if not f.driver.is_valid)
assert not invalid,invalid
tri=sum(len(p.vertices)-2 for p in rock.data.polygons)
assert tri<175365*.25
report={'passed':True,'rounded_roof_sections':4,'height_and_radius_tests':tests,
        'native_radius_control':'Light radius (m)','radius_range_m':[.85,2.10],
        'restored_height':defaults[0],'restored_radius':defaults[1],
        'source_terrain_triangles':175365,'final_terrain_triangles':tri,
        'terrain_triangle_reduction_percent':100*(1-tri/175365),
        'non_manifold_fixture_or_roof_edges':bad,'invalid_drivers':invalid}
(P/'verification.json').write_text(json.dumps(report,indent=2))
result=report
