import bpy,bmesh,json
from mathutils import Vector
w=bpy.data.objects['150 | continuous cave with oblique carved rooms']
deck=bpy.data.objects['Upper | beveled square gallery']
KEY='Upper right | pulled forward continuous rock'
if w.get('forward_patch_subdivided'):
    result={'already_done':True}
else:
    key=w.data.shape_keys.key_blocks[KEY]
    key.value=0
    bpy.context.view_layer.update()
    mx=deck.matrix_world.inverted()@w.matrix_world
    imx=mx.inverted()
    bm=bmesh.new();bm.from_mesh(w.data)
    layers={name:bm.verts.layers.shape[name] for name in bm.verts.layers.shape.keys()}
    basis=layers['Basis']
    keys=w.data.shape_keys.key_blocks
    values=[(layers[k.name],layers[k.relative_key.name],k.value) for k in keys if k.name not in ('Basis',KEY) and not k.mute]
    for v in bm.verts:
        p=v[basis].copy()
        for lay,rel,value in values:p+=(v[lay]-v[rel])*value
        v.co=mx@p
    def overlaps(f):
        return all(min(v.co[i] for v in f.verts)<hi and max(v.co[i] for v in f.verts)>lo for i,lo,hi in [(0,-2.8,4.8),(1,-6.7,-2.75),(2,9.5,14.9)])
    before=len(bm.verts)
    for _ in range(4):
        local={e for f in bm.faces if overlaps(f) for e in f.edges}
        edges=[e for e in local if e.calc_length()>.28]
        if not edges:break
        bmesh.ops.subdivide_edges(bm,edges=edges,cuts=1,use_grid_fill=True)
    for v in bm.verts:
        p=v[basis].copy()
        for lay,rel,value in values:p+=(v[lay]-v[rel])*value
        correction=imx@v.co-p
        for lay in layers.values():v[lay]+=correction
        v.co=v[basis]
    bmesh.ops.triangulate(bm,faces=[f for f in bm.faces if len(f.verts)>3])
    after=len(bm.verts)
    bm.to_mesh(w.data);bm.free();w.data.update()
    w['forward_patch_subdivided']=True
    bpy.context.view_layer.update()
    result={'vertices_before':before,'vertices_after':after}
