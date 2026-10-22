import bpy,json
from pathlib import Path
OUT=Path('/Users/danielku/mywebsite/secret-base/reference-rock')
old=bpy.data.materials['Terrain | matte blue-gray facets.001']
rocks=[o for o in bpy.context.scene.objects if o.type=='MESH' and old in list(o.data.materials)]
m=bpy.data.materials.new('Terrain | rough hewn slate');m.use_nodes=True;m.diffuse_color=(.09,.115,.135,1)
n=m.node_tree.nodes;n.clear();l=m.node_tree.links

def node(kind,name,x,y):
 a=n.new(kind);a.name=name;a.label=name;a.location=(x,y);return a

def link(a,x,b,y):l.new(a.outputs[x],b.inputs[y])
tc=node('ShaderNodeTexCoord','Rock coordinates',-1000,0)
v=node('ShaderNodeVectorMath','Long irregular clefts',-800,0);v.operation='MULTIPLY';v.inputs[1].default_value=(1.1,1.1,.22);link(tc,'Object',v,0)
broad=node('ShaderNodeTexNoise','Broad broken rock relief',-600,100);broad.inputs['Scale'].default_value=1.7;broad.inputs['Detail'].default_value=3;broad.inputs['Roughness'].default_value=.65;link(v,'Vector',broad,'Vector')
r=node('ShaderNodeValToRGB','Quiet slate color variation',-340,300);r.color_ramp.elements[0].position=.12;r.color_ramp.elements[0].color=(.038,.05,.06,1);r.color_ramp.elements[1].position=.85;r.color_ramp.elements[1].color=(.13,.155,.175,1);link(broad,'Fac',r,'Fac')
b=node('ShaderNodeBump','Weathered broad relief',-60,0);b.inputs['Strength'].default_value=.42;b.inputs['Distance'].default_value=.21;link(broad,'Fac',b,'Height')
f=node('ShaderNodeTexNoise','Fine natural stone grain',-350,-230);f.inputs['Scale'].default_value=45;f.inputs['Detail'].default_value=2;f.inputs['Roughness'].default_value=.7;link(tc,'Object',f,'Vector')
b2=node('ShaderNodeBump','Subtle stone grain',150,-80);b2.inputs['Strength'].default_value=.19;b2.inputs['Distance'].default_value=.018;link(f,'Fac',b2,'Height');link(b,'Normal',b2,'Normal')
p=node('ShaderNodeBsdfPrincipled','Matte charcoal slate',400,220);p.inputs['Roughness'].default_value=.83;p.inputs['Specular IOR Level'].default_value=.25;link(r,'Color',p,'Base Color');link(b2,'Normal',p,'Normal')
o=node('ShaderNodeOutputMaterial','Surface',690,220);link(p,'BSDF',o,'Surface')
tex=bpy.data.textures.new('Rock | broad chipped relief',type='CLOUDS');tex.noise_scale=.75;tex.noise_depth=1;tex.noise_type='HARD_NOISE'
for ob in rocks:
 for slot in ob.material_slots:
  if slot.material==old:slot.material=m
 mod=ob.modifiers.new('Rock | subtle broken planes','DISPLACE');mod.texture=tex;mod.texture_coords='GLOBAL';mod.strength=.16;mod.mid_level=.5
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'textured-cavern.blend'),copy=True)
result={'rocks':[o.name for o in rocks],'material':m.name,'relief':'0.16-unit non-destructive displacement; original topology retained'}
(OUT/'checks.json').write_text(json.dumps(result,indent=2))
