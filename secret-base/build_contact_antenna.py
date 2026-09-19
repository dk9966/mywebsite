import bpy, math
from mathutils import Vector
if bpy.context.mode != 'OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
col=bpy.data.collections.new('contact_antenna'); bpy.context.scene.collection.children.link(col)
root=bpy.data.objects.new('contactAntenna_root',None);col.objects.link(root)
def mat(name,color,metal,rough):
 m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
 p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=rough
 return m
ivory=mat('antenna_satin_ivory_alloy',(.65,.62,.53),.58,.29)
edge=mat('antenna_brushed_nickel',(.43,.45,.43),.8,.24)
dark=mat('antenna_recess_graphite',(.045,.051,.048),.48,.4)
ceramic=mat('antenna_sensor_ceramic',(.78,.77,.68),.25,.28)
def finish(o,name,material,bevel=0):
 o.name='contactAntenna_'+name
 for c in list(o.users_collection):c.objects.unlink(o)
 col.objects.link(o);o.parent=root;o.data.materials.append(material)
 if bevel:
  mod=o.modifiers.new('Machined edge highlights','BEVEL');mod.width=bevel;mod.segments=2
 if o.type=='MESH':
  for p in o.data.polygons:p.use_smooth=len(p.vertices)==4
 return o

def cyl(name,r,z0,z1,material=ivory,x=0,y=0,r2=None):
 bpy.ops.mesh.primitive_cone_add(vertices=48,radius1=r,radius2=r if r2 is None else r2,depth=z1-z0,location=(x,y,(z0+z1)/2))
 return finish(bpy.context.object,name,material,.008)
def box(name,loc,dims,material=ivory,bevel=.012):
 bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.dimensions=dims
 bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 return finish(o,name,material,bevel)
def bar(name,a,b,r,material=edge):
 a,b=Vector(a),Vector(b);o=cyl(name,r,0,(b-a).length,material);o.location=(a+b)/2;o.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler();return o
def ring(name,loc,r,t,material=edge,rot=None):
 bpy.ops.mesh.primitive_torus_add(major_radius=r,minor_radius=t,major_segments=48,minor_segments=10,location=loc)
 o=finish(bpy.context.object,name,material)
 if rot:o.rotation_euler=rot
 return o
# Flared foot, radial reinforcing gussets and bolted flange.
cyl('foot_flange',.92,0,.065,edge)
cyl('flared_pedestal',.86,.065,.36,ivory,r2=.49)
cyl('base_collar',.51,.34,.49)
for i in range(8):
 a=i*math.tau/8
 o=box('radial_foot_rib_%02d'%i,(.63*math.cos(a),.63*math.sin(a),.2),(.52,.055,.22),ivory)
 o.rotation_euler=(0,-.38,a)
 cyl('anchor_bolt_%02d'%i,.035,.065,.095,edge,x=.79*math.cos(a),y=.79*math.sin(a))
# Main pump and condenser, twin louvred front panels.
cyl('pump_body',.48,.49,1.32)
for z in [.52,1.28,1.48,2.65,2.86]:cyl('body_flange',.51,z,z+.055,edge)
cyl('central_spine',.35,1.3,3.07,edge)
box('water_pump_access',(0,-.465,.91),(.38,.09,.49))
box('pump_recess',(0,-.516,.92),(.23,.025,.29),dark)
box('condenser_cabinet',(0,0,2.07),(1.14,.88,1.16))
for x in [-.27,.27]:
 box('vent_frame',(x,-.47,2.07),(.46,.09,1.02),edge)
 box('vent_shadow',(x,-.523,2.07),(.365,.025,.9),dark)
 for j in range(24):
  o=box('condenser_louvre',(x,-.547,1.65+j*.036),(.35,.04,.015),ivory,.003);o.rotation_euler.x=.22
for z in [1.84,2.31]:
 bar('patch_port',(-.58,0,z),(-.69,0,z),.135)
 ring('patch_port_lip',(-.70,0,z),.115,.022,ivory,(0,math.pi/2,0))
 bar('patch_port_dark',(-.695,0,z),(-.699,0,z),.089,dark)
# Wide machinery barrel with stacked disc collars and cooling ribs.
cyl('lower_neck',.39,2.66,2.94)
cyl('main_barrel',.55,2.94,3.57)
for z in [2.94,3.55,3.77,4.02,4.2]:cyl('machined_disc',.59 if z<3.7 else .60,z,z+.095)
cyl('recessed_belt',.47,3.64,4.21,dark)
for i in range(12):
 a=i*math.tau/12;o=box('belt_segment',(.50*math.cos(a),.50*math.sin(a),3.88),(.15,.12,.19),ivory);o.rotation_euler.z=a
