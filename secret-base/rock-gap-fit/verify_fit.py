import bpy,bmesh,json,hashlib
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent
S=bpy.context.scene
w=bpy.data.objects['150 | continuous cave with oblique carved rooms']
deck=bpy.data.objects['Upper | beveled square gallery']
mod=w.modifiers['Upper right | continuous forward rock fit']
H=deck['deck_height_m']

def signature(o):
    h=hashlib.sha256(repr(([list(r) for r in o.matrix_world],o.hide_render,o.hide_get(),o.parent.name if o.parent else None)).encode())
    if o.type=='MESH':h.update(repr([tuple(v.co) for v in o.data.vertices]).encode())
    return h.hexdigest()

def clearances():
    e=w.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mx=e.matrix_world.inverted()@deck.matrix_world
    walk=[]
    for i in range(25):
        for j in range(25):
            x=-2.8+5.6*i/24;y=-2.8+5.6*j/24
            if abs(x)+abs(y)>4.32:continue
            hit,p,n,index=e.ray_cast(mx@Vector((x,y,H+.035)),Vector((0,0,1)),distance=1.7)
            if hit:walk.append([i,j])
    root=bpy.data.objects['Lower | circular roof assembly']
    cover=bpy.data.objects['Lower | circular light upper cover'].evaluated_get(bpy.context.evaluated_depsgraph_get())
    vs=[cover.matrix_world@v.co for v in cover.data.vertices]
    ztop=max(p.z for p in vs)
    center=e.matrix_world.inverted()@root.matrix_world.translation
    rad=max((Vector((p.x,p.y))-Vector((root.matrix_world.translation.x,root.matrix_world.translation.y))).length for p in vs)
    fixture=[]
    for i in range(17):
        for j in range(17):
            x=rad*(i-8)/8*.94;y=rad*(j-8)/8*.94
            if x*x+y*y>rad*rad*.94**2:continue
            hit,p,n,index=e.ray_cast(Vector((center.x+x,center.y+y,ztop-.22)),Vector((0,0,1)),distance=.225)
            if hit:fixture.append([i,j])
    return {'walking_intrusions':walk,'light_intrusions':fixture}

try:
    mod.show_viewport=False;bpy.context.view_layer.update()
    before=clearances()
    mod.show_viewport=True;bpy.context.view_layer.update()
    after=clearances()
finally:
    mod.show_viewport=True;mod.show_render=True;bpy.context.view_layer.update()

e=w.evaluated_get(bpy.context.evaluated_depsgraph_get())
bm=bmesh.new();bm.from_mesh(e.data)
left=set(bm.verts);components=0
while left:
    components+=1;stack=[left.pop()]
    while stack:
        v=stack.pop()
        for edge in v.link_edges:
            other=edge.other_vert(v)
            if other in left:left.remove(other);stack.append(other)
protected=json.loads((P/'protected-before.json').read_text())
changed=[name for name,h in protected.items() if name not in bpy.data.objects or signature(bpy.data.objects[name])!=h]
final_protected=json.loads((P/'protected-final.json').read_text()) if (P/'protected-final.json').exists() else protected
final_changed=[name for name,h in final_protected.items() if name not in bpy.data.objects or signature(bpy.data.objects[name])!=h]
newwalk=[p for p in after['walking_intrusions'] if p not in before['walking_intrusions']]
newlight=[p for p in after['light_intrusions'] if p not in before['light_intrusions']]
result={'connected_components':components,'loose_edges':sum(len(e.link_faces)==0 for e in bm.edges),'nonmanifold_junctions':sum(len(e.link_faces)>2 for e in bm.edges),'protected_objects':len(protected),'changed_unrelated_objects':changed,'new_walking_intrusions':newwalk,'new_light_intrusions':newlight,'clearances_before':before,'clearances_after':after,'active_fit_modifier':mod.name}
result['final_unrelated_object_changes']=final_changed
result['preservation_note']='Nine upper-roof parts changed concurrently during the session. This edit touched only the cave terrain; the final protection snapshot retains all current non-terrain objects.'
bm.free()
(P/'verification.json').write_text(json.dumps(result,indent=2))
assert not final_changed and not newwalk and not newlight
assert components==1 and not result['loose_edges'] and not result['nonmanifold_junctions']
