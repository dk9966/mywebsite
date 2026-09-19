"""Anchor the lamp displaced by the new entrance, then render final review."""
import bpy, bmesh
from mathutils import Vector
source=Vector((21.7464,-2.6751,7.32228565))
target=Vector((21.94999924,-2.6329536,7.3974))
delta=target-source
for name in ['deck_lantern_posts_b','deck_lantern_glass_b']:
    ob=bpy.data.objects[name]; bm=bmesh.new(); bm.from_mesh(ob.data); unseen=set(bm.verts)
    while unseen:
        v=unseen.pop(); comp={v}; stack=[v]
        while stack:
            p=stack.pop()
            for e in p.link_edges:
                q=e.other_vert(p)
                if q in unseen: unseen.remove(q); comp.add(q); stack.append(q)
        center=sum((ob.matrix_world@v.co for v in comp),Vector())/len(comp)
        if abs(center.x-source.x)<.06 and abs(center.y-source.y)<.06:
            local_delta=ob.matrix_world.inverted().to_3x3()@delta
            for v in comp: v.co+=local_delta
    bm.to_mesh(ob.data); bm.free()
for ob in bpy.data.collections['deck_project'].objects:
    if ob.type=='LIGHT' and 'lantern' in ob.name:
        p=ob.matrix_world.translation
        if abs(p.x-source.x)<.12 and abs(p.y-source.y)<.12:
            mw=ob.matrix_world.copy(); mw.translation+=delta; ob.matrix_world=mw
scene=bpy.context.scene; cam=scene.camera
for detail in (False,True):
    cam.location=(31,-10,13) if detail else (37.3,-18,18)
    cam.rotation_euler=(Vector((21.3,-4.65,6.85 if detail else 4.6))-cam.location).to_track_quat('-Z','Y').to_euler()
    cam.data.ortho_scale=7.3 if detail else 16.5
    scene.render.filepath='/Users/danielku/mywebsite/secret-base/bridge-review/iteration-3'+('-detail' if detail else '')+'.png'
    bpy.ops.render.render(write_still=True)
