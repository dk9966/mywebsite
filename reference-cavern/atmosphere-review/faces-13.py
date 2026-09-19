"""Embed reusable CC0 scanned rock volumes into the authored cavern masses.
Rock Face 01 by Dario Barresi / Poly Haven. One ~20K-triangle mesh is instanced.
"""
from mathutils import Matrix
before=set(S.objects)
bpy.ops.import_scene.gltf(filepath=os.path.join(ROOT,'assets','rock_face_01','rock_face_01_2k.gltf'))
imported=[o for o in S.objects if o not in before]
proto=next(o for o in imported if o.type=='MESH')
proto.data.transform(proto.matrix_world);proto.matrix_world=Matrix.Identity(4)
vs=[v.co for v in proto.data.vertices];cx=(min(v.x for v in vs)+max(v.x for v in vs))/2;y0=min(v.y for v in vs);z0=min(v.z for v in vs)
for v in proto.data.vertices:v.co-=Vector((cx,y0,z0))
mesh=proto.data;mesh.name='Geology | scanned sediment face • shared 20K'
for m in mesh.materials:
 m.name='GEOLOGY | scanned sedimentary faces';nt=m.node_tree;p=nt.nodes.get('Principled BSDF');p.inputs['Specular IOR Level'].default_value=.26
 for n in nt.nodes:
  if n.type=='TEX_IMAGE' and n.image:
   if '_diff_' in n.image.name:
    source=n.image;w,h=source.size;buf=np.empty(w*h*4,dtype=np.float32);source.pixels.foreach_get(buf);a=buf.reshape(-1,4);rgb=a[:,:3];lin=np.where(rgb<=.04045,rgb/12.92,((rgb+.055)/1.055)**2.4);gray=lin@np.array([.2126,.7152,.0722],dtype=np.float32);a[:,:3]=gray[:,None]*np.array([.24,.27,.29]);a[:,:3]=np.where(a[:,:3]<=.0031308,a[:,:3]*12.92,1.055*np.maximum(a[:,:3],0)**(1/2.4)-.055)
    im=bpy.data.images.new('cavern_scanned_faces_color_2k',width=w,height=h,alpha=True);im.colorspace_settings.name='sRGB';im.pixels.foreach_set(a.ravel());im.filepath_raw=os.path.join(TEX,'cavern_scanned_faces_color_2k.png');im.file_format='PNG';im.save();im.pack();n.image=im
   else:n.image.pack()
 m['source']='https://polyhaven.com/a/rock_face_01';m['author']='Dario Barresi';m['license']='CC0'
co=bpy.data.collections['01 | CAVERN • structural geology']
placements=[
 ('Left lower',(-20.5,-.8,11.6),(1.1,1.0,1.2),(0,.06,.10)),
 ('Left middle',(-20.7,-.35,15.3),(1.3,1.0,1.35),(.02,-.06,-.12)),
 ('Left upper',(-20.6,.1,19.5),(1.1,1.0,1.4),(0,.09,.06)),
 ('Inner left',(-9.3,17.2,14.6),(1.15,.9,1.35),(0,.05,-.12)),
 ('Inner left upper',(-9.8,18.1,18.7),(1.25,1.0,1.45),(0,-.06,.10)),
 ('Right lower',(22.1,.4,11.2),(-1.1,1.0,1.3),(0,-.03,-.07)),
 ('Right middle',(22.3,.8,15.4),(-1.2,1.0,1.35),(0,.05,.10)),
 ('Right upper',(22.1,1.3,19.6),(-1.1,1.0,1.4),(0,-.07,-.10)),
 ('About overhang',(14.0,2.3,14.0),(1.8,.70,.62),(0,pi,0)),
 ('Ceiling left',(-5.6,23.2,24.7),(.8,1.0,1.9),(0,pi,.1)),
 ('Ceiling center',(2.0,22.8,25.6),(.9,1.0,1.9),(0,pi,-.12)),
]
for tag,pos,scale,rot in placements:
 o=bpy.data.objects.new('Geology | scanned fractured '+tag,mesh);co.objects.link(o);o.location=pos;o.scale=scale;o.rotation_euler=rot;o['component']='Shared scanned sedimentary rock volume embedded in existing cavern.'
for o in imported:bpy.data.objects.remove(o,do_unlink=True)
S['scanned_rock_instances']=len(placements)
print('Embedded scanned rock modules',len(placements),'triangles each',sum(len(p.vertices)-2 for p in mesh.polygons),flush=True)

# Sparse shallow abrasion on walked metal surfaces. All marks lie on actual deck geometry.
wearco=bpy.data.collections['26 | SECONDARY • service details']
scuff=mat('WEAR | exposed brushed steel',(.11,.125,.13),.78,.48)
grit=mat('WEAR | dark embedded scuff',(.022,.028,.032),.45,.84)
S.view_layers[0].update();dg=bpy.context.evaluated_depsgraph_get();rng=random.Random(7331)
verts=[];faces=[];ids=[]
for area,cx,cy,z,rmin,rmax,count in [('Hub',0,5.4,7.65,1.6,5.0,45),('About',13.75,-1.2,7.7,3.4,5.4,26)]:
 for k in range(count):
  angle=rng.uniform(0,2*pi);rr=rng.uniform(rmin,rmax);x=cx+rr*cos(angle);y=cy+rr*sin(angle)
  hit,loc,norm,idx,obj,M=S.ray_cast(dg,Vector((x,y,z+1.0)),Vector((0,0,-1)),distance=2)
  if not hit or norm.z<.98 or not any(t in obj.name.lower() for t in ['floor','plate','tile']):continue
  direction=rng.uniform(0,pi)
  for j in range(rng.randint(2,5)):
   length=rng.uniform(.10,.48);width=rng.uniform(.005,.017);a=direction+rng.uniform(-.10,.10)
   tangent=Vector((cos(a),sin(a),0));side=Vector((-sin(a),cos(a),0));p=loc+norm*.0025+side*(j*.022)
   base=len(verts);verts.extend([p-tangent*length*.5-side*width*.2,p+tangent*length*.46-side*width*.6,p+tangent*length*.5+side*width*.1,p-tangent*length*.38+side*width*.5]);faces.append((base,base+1,base+2,base+3));ids.append(0 if rng.random()<.68 else 1)
me=bpy.data.meshes.new('Deck | sparse abrasion marks');me.from_pydata(verts,[],faces);me.materials.append(scuff);me.materials.append(grit)
for f,i in zip(me.polygons,ids):f.material_index=i
ob=bpy.data.objects.new('Deck wear | sparse directional abrasion',me);wearco.objects.link(ob)
print('Surface abrasion strokes',len(faces),flush=True)
