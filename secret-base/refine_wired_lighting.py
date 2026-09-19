exec(compile(open('/Users/danielku/mywebsite/secret-base/refine_wired_depth.py').read().split('# Remove unsupported')[0],'helpers','exec'))
# A dedicated neutral stone light leaves the metal station's established lighting intact.
recv=bpy.data.collections.get('Wired Foundation light receivers') or bpy.data.collections.new('Wired Foundation light receivers')
if recv.name not in s.collection.children:s.collection.children.link(recv)
for o in bpy.data.objects:
 if o.type=='MESH' and any(k in o.name for k in ['bedrock foundation island','buttress','footing cap','foreground rim','chasm rubble ridge','ridge talus','visible abyss pinnacle','grounded fractured rubble']):
  if o.name not in recv.objects:recv.objects.link(o)
for o in col.objects:
 if o.type=='LIGHT' and 'foundation face grazing' in o.name:
  o.data.energy=2800;o.data.color=(.52,.61,.72);o.light_linking.receiver_collection=recv
# A medium-scale fracture network bends flat faces into irregular rock.
for o in bpy.data.objects:
 if o.type!='MESH' or 'bedrock foundation island' not in o.name:continue
 for v in o.data.vertices:
  if v.co.z<-.6:
   t=min(1,(-v.co.z-.6)/1.3);nv=noise.noise_vector(v.co*1.15);v.co+=nv*.37*t
 o.data.update()
# Break the overly regular vertical blade rhythm in the overhead frame.
for i,o in enumerate([o for o in col.objects if 'fractured vertical rock blade' in o.name]):
 if i%3==0:o.hide_render=True;o.hide_set(True)
# Gentle facet fill on the inward walls, neutral and very subdued.
wallrecv=bpy.data.collections.get('Wired inner wall light receivers') or bpy.data.collections.new('Wired inner wall light receivers')
if wallrecv.name not in s.collection.children:s.collection.children.link(wallrecv)
for o in col.objects:
 if o.type=='MESH' and any(k in o.name for k in ['massive wall','foreground cliff','service ledge','loose ledge','vertical rock blade']):
  if o.name not in wallrecv.objects:wallrecv.objects.link(o)
o=area('Wired | slate wall facet fill',(0,1,10),(0,0,-3),900,11,(.45,.54,.65));o.data.volume_factor=0;o.data.specular_factor=.1;o.light_linking.receiver_collection=wallrecv
s.render.filepath='/Users/danielku/mywebsite/secret-base/wired-review/iteration-7.png'
bpy.ops.wm.save_as_mainfile(filepath='/Users/danielku/mywebsite/secret-base/base.blend')