cyl('cooling_core',.31,4.24,4.67,dark)
for i in range(8):cyl('cooling_fin',.365,4.26+i*.048,4.282+i*.048,edge)
# Three long segmented chiller rods, attached by two levels of brackets.
for i,a in enumerate([math.radians(30),math.radians(150),math.radians(270)]):
 x,y=.98*math.cos(a),.98*math.sin(a)
 cyl('chiller_rod_%d'%i,.079,.61,4.87,ivory,x,y)
 for z0,z1 in [(.67,2.08),(2.13,2.77),(2.83,3.64),(3.91,4.68)]:cyl('chiller_sleeve',.101,z0,z1,ivory,x,y)
 for z in [.67,2.09,2.78,3.64,3.87,4.68]:cyl('chiller_cuff',.127,z,z+.047,edge,x,y)
 cyl('chiller_tip',.096,4.78,4.89,ceramic,x,y,r2=.045)
 for z in [.67,3.81]:bar('radial_support',(0,0,z),(x,y,z),.065,ivory)
# Sensor stack with dark separation seams, instrument ports and crown.
for name,r,z0,z1 in [('intake',.27,4.65,5.11),('pressure',.25,5.17,5.62),('density',.24,5.72,6.06),('upper',.23,6.4,6.76)]:
 cyl(name,r,z0,z1);cyl(name+'_gasket',r*.91,z1,z1+.065,dark)
cyl('ribbed_collar',.32,6.12,6.36,edge)
for i in range(20):
 a=i*math.tau/20;bar('crown_flute',(.30*math.cos(a),.30*math.sin(a),6.16),(.30*math.cos(a),.30*math.sin(a),6.33),.029,ivory)
cyl('telemetry_cone',.235,6.76,7.17,ivory,r2=.15)
for z,r in [(5.04,.29),(5.65,.26),(6.06,.27),(6.4,.25),(6.75,.24)]:cyl('sensor_rim',r,z,z+.035,edge)
for z,rad in [(3.32,.12),(4.92,.145),(5.42,.115)]:
 bar('sensor_nozzle',(0,-.19,z),(0,-.37,z),rad,ivory)
 ring('sensor_port_lip',(0,-.39,z),rad*.87,.021,edge,(math.pi/2,0,0))
 bar('sensor_port_recess',(0,-.373,z),(0,-.382,z),rad*.66,dark)
for z in [5.82,6.0,7.0]:bar('small_side_probe',(.17,0,z),(.33,0,z),.035,edge)
# Long slender aerial and paired ribbed humidity paddles.
cyl('aerial_mast',.042,7.16,9.28,edge,r2=.032)
cyl('aerial_tip',.022,9.28,9.85,edge)
bar('sensor_crossbar',(-.43,0,9.84),(.43,0,9.84),.025,edge)
for s in [-1,1]:
 o=box('humidity_paddle',(s*.34,0,9.855),(.31,.035,.29),ivory,.009);o.rotation_euler.y=s*-.13
 for j in range(4):box('humidity_paddle_rib',(s*(.21+j*.078),-.026,9.855),(.014,.024,.265),edge,.003)
# Normalize true assembled bounds, including the foot ribs, to exactly 1.4x machinery height.
bpy.context.view_layer.update()
pts=[o.matrix_world@Vector(v) for o in col.objects if o.type=='MESH' for v in o.bound_box]
zlo=min(p.z for p in pts);zhi=max(p.z for p in pts)
reference=bpy.data.objects['deck_desk_b'];pts_ref=[reference.matrix_world@Vector(v) for v in reference.bound_box]
height=max(p.z for p in pts_ref)-min(p.z for p in pts_ref)
s=height*1.4/(zhi-zlo)
floor=bpy.data.objects['deck_floor_contact']
bpy.context.view_layer.update()
fp=[floor.matrix_world@Vector(v) for v in floor.bound_box]
cx=(min(p.x for p in fp)+max(p.x for p in fp))/2
cy=(min(p.y for p in fp)+max(p.y for p in fp))/2
root.scale=(s,s,s);root.location=(cx-.52,cy+.35,max(p.z for p in fp)-zlo*s);root.rotation_euler.z=math.radians(-12)
bpy.context.view_layer.update()
mw=root.matrix_world.copy();root.parent=bpy.data.objects['island_pillar_contact'];root.matrix_world=mw
root['height_ratio']=1.4;root['reference_object']='deck_desk_b';root['reference_height']=height;root['antenna_height']=height*1.4
bpy.context.view_layer.update()
bpy.ops.object.select_all(action='DESELECT');root.select_set(True);bpy.context.view_layer.objects.active=root
bpy.ops.wm.save_as_mainfile(filepath='/Users/danielku/mywebsite/secret-base/base.blend')
result={'height':height*1.4,'parts':len(col.objects)-1,'location':list(root.location)}
