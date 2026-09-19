"""Unify cave and pillars with restrained mid-scale relief and coherent stone tones."""
import bpy, random, math, os
from mathutils import Vector
random.seed(917)
ROOT='/Users/danielku/mywebsite/secret-base/'
backup=ROOT+'rock-review/before-harmonized-stone.blend'
if not os.path.exists(backup):bpy.ops.wm.save_as_mainfile(filepath=backup,copy=True)
# Pillar surface patches share nearly the same color as the host stone.
for key in ['project','about','experience','contact']:
    o=bpy.data.objects['island_pillar_'+key]
    for mat in o.data.materials:
        nt=mat.node_tree
        for n in nt.nodes:
            if n.type=='BSDF_PRINCIPLED':
                n.inputs['Base Color'].default_value=(.018,.024,.032,1)
                n.inputs['Roughness'].default_value=.74;n.inputs['Specular IOR Level'].default_value=.28
            if n.type=='TEX_NOISE':n.inputs['Scale'].default_value=7
            if n.type=='BUMP':n.inputs['Strength'].default_value=.16;n.inputs['Distance'].default_value=.035
for j in range(5):
    mat=bpy.data.materials['Pillar matte relief %d'%j];bs=mat.node_tree.nodes.get('Principled BSDF')
    f=.96+j*.025
    bs.inputs['Base Color'].default_value=(.018*f,.024*f,.032*f,1)
    bs.inputs['Roughness'].default_value=.75;bs.inputs['Specular IOR Level'].default_value=.28
# Retain only half of the small boxes and enlarge their footprint on the surface.
for o in bpy.data.collections['Pillar_Surface_Relief'].objects:
    if o.get('coarser_relief'):continue
    vs=[];fs=[];old=o.data
    for i in range(len(old.vertices)//8):
        if i%2:continue
        pts=[old.vertices[i*8+j].co.copy() for j in range(8)]
        rear=sum(pts[:4],Vector())/4;front=sum(pts[4:],Vector())/4
        start=len(vs)
        for j,p in enumerate(pts):
            center=rear if j<4 else front
            p=center+(p-center)*1.5
            if j>=4:p-= (front-rear)*.2
            vs.append(p)
        fs.extend([tuple(start+j for j in f) for f in [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]])
    me=bpy.data.meshes.new(o.name+' broad relief');me.from_pydata(vs,[],fs);me.update()
    for m in old.materials:me.materials.append(m)
    for i,p in enumerate(me.polygons):p.material_index=(i//6)%len(me.materials)
    o.data=me;o['coarser_relief']=True
# Narrow the cave's material palette; surface orientation supplies most contrast.
cave=bpy.data.collections['Cave_Backdrop'];mats=[]
for o in cave.objects:
    if o.type=='MESH' and ('walls' in o.name or 'bedrock' in o.name):
        for m in o.data.materials:
            if m not in mats:mats.append(m)
for j,m in enumerate(mats):
    nt=m.node_tree;bs=nt.nodes.get('Principled BSDF')
    if not bs:continue
    f=.91+.18*j/max(1,len(mats)-1)
    bs.inputs['Base Color'].default_value=(.023*f,.034*f,.049*f,1)
    bs.inputs['Roughness'].default_value=.78;bs.inputs['Specular IOR Level'].default_value=.28
    noise=nt.nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=6;noise.inputs['Detail'].default_value=2
    bump=nt.nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.25;bump.inputs['Distance'].default_value=.075
    nt.links.new(noise.outputs['Fac'],bump.inputs['Height']);nt.links.new(bump.outputs['Normal'],bs.inputs['Normal'])
# Broad raised facets on the existing cave, not a new cave silhouette.
coll=bpy.data.collections.get('Cave_Surface_Relief')
if coll:
    for o in list(coll.objects):bpy.data.objects.remove(o,do_unlink=True)
else:
    coll=bpy.data.collections.new('Cave_Surface_Relief');bpy.context.scene.collection.children.link(coll)
vs=[];fs=[];centers=[]
for host in cave.objects:
    if host.type!='MESH' or not ('walls' in host.name or 'bedrock foundation' in host.name):continue
    polygons=list(host.data.polygons);random.shuffle(polygons);count=0
    limit=210 if 'walls' in host.name else 22
    for poly in polygons:
        if count>=limit:break
        if poly.area<.10:continue
        pts=[host.matrix_world@host.data.vertices[i].co for i in poly.vertices]
        c=sum(pts,Vector())/len(pts)
        if any((c-q).length<.68 for q in centers):continue
        normal=(host.matrix_world.to_3x3()@poly.normal).normalized()
        if 'walls' in host.name:
            toward=Vector((21,1,4))-c
            if normal.dot(toward)<0:normal=-normal
        else:
            center=sum((host.matrix_world@Vector(v) for v in host.bound_box),Vector())/8
            if normal.dot(c-center)<0:normal=-normal
        extent=max((p-c).length for p in pts)
        scale=min(.88,1.05/max(extent,.01))
        start=len(vs);n=len(pts);depth=random.uniform(.02,.055)
        for offset,shrink in [(-.035,1),(depth,.92)]:
            vs.extend([c+(p-c)*scale*shrink+normal*offset for p in pts])
        fs.append(tuple(start+n+i for i in range(n)))
        for i in range(n):fs.append((start+i,start+(i+1)%n,start+n+(i+1)%n,start+n+i))
        centers.append(c);count+=1
me=bpy.data.meshes.new('Cave broad fractured facets');me.from_pydata(vs,[],fs);me.update()
o=bpy.data.objects.new('Cave | broad stone relief',me);coll.objects.link(o)
for m in mats:me.materials.append(m)
for p in me.polygons:p.material_index=len(mats)//2
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'base.blend')
result={'cave_raised_facets':len(centers),'pillar_patches_each':73,'pillar_roughness':.74,'cave_roughness':.78}
