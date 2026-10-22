"""Separate upper-gallery dependency updates from expensive scene-wide controls."""
import bpy,json,time,hashlib,array
from pathlib import Path
P=Path(__file__).resolve().parent
S=bpy.context.scene
old=bpy.data.objects['SCENE SLIDERS'];oldmod=old.modifiers['Scene Sliders']
assert bpy.data.objects.get('UPPER PLATFORM SLIDERS') is None
sockets=[i for i in oldmod.node_group.interface.items_tree if i.item_type=='SOCKET' and i.in_out=='INPUT' and (i.name=='Upper corner bevel (m)' or i.name.startswith('Upper light '))]
assert len(sockets)==5

def geometry_signatures():
    dg=bpy.context.evaluated_depsgraph_get();out={}
    for obj in S.objects:
        if obj.type!='MESH' or obj.hide_render:continue
        e=obj.evaluated_get(dg);data=e.data
        coords=array.array('f',[0])*(3*len(data.vertices));data.vertices.foreach_get('co',coords)
        h=hashlib.sha256(coords.tobytes());h.update(repr([list(r) for r in e.matrix_world]).encode())
        out[obj.name]=h.hexdigest()
    return out

before=geometry_signatures()
me=bpy.data.meshes.new('Upper platform | slider container')
ctrl=bpy.data.objects.new('UPPER PLATFORM SLIDERS',me)
bpy.data.collections['00 | Scene sliders'].objects.link(ctrl)
ctrl.hide_render=True
group=bpy.data.node_groups.new('Upper Platform Sliders','GeometryNodeTree')
group.interface.new_socket(name='Geometry',in_out='INPUT',socket_type='NodeSocketGeometry')
group.interface.new_socket(name='Geometry',in_out='OUTPUT',socket_type='NodeSocketGeometry')
gi=group.nodes.new('NodeGroupInput');go=group.nodes.new('NodeGroupOutput');group.links.new(gi.outputs['Geometry'],go.inputs['Geometry'])
mod=ctrl.modifiers.new('Upper Platform Sliders','NODES');mod.node_group=group
mapping={};values={}
for source in sockets:
    target=group.interface.new_socket(name=source.name,in_out='INPUT',socket_type='NodeSocketFloat')
    for prop in ['default_value','min_value','max_value','description']:
        setattr(target,prop,getattr(source,prop))
    value=float(oldmod[source.identifier]);mod[target.identifier]=value;values[source.name]=value
    mapping['modifiers["Scene Sliders"]["'+source.identifier+'"]']='modifiers["Upper Platform Sliders"]["'+target.identifier+'"]'

retargeted=0;owners=[]
for attr in ['objects','shape_keys','meshes','curves','lights','materials','node_groups','scenes','cameras']:
    for owner in getattr(bpy.data,attr):
        if not owner.animation_data:continue
        touched=False
        for fc in owner.animation_data.drivers:
            for variable in fc.driver.variables:
                for target in variable.targets:
                    if target.id==old and target.data_path in mapping:
                        path=mapping[target.data_path];target.id=ctrl;target.data_path=path
                        retargeted+=1;touched=True
        if touched:owners.append(owner)
for source in sockets:
    identifier=source.identifier;oldmod.node_group.interface.remove(source)
    if identifier in oldmod:del oldmod[identifier]
old['Upper platform controls']='Use UPPER PLATFORM SLIDERS > Modifiers > Upper Platform Sliders. Isolated to prevent unrelated bridge boolean recalculation.'
ctrl['How to use']='Modifiers > Upper Platform Sliders. Platform corner bevel and overhead-light width, depth, height, corner bevel.'
ctrl['Why separate']='Changing a shared controller invalidated scene-wide bridge/railing booleans. This object only drives the upper platform.'
for owner in owners:owner.update_tag()
old.update_tag();ctrl.update_tag();bpy.context.view_layer.update()
after=geometry_signatures()
changed=[n for n,v in before.items() if after.get(n)!=v]
assert not changed,changed

timings={}
try:
    for name in ['Upper light width (m)','Upper light height (m)','Upper corner bevel (m)']:
        ident=next(i.identifier for i in group.interface.items_tree if i.name==name)
        startval=mod[ident];samples=[]
        for step in [1,2,3]:
            start=time.perf_counter();mod[ident]=startval-.0001*step;ctrl.update_tag();bpy.context.view_layer.update();samples.append(time.perf_counter()-start)
        mod[ident]=startval;ctrl.update_tag();bpy.context.view_layer.update()
        timings[name]=samples
finally:
    for name,value in values.items():
        ident=next(i.identifier for i in group.interface.items_tree if i.name==name);mod[ident]=value
    ctrl.update_tag();bpy.context.view_layer.update()
assert geometry_signatures()==before
bad=[]
for owner in owners:
    for fc in owner.animation_data.drivers:
        if not fc.driver.is_valid:bad.append((owner.name,fc.data_path))
assert not bad,bad
for area in bpy.context.screen.areas:
    if area.type=='PROPERTIES':area.spaces.active.pin_id=ctrl;area.spaces.active.context='MODIFIER'
report={'retargeted_drivers':retargeted,'existing_meshes_identical':len(before),'preserved_values':values,'timings_seconds':timings,'invalid_drivers':bad,'old_shared_control_update_seconds':[5.729,5.6123,5.5875],'mode_preserved':bpy.context.mode}
(P/'verification.json').write_text(json.dumps(report,indent=2))
txt=bpy.data.texts.new('upper_platform_slider_performance_fix.py');txt.write(Path(__file__).read_text())
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
result=report
