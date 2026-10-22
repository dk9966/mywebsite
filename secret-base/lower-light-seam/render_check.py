import bpy,sys
p='/Users/danielku/mywebsite/secret-base/lower-light-seam/'
s=bpy.context.scene
s.cycles.device='CPU';s.cycles.samples=24;s.cycles.use_denoising=True
s.render.resolution_x=2000;s.render.resolution_y=1104;s.render.resolution_percentage=100
s.render.use_border=True;s.render.use_crop_to_border=True
s.render.border_min_x=.70;s.render.border_max_x=.985;s.render.border_min_y=.235;s.render.border_max_y=.64
s.render.image_settings.file_format='PNG'
variant=sys.argv[-1]
if variant=='soft':
 o=bpy.data.objects['RL | Lower right | soft overhead spot']
 for f in o.data.animation_data.drivers:
  if f.data_path=='shadow_soft_size': f.driver.expression='1.1*r'
 s.frame_set(s.frame_current)
if variant=='no-spot':
 bpy.data.objects['RL | Lower right | soft overhead spot'].hide_render=True
if variant=='no-wall':
 for o in s.objects:
  if o.type=='LIGHT' and o.name.startswith('Lower |') and 'wash' in o.name: o.hide_render=True
if variant=='no-side':
 bpy.data.objects['RL | Cave | soft side bounce +1'].hide_render=True
if variant=='moved-fill':
 from mathutils import Vector
 o=bpy.data.objects['RL | Cave | soft side bounce +1']
 mw=o.matrix_world.copy();mw.translation-= (mw.to_quaternion()@Vector((0,0,-1)))*4.0
 o.matrix_world=mw
 bpy.context.view_layer.update()
s.render.filepath=p+variant+'.png'
bpy.ops.render.render(write_still=True)
