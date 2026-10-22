import bpy
import bmesh
import math
from mathutils import Vector

wall=bpy.data.objects['150 | continuous cave with oblique carved rooms']
source=bpy.data.meshes[wall['infill_source_mesh']]
wall.data=source.copy();wall.data.name='Cave wall | complete side walls'
mesh=wall.data
bm=bmesh.new();bm.from_mesh(mesh)
t_layer=bm.verts.layers.float['wall_path_t'];v_layer=bm.verts.layers.float['wall_height_v']
rim=sorted([v for v in bm.verts if v.is_boundary and v[v_layer]>.9999 and 40<=v[t_layer]<=105],key=lambda v:v[t_layer])
assert len(rim)==66
cols=[];added=[]
for k,base in enumerate(rim):
    t=base[t_layer];co=base.co.copy()
    # Match the existing full-height cliff and retain a continuous enclosure.
    top_z=17.2
    if k==0 or k==len(rim)-1:top_z=co.z
    rise=max(0,top_z-co.z)
    target=co.copy();target.z=top_z
    # Flare the upper wall away from the fixed camera's view. The approved
    # lower contour remains the exact welded base of the new faces.
    extent=max(abs(co.x),.75*max(0,co.y+18.1955)+1.2)
    if co.x<-1:target.x=-extent
    elif co.x>1:target.x=extent
    target.x=co.x+(target.x-co.x)*min(1,rise/4)
    if rise<.08:
        cols.append([base]);continue
    steps=max(1,math.ceil(rise/.8))
    column=[base]
    for j in range(1,steps+1):
        f=j/steps
        p=co.lerp(target,f)
        p.x=co.x+(target.x-co.x)*(f**.6)
        # Low-amplitude rock variation; all faces stay flat shaded.
        envelope=math.sin(math.pi*f)*min(1,rise/2)
        p.x+=.18*envelope*math.sin(t*1.79+p.z*.87)
        p.y+=.18*envelope*math.sin(t*.91-p.z*1.13)
        v=bm.verts.new(p);v[t_layer]=t;v[v_layer]=1+f
        column.append(v);added.append(v)
    cols.append(column)

faces=[]
for a,b in zip(cols,cols[1:]):
    ia=ib=0;na=len(a)-1;nb=len(b)-1
    while ia<na or ib<nb:
        fa=(ia+1)/na if ia<na else float('inf')
        fb=(ib+1)/nb if ib<nb else float('inf')
        if abs(fa-fb)<1e-8:
            faces.append(bm.faces.new((a[ia],b[ib],b[ib+1])))
            faces.append(bm.faces.new((a[ia],b[ib+1],a[ia+1])))
            ia+=1;ib+=1
        elif fa<fb:
            faces.append(bm.faces.new((a[ia],b[ib],a[ia+1])));ia+=1
        else:
            faces.append(bm.faces.new((a[ia],b[ib],b[ib+1])));ib+=1
for face in faces:face.smooth=False
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
bm.to_mesh(mesh);bm.free();mesh.update()
for f in mesh.polygons:f.use_smooth=False
wall['upper_wall_fill']='Both side gaps above the low contour filled to surrounding cliff height with welded flat-shaded rock faces. Lower contour, platform contact, and camera preserved.'
bpy.context.view_layer.update()
result={'new_faces':len(faces),'new_vertices':len(added),'total_faces':len(mesh.polygons),'wall_height':17.2}
