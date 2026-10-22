import bpy, json
from pathlib import Path
OUT=Path('/Users/danielku/mywebsite/secret-base/reference-rock')
old=bpy.data.materials['Terrain | matte blue-gray facets.001']
rocks=[o for o in bpy.context.scene.objects if o.type=='MESH' and old in list(o.data.materials)]
mat=bpy.data.materials.new('Terrain | fractured charcoal slate')
mat.use_nodes=True
mat.diffuse_color=(.065,.085,.10,1)
ns=mat.node_tree.nodes; ns.clear(); links=mat.node_tree.links

def node(kind,name,x,y):
 n=ns.new(kind);n.label=name;n.name=name;n.location=(x,y);return n

def link(a,out,b,inp):links.new(a.outputs[out],b.inputs[inp])
def ramp(name,x,y,stops):
 n=node('ShaderNodeValToRGB',name,x,y)
 r=n.color_ramp
 for e in list(r.elements)[2:]:r.elements.remove(e)
 r.elements[0].position=stops[0][0];r.elements[0].color=stops[0][1]
 r.elements[1].position=stops[-1][0];r.elements[1].color=stops[-1][1]
 for p,c in stops[1:-1]:r.elements.new(p).color=c
 return n
tex=node('ShaderNodeTexCoord','Seamless local rock coordinates',-1100,0)
stretch=node('ShaderNodeVectorMath','Vertical folded slate',-900,0);stretch.operation='MULTIPLY';stretch.inputs[1].default_value=(1.35,1.35,.38);link(tex,'Object',stretch,0)
noise=node('ShaderNodeTexNoise','Broad mineral variation',-700,360);noise.inputs['Scale'].default_value=1.1;noise.inputs['Detail'].default_value=4;noise.inputs['Roughness'].default_value=.72;link(stretch,'Vector',noise,'Vector')
color=ramp('Charcoal and blue slate',-430,450,[(.18,(.018,.025,.031,1)),(.48,(.060,.078,.090,1)),(.78,(.14,.165,.18,1))]);link(noise,'Fac',color,'Fac')
vor=node('ShaderNodeTexVoronoi','Angular geological joints',-700,50);vor.feature='DISTANCE_TO_EDGE';vor.inputs['Scale'].default_value=2.3;link(stretch,'Vector',vor,'Vector')
joints=ramp('Recessed narrow fractures',-440,100,[(.0,(.08,.08,.08,1)),(.035,(.28,.28,.28,1)),(.095,(.85,.85,.85,1)),(.18,(1,1,1,1))]);link(vor,'Distance',joints,'Fac')
mix=node('ShaderNodeMixRGB','Dark fissures in slate',-140,450);mix.blend_type='MULTIPLY';mix.inputs[0].default_value=.75;link(color,'Color',mix,1);link(joints,'Color',mix,2)
wave=node('ShaderNodeTexWave','Broken sediment laminae',-700,-250);wave.wave_type='BANDS';wave.bands_direction='Z';wave.inputs['Scale'].default_value=3.2;wave.inputs['Distortion'].default_value=8;wave.inputs['Detail'].default_value=4;wave.inputs['Detail Scale'].default_value=1.4;link(tex,'Object',wave,'Vector')
fine=node('ShaderNodeTexNoise','Fine chipped grain',-440,-470);fine.inputs['Scale'].default_value=32;fine.inputs['Detail'].default_value=2.5;fine.inputs['Roughness'].default_value=.7;link(tex,'Object',fine,'Vector')
b1=node('ShaderNodeBump','Fracture relief',-120,50);b1.inputs['Strength'].default_value=.65;b1.inputs['Distance'].default_value=.14;link(joints,'Color',b1,'Height')
b2=node('ShaderNodeBump','Layered stone relief',100,-100);b2.inputs['Strength'].default_value=.32;b2.inputs['Distance'].default_value=.065;link(wave,'Fac',b2,'Height');link(b1,'Normal',b2,'Normal')
b3=node('ShaderNodeBump','Stone grain relief',330,-140);b3.inputs['Strength'].default_value=.28;b3.inputs['Distance'].default_value=.025;link(fine,'Fac',b3,'Height');link(b2,'Normal',b3,'Normal')
rough=node('ShaderNodeMapRange','Dry slate roughness',50,-400);rough.inputs['From Min'].default_value=0;rough.inputs['From Max'].default_value=1;rough.inputs['To Min'].default_value=.63;rough.inputs['To Max'].default_value=.9;link(noise,'Fac',rough,'Value')
bs=node('ShaderNodeBsdfPrincipled','Natural slate',570,330);link(mix,'Color',bs,'Base Color');link(b3,'Normal',bs,'Normal');link(rough,'Result',bs,'Roughness');bs.inputs['Specular IOR Level'].default_value=.3
output=node('ShaderNodeOutputMaterial','Rock surface',870,330);link(bs,'BSDF',output,'Surface')
for ob in rocks:
 ob['pre_texture_material']=old.name
 for slot in ob.material_slots:
  if slot.material==old:slot.material=mat
old.use_fake_user=True
report={'objects':[o.name for o in rocks],'vertices':sum(len(o.data.vertices) for o in rocks),'faces':sum(len(o.data.polygons) for o in rocks),'geometry_changed':False,'material':mat.name}
(OUT/'checks.json').write_text(json.dumps(report,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'textured-cavern.blend'),copy=True)
result=report
