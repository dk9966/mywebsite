exec(compile(open('/Users/danielku/mywebsite/secret-base/refine_wired_depth.py').read().split('# Remove unsupported')[0],'helpers','exec'))
random.seed(533)
# Break horizontal pedestal courses into coherent oblique fracture systems.
for o in bpy.data.objects:
 if o.type!='MESH' or 'bedrock foundation island' not in o.name:continue
 pillar=bpy.data.objects[o.name.split('foundation ')[1]];cx,cy=pillar.matrix_world.translation.xy
 for v in o.data.vertices:
  if v.co.z<-.35:
   t=min(1,(-v.co.z-.35)/.8);a=math.atan2(v.co.y-cy,v.co.x-cx)
   v.co.z+=t*(.32*math.sin(3*a+v.co.z*.6)+.19*math.sin(a*7+v.co.z))
   rr=1+.045*math.sin(a*5+v.co.z*.7);v.co.x=cx+(v.co.x-cx)*rr;v.co.y=cy+(v.co.y-cy)*rr
 o.data.update()
# Larger partially embedded fractured blocks interrupt the radial ring pattern.
from mathutils.bvhtree import BVHTree
for o in [o for o in bpy.data.objects if 'bedrock foundation island' in o.name]:
 vs=[o.matrix_world@v.co for v in o.data.vertices];bvh=BVHTree.FromPolygons(vs,[list(f.vertices) for f in o.data.polygons]);qs=[v-C for v in vs];xmin=min(v.dot(R) for v in qs);xmax=max(v.dot(R) for v in qs);ymax=max(v.dot(U) for v in qs)
 for i in range(32):
  x=random.uniform(xmin,xmax);y=random.uniform(ymax-6,ymax-.3);hit,n,idx,dist=bvh.ray_cast(p(x,y,35),-D,90)
  if hit:
   q=hit-C;r=random.uniform(.4,.85);chunk=crag('Wired | broad oblique basalt fracture',(q.dot(R),q.dot(U),q.dot(D)-r*.3),(r,random.uniform(.65,1.25),r*.65),1)
   recv=bpy.data.collections['Wired Foundation light receivers'];recv.objects.link(chunk)
# Blue haze resides in four winding abyss channels.
for o in col.objects:
 if any(k in o.name for k in ['channel mist pocket','blue mist along cave bed']):o.hide_render=True;o.hide_set(True)
old=bpy.data.objects['Wired | low curling chasm mist']
for i,(xyz,sc) in enumerate([((-10.8,-8,1),(4,9,6)),((-1.4,-9,-1),(4,8,7)),((4.8,-7,0),(4.5,10,7)),((11,-8,1),(3.5,8,6))]):
 o=bpy.data.objects.new('Wired | luminous abyss channel %d'%i,old.data.copy());col.objects.link(o);o.location=p(*xyz);o.rotation_euler=cam.rotation_euler;o.scale=sc
 m=old.data.materials[0].copy();o.data.materials.clear();o.data.materials.append(m)
 for n in list(m.node_tree.nodes):
  if n.type=='PRINCIPLED_VOLUME':
   for sock,mulval in [('Emission Strength',4),('Density',1.8)]:
    inp=n.inputs[sock];src=inp.links[0].from_socket;mul=m.node_tree.nodes.new('ShaderNodeMath');mul.operation='MULTIPLY';mul.inputs[1].default_value=mulval;m.node_tree.links.new(src,mul.inputs[0]);m.node_tree.links.new(mul.outputs[0],inp)
# Facet lighting is dimmer and less saturated at the support faces.
for o in col.objects:
 if o.type=='LIGHT' and 'foundation face grazing' in o.name:o.data.energy=900
 if o.type=='LIGHT' and 'abyss light' in o.name:o.data.energy*=.6
# Asymmetrical leaning blunt crags, with fractured tops in place of cones.
for o in col.objects:
 if o.type!='MESH' or 'grounded broken stalagmite' not in o.name:continue
 zmin=min(v.co.z for v in o.data.vertices);zmax=max(v.co.z for v in o.data.vertices);cx=sum(v.co.x for v in o.data.vertices)/len(o.data.vertices);cy=sum(v.co.y for v in o.data.vertices)/len(o.data.vertices)
 for v in o.data.vertices:
  t=(v.co.z-zmin)/(zmax-zmin);v.co.x+=t*.35
  if t>.7:v.co.x=cx+(v.co.x-cx)*1.8;v.co.y=cy+(v.co.y-cy)*1.8;v.co.z+=random.uniform(-.23,.13)
 o.data.update()
# Dim framing facets at extreme sides, so they are rock rather than empty black wedges.
for side in [-1,1]:
 o=area('Wired | near frame rim',(side*12,0,14),(side*17,-3,7),900,7,(.28,.36,.48));o.data.volume_factor=0;o.data.specular_factor=0;o.light_linking.receiver_collection=bpy.data.collections['Wired inner wall light receivers']
s.render.filepath='/Users/danielku/mywebsite/secret-base/wired-review/iteration-11.png'
bpy.ops.wm.save_as_mainfile(filepath='/Users/danielku/mywebsite/secret-base/base.blend')
