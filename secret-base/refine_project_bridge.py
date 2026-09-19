"""Second pass: explicit open rim geometry, seamless railing arcs and thresholds."""
import bpy, bmesh, math
from mathutils import Vector
CX=21.299999237060547
F=6.871178627
R=2.712
HALF=.65

def mesh_object(name, verts, faces, mat, coll, parent):
    old=bpy.data.objects.get(name)
    if old: bpy.data.objects.remove(old,do_unlink=True)
    me=bpy.data.meshes.new(name); me.from_pydata(verts,[],faces); me.update()
    bm=bmesh.new(); bm.from_mesh(me); bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces)); bm.to_mesh(me); bm.free()
    ob=bpy.data.objects.new(name,me); coll.objects.link(ob)
    me.materials.append(bpy.data.materials[mat])
    mw=ob.matrix_world.copy(); ob.parent=parent; ob.matrix_world=mw
    return ob

def arc_geometry(cx,cy,r0,r1,z0,z1,start,end):
    n=192; vs=[]; fs=[]
    for i in range(n+1):
        a=start+(end-start)*i/n
        for r,z in [(r0,z0),(r1,z0),(r1,z1),(r0,z1)]:
            vs.append((cx+r*math.cos(a),cy+r*math.sin(a),z))
    for i in range(n):
        for j in range(4): fs.append((4*i+j,4*i+(j+1)%4,4*(i+1)+(j+1)%4,4*(i+1)+j))
    fs.extend([(3,2,1,0),(4*n,4*n+1,4*n+2,4*n+3)])
    return vs,fs

def add_box(vs,fs,x,y,z,sx,sy,sz,a=0):
    j=len(vs)
    for dx,dy,dz in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]:
        u,v=dx*sx/2,dy*sy/2
        vs.append((x+u*math.cos(a)-v*math.sin(a),y+u*math.sin(a)+v*math.cos(a),z+dz*sz/2))
    fs.extend([tuple(j+k for k in face) for face in [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]])

for suffix,cy,angle,collname,parentname in [('_b',0,-math.pi/2,'deck_project','island_pillar_project'),('_empty',-9.3,math.pi/2,'deck_empty','island_pillar_empty')]:
    coll=bpy.data.collections[collname]; parent=bpy.data.objects[parentname]
    gap=math.asin(HALF/R); start=angle+gap; end=angle+math.tau-gap
    vs=[]; fs=[]
    for z0,z1 in [(7.154,7.1717),(7.2866,7.3043)]:
        v,f=arc_geometry(CX,cy,R-.019,R+.019,z0,z1,start,end)
        j=len(vs); vs+=v; fs += [tuple(j+k for k in face) for face in f]
    if suffix=='_b':
        # Preserve posts under the original lamps, excluding crowded mouth posts.
        for name in ['deck_railing_b_before_bridge','deck_railing_back_b_before_bridge']:
            src=bpy.data.objects[name]; bm=bmesh.new(); bm.from_mesh(src.data); unseen=set(bm.verts)
            while unseen:
                v=unseen.pop(); comp={v}; todo=[v]
                while todo:
                    p=todo.pop()
                    for e in p.link_edges:
                        q=e.other_vert(p)
                        if q in unseen: unseen.remove(q); comp.add(q); todo.append(q)
                if len(comp)>24: continue
                pts=[src.matrix_world@v.co for v in comp]
                mid=sum(pts,Vector())/len(pts)
                if mid.y<-2.3 and abs(mid.x-CX)<.85: continue
                # retain original post/cap forms; normalize the taller rear uprights
                idx={v:len(vs)+i for i,v in enumerate(comp)}
                for v in comp:
                    p=src.matrix_world@v.co
                    if 'back' in name and abs(p.z-7.4327)<.002: p.z=7.3223
                    vs.append(tuple(p))
                faces={face for v in comp for face in v.link_faces}
                fs += [tuple(idx[v] for v in face.verts) for face in faces]
            bm.free()
    else:
        # Same slim profile, evenly spaced around the otherwise empty deck.
        count=31
        for i in range(1,count):
            a=start+(end-start)*i/count
            add_box(vs,fs,CX+R*math.cos(a),cy+R*math.sin(a),(6.91057+7.3223)/2,.05,.05,7.3223-6.91057,a)
    mesh_object('deck_railing'+suffix,vs,fs,'mcWood',coll,parent)
    old=bpy.data.objects.get('deck_railing_back'+suffix)
    if old: bpy.data.objects.remove(old,do_unlink=True)
    v,f=arc_geometry(CX,cy,2.642,2.792,6.855178,6.936178,start,end)
    mesh_object('deck_parapet'+suffix,v,f,'stationFloorSatin',coll,parent)

# No paving pieces overlap the original circular deck or form raised thresholds.
for o in list(bpy.data.objects):
    if o.name.startswith('bridge_paving_'):
        cy=o.matrix_world.translation.y
        if cy > -2.90 or cy < -6.40:
            bpy.data.objects.remove(o,do_unlink=True)
        else:
            for v in o.data.vertices: v.co.z-=.006

bpy.context.view_layer.update()
scene=bpy.context.scene; cam=scene.camera
cam.location=(CX+16,-18,18)
cam.rotation_euler=(Vector((CX,-4.65,4.6))-cam.location).to_track_quat('-Z','Y').to_euler()
cam.data.ortho_scale=16.5
scene.render.filepath='/Users/danielku/mywebsite/secret-base/bridge-review/iteration-2.png'
bpy.ops.render.render(write_still=True)
cam.location=(31,-10,13)
cam.rotation_euler=(Vector((CX,-4.65,6.85))-cam.location).to_track_quat('-Z','Y').to_euler()
cam.data.ortho_scale=7.3
scene.render.filepath='/Users/danielku/mywebsite/secret-base/bridge-review/iteration-2-detail.png'
bpy.ops.render.render(write_still=True)
