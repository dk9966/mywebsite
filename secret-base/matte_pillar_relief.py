"""Restore approved silhouette and add restrained stone relief and matte lighting."""
import bpy, math, random, os
from mathutils import Vector
ROOT='/Users/danielku/mywebsite/secret-base/'
backup=ROOT+'rock-review/before-matte-relief.blend'
if not os.path.exists(backup):bpy.ops.wm.save_as_mainfile(filepath=backup,copy=True)
random.seed(528)
col=bpy.data.collections.get('Pillar_Surface_Relief')
if col:
    for o in list(col.objects):bpy.data.objects.remove(o,do_unlink=True)
else:
    col=bpy.data.collections.new('Pillar_Surface_Relief');bpy.context.scene.collection.children.link(col)
mats=[]
for j in range(5):
    m=bpy.data.materials.get('Pillar matte relief %d'%j) or bpy.data.materials.new('Pillar matte relief %d'%j)
    m.use_nodes=True;bs=m.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Base Color'].default_value=(.025+j*.004,.035+j*.005,.048+j*.006,1)
    bs.inputs['Roughness'].default_value=.9;bs.inputs['Specular IOR Level'].default_value=.2
    mats.append(m)
changed=[]
for key in ['project','about','experience','contact']:
    pillar=bpy.data.objects['island_pillar_'+key]
    # The stored baseline is the approved integrated rim, before the rejected widening.
    for o in [pillar]+[o for o in bpy.data.collections['deck_'+key].objects if 'pillar_veins' in o.name and o.type=='MESH']:
        a=o.data.attributes.get('gentle_taper_original')
        if a:
            for v,p in zip(o.data.vertices,a.data):v.co=p.vector
            o.data.update()
    for slot in pillar.material_slots:
        m=slot.material.copy();m.name='Pillar matte stone '+key;slot.material=m
        nt=m.node_tree
        for n in nt.nodes:
            if n.type=='BSDF_PRINCIPLED':
                for name,value in [('Roughness',.92),('Specular IOR Level',.18),('Coat Weight',0)]:
                    for link in list(n.inputs[name].links):nt.links.remove(link)
                    n.inputs[name].default_value=value
                noise=nt.nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=24;noise.inputs['Detail'].default_value=3
                bump=nt.nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.22;bump.inputs['Distance'].default_value=.028
                nt.links.new(noise.outputs['Fac'],bump.inputs['Height']);nt.links.new(bump.outputs['Normal'],n.inputs['Normal'])
    bpy.context.view_layer.update()
    cx,cy=pillar.matrix_world.translation.xy;inv=pillar.matrix_world.inverted()
    top=max((pillar.matrix_world@v.co).z for v in pillar.data.vertices)
    vs=[];fs=[]
    for i in range(145):
        a=random.random()*math.tau;z=random.uniform(.65,top-.42)
        outward=Vector((math.cos(a),math.sin(a),0));tangent=Vector((-math.sin(a),math.cos(a),0))
        origin=Vector((cx,cy,z))+outward*4
        hit,loc,normal,idx=pillar.ray_cast(inv@origin,(inv.to_3x3()@(-outward)).normalized())
        if not hit:continue
        p=pillar.matrix_world@loc
        w=random.uniform(.10,.25);h=random.uniform(.20,.65);thick=random.uniform(.045,.12)
        start=len(vs)
        for depth in [-.045,thick]:
            for tx,dz in [(-w/2,-h/2),(w/2,-h/2),(w/2,h/2),(-w/2,h/2)]:
                v=p+tangent*tx+Vector((0,0,dz))+outward*depth
                vs.append(v)
        fs.extend([tuple(start+k for k in f) for f in [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]])
    me=bpy.data.meshes.new('Stone relief '+key);me.from_pydata(vs,[],fs);me.update()
    o=bpy.data.objects.new('Pillar | fine raised stone '+key,me);col.objects.link(o)
    for m in mats:me.materials.append(m)
    for i,p in enumerate(me.polygons):p.material_index=(i//6)%len(mats)
    changed.append(key)
for o in bpy.context.scene.objects:
    if o.type!='LIGHT':continue
    if 'shaft' in o.name or 'foundation grazing' in o.name:
        if 'matte_relief_original_energy' not in o:o['matte_relief_original_energy']=o.data.energy
        o.data=o.data.copy()
        factor=.24 if ('back' not in o.name and 'rim' not in o.name) else .4
        o.data.energy=o['matte_relief_original_energy']*factor
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'base.blend')
result={'restored_pillars':changed,'roughness':.92,'primary_grazing_power_fraction':.24,'relief_objects':len(col.objects)}
