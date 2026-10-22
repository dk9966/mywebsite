import bpy, math, json
import numpy as np
from pathlib import Path
from mathutils import Vector, Matrix
from mathutils.geometry import intersect_ray_tri
from bpy_extras.object_utils import world_to_camera_view
P=Path('/Users/danielku/mywebsite/secret-base/lower-reference-alignment')
S=bpy.context.scene;CAM=S.camera;lower=bpy.data.objects['Lower | plain octagon']
FRAME=Matrix.Translation((21.299999237,0,0))@Matrix.Rotation(-math.atan2(12,19),4,'Z');INV=FRAME.inverted();F=6.824491024;H=2.03
W=1697;IH=927;RH=W*S.render.resolution_y/S.render.resolution_x;PAD=(RH-IH)/2
vp=CAM.calc_matrix_camera(bpy.context.evaluated_depsgraph_get(),x=S.render.resolution_x,y=S.render.resolution_y)@CAM.matrix_world.inverted();ivp=vp.inverted()
def ray(uv):
 p=ivp@Vector((2*uv[0]/W-1,1-2*(uv[1]+PAD)/RH,-1,1));p=p.xyz/p.w
 return CAM.matrix_world.translation.copy(),(p-CAM.matrix_world.translation).normalized()
def at_z(uv,z):
 a,d=ray(uv);return a+d*((z-a.z)/d.z)
def uv(p):
 q=world_to_camera_view(S,CAM,p);return Vector((q.x*W,(1-q.y)*RH-PAD))
def col(name):
 c=bpy.data.collections.get(name)
 if not c:c=bpy.data.collections.new(name);S.collection.children.link(c)
 return c
ARCH=col('160 | Reference aligned workshop architecture')
DETAIL=col('161 | Reference aligned service pad and brackets')
for c in (ARCH,DETAIL):
 for o in list(c.objects):bpy.data.objects.remove(o,do_unlink=True)
bpy.data.collections['156 | Lower workshop walls and canopy'].hide_viewport=True
bpy.data.collections['156 | Lower workshop walls and canopy'].hide_render=True
steel=bpy.data.materials['Metal | dark structural steel'];black=bpy.data.materials['Metal | unlit grate recess'];alloy=bpy.data.materials['Metal | outer walkway alloy'];edge=bpy.data.materials['Metal | machined edge highlights'];white=bpy.data.materials['Lower | cool white practical diffuser'];paint=bpy.data.materials['Lower | muted brass floor registration']
def mat(name,color,metal=.65,rough=.42):
 m=bpy.data.materials.get(name) or bpy.data.materials.new(name);m.use_nodes=True;m.diffuse_color=(*color,1)
 p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=rough
 return m
wall=mat('Lower | aligned blue graphite panels',(.085,.115,.135),.55,.46)
turn=mat('Lower | radial satin turntable',(.10,.14,.17),.72,.37)
trim=mat('Lower | aligned architectural trim',(.055,.082,.10),.65,.40)
roofmat=bpy.data.materials['Lower | matte roof cassette']
def mesh(name,verts,faces,material,c=ARCH,bevel=0):
 me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.materials.append(material);me.update()
 o=bpy.data.objects.new(name,me);c.objects.link(o)
 o.parent=lower;o.matrix_world=Matrix.Identity(4)
 if bevel:
  m=o.modifiers.new('Small fabricated edge','BEVEL');m.width=bevel;m.segments=2
  o.modifiers.new('Weighted surface normals','WEIGHTED_NORMAL')
 return o

def beam(name,a,b,width,depth,material=steel,c=ARCH,bevel=.003):
 a,b=Vector(a),Vector(b);axis=(b-a).normalized();help=Vector((0,0,1)) if abs(axis.z)<.9 else Vector((0,1,0));u=axis.cross(help).normalized()*width/2;v=axis.cross(u).normalized()*depth/2
 vs=[tuple(p+su*u+sv*v) for p in(a,b) for su,sv in [(-1,-1),(1,-1),(1,1),(-1,1)]]
 return mesh(name,vs,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],material,c,bevel)
def plate(name,points,normal,depth,material,c=ARCH,bevel=.004):
 vs=[tuple(p-normal*d) for d in (0,depth) for p in points];n=len(points)
 fs=[tuple(range(n)),tuple(reversed(range(n,2*n)))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
 return mesh(name,vs,fs,material,c,bevel)
B=[(1244,515),(1340,516),(1458,530),(1590,565),(1656,588)]
T=[(1250,394),(1357,398),(1486,429),(1615,469),(1670,500)]
base=[at_z(p,F) for p in B];top=[at_z(p,F+H) for p in T]
lights=[((1280,442),(1323,442)),((1380,444),(1424,444)),((1523,455),(1568,466)),((1626,507),(1658,518))]
patches=[]
for i in range(4):
 a,b=base[i:i+2];d,c=top[i:i+2];points=[a,b,c,d]
 normal=(b-a).cross(d-a).normalized()
 if normal.dot(CAM.location-(a+b+c+d)/4)<0:normal=-normal
 patches.append((points,normal))
 plate('Lower | fitted recessed bay %02d'%i,points,normal,.11,wall)
 def surf(px):
  origin,direction=ray(px)
  hit=intersect_ray_tri(a,b,c,direction,origin,False)
  # Bilinear quad is represented by Blender's two triangles.
  valid=intersect_ray_tri(a,b,c,direction,origin,True)
  if valid is not None:return valid
  valid=intersect_ray_tri(a,c,d,direction,origin,True)
  return valid if valid is not None else hit
 # Three subtle horizontal seams and one central vertical seam.
 for h in [.22,.49,.72]:
  p=a.lerp(d,h)+normal*.008;q=b.lerp(c,h)+normal*.008
  beam('Lower | fitted horizontal panel reveal',p,q,.010,.010,black,ARCH,0)
 p=a.lerp(b,.5)+normal*.008;q=d.lerp(c,.5)+normal*.008
 beam('Lower | fitted vertical panel reveal',p,q,.009,.009,black,ARCH,0)
 for p,q in [(a,b),(d,c)]:beam('Lower | recessed panel border',p+normal*.028,q+normal*.028,.055,.055,trim)
 aa,bb=lights[i];p=surf(aa)+normal*.028;q=surf(bb)+normal*.028
 beam('Lower | reference strip light housing',p,q,.074,.063,steel)
 beam('Lower | reference white strip diffuser',p+normal*.037,q+normal*.037,.023,.019,white)
 # Real lights follow the fitted emitters and illuminate the wall below.
 data=bpy.data.lights.new('Lower | fitted wall wash','AREA');data.energy=28;data.color=(.65,.82,1);data.shape='RECTANGLE';data.size=(q-p).length;data.size_y=.14
 o=bpy.data.objects.new('Lower | fitted wall wash',data);ARCH.objects.link(o);o.location=(p+q)/2+normal*.17
 target=(a+b)/2+normal*.15;o.rotation_euler=(target-o.location).to_track_quat('-Z','Y').to_euler();mw=o.matrix_world.copy();o.parent=lower;o.matrix_world=mw
# Broad inset metal uprights with splayed foot braces.
for i,(p,q) in enumerate(zip(base,top)):
 n=patches[min(i,3)][1]
 beam('Lower | fitted structural pier',p+n*.045,q+n*.045,.14,.19,trim,ARCH,.007)
 beam('Lower | fitted pier edge',p+n*.15,q+n*.15,.023,.018,alloy)
 beam('Lower | fitted splayed pier foot',p+n*.20+Vector((0,0,.025)),p+n*.06+Vector((0,0,.34)),.22,.16,trim,ARCH,.006)
 beam('Lower | fitted foot inset',p+n*.29+Vector((0,0,.04)),p+n*.14+Vector((0,0,.29)),.065,.023,black,ARCH,.002)
# Roof lintel follows the same wall outline. Its depth stays behind the front lip.
for i in range(4):
 a,b=top[i:i+2];n=patches[i][1]
 beam('Lower | fitted roof fascia',a+n*.12,b+n*.12,.18,.16,steel,ARCH,.006)
 points=[a+n*.12,b+n*.12,b-n*.4,a-n*.4]
 plate('Lower | fitted roof cassette',points,Vector((0,0,1)),.09,roofmat)
 beam('Lower | fitted roof edge',a+n*.19+Vector((0,0,.07)),b+n*.19+Vector((0,0,.07)),.032,.022,alloy)
# Wide faceted hood traced from the reference, at the architectural roof level.
hoodpx=[(1375,392),(1394,378),(1512,384),(1575,404),(1560,421),(1503,431),(1435,426),(1374,410)]
hood=[at_z(p,F+H-.02) for p in hoodpx]
plate('Lower | reference octagonal overhead hood',hood,Vector((0,0,1)),.20,roofmat)
for i in range(len(hood)):
 beam('Lower | overhead hood armor edge',hood[i]-Vector((0,0,.15)),hood[(i+1)%len(hood)]-Vector((0,0,.15)),.055,.072,steel)
for a,b in [((1408,415),(1430,420)),((1480,425),(1508,425))]:
 p=at_z(a,F+H-.23);q=at_z(b,F+H-.23)
 beam('Lower | overhead inset diffuser',p,q,.025,.016,white)
# Replace old service track and undersized multiple V trusses with the reference shapes.
for o in bpy.data.collections['157 | Lower deck and cliff supports'].objects:
 if o.type=='MESH' and any(t in o.name for t in ['circular','registration','center service','radial plate joint','diagonal brace','vertical load leg','foundation','front girder gusset','exposed front V','load transfer','truss anchor']):
  o.hide_render=True;o.hide_set(True)
e=json.loads((P/'gold-ellipse.json').read_text());center=np.array(e['center']);basis=np.array(e['basis'])
def ellipse(r,t,z=F+.014):
 pix=center+basis@np.array([r*math.cos(t),r*math.sin(t)])
 return at_z(pix,z)
def ring(name,ri,ro,material,z=F+.014):
 n=192;vs=[tuple(ellipse(r,i*math.tau/n,z)) for r in (ri,ro) for i in range(n)]
 fs=[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
 return mesh(name,vs,fs,material,DETAIL)
ring('Lower | fitted turntable surface',0,1,turn,F+.010)
ring('Lower | fitted brass registration band',.995,1.023,paint,F+.022)
ring('Lower | fitted inner metal rim',1.027,1.058,alloy,F+.019)
ring('Lower | fitted outer recessed channel',1.058,1.083,black,F+.016)
ring('Lower | fitted broad perimeter apron',1.086,1.225,turn,F+.012)
ring('Lower | fitted outer circle groove',1.225,1.239,black,F+.016)
ring('Lower | fitted outer circle glint',1.239,1.250,edge,F+.018)
ring('Lower | fitted perimeter groove',1.287,1.300,black,F+.012)
ring('Lower | fitted center disc rim',.452,.469,alloy,F+.024)
ring('Lower | fitted center disc reveal',.469,.481,black,F+.023)
for i in range(12):
 t=i*math.tau/12+.11
 beam('Lower | fitted radial turntable seam',ellipse(.485,t,F+.024),ellipse(.99,t,F+.024),.006,.004,black,DETAIL,0)
for i in range(16):
 t=i*math.tau/16
 p=ellipse(1.011,t,F+.026)
 beam('Lower | registration band fastener',p-Vector((.010,0,0)),p+Vector((.010,0,0)),.018,.005,black,DETAIL,0)
# Two larger diagonal foundations matching the silhouette, with one central upright.
# Points under the slab intersect a camera-parallel plane through its near edge.
front=[at_z(p,F-.05) for p in [(1218,668),(1335,699),(1593,699)]]
plane_point=front[1];normal=CAM.matrix_world.to_3x3()@Vector((0,0,1))
def under(p):
 a,d=ray(p);return a+d*((plane_point-a).dot(normal)/d.dot(normal))
for a,b in [((1240,706),(1334,832)),((1334,723),(1334,832)),((1334,832),(1438,725)),((1503,725),(1585,814)),((1585,814),(1602,724))]:
 beam('Lower | reference large diagonal bracket',under(a),under(b),.12,.15,steel,DETAIL,.004)
for p in [(1334,832),(1585,814)]:
 a=under(p);beam('Lower | reference bracket foot',a-Vector((0,0,.065)),a+Vector((0,0,.065)),.23,.23,trim,DETAIL,.005)
# Main front fascia is visibly deep in the reference.
for a,b in [((1218,670),(1335,699)),((1335,699),(1593,699)),((1593,699),(1645,664))]:
 p=at_z(a,F);q=at_z(b,F)
 beam('Lower | fitted deep front fascia',p-Vector((0,0,.16)),q-Vector((0,0,.16)),.12,.32,steel,DETAIL,.003)
# Additional floor joints toward rear wall, as in the unfurnished shell.
for a,b in [((1200,563),(1262,540)),((1262,540),(1385,540)),((1385,540),(1510,548)),((1510,548),(1600,590)),((1600,590),(1644,605)),((1229,644),(1255,622)),((1553,669),(1540,653))]:
 beam('Lower | fitted outer deck seam',at_z(a,F+.013),at_z(b,F+.013),.008,.003,black,DETAIL,0)
# Dark metallic materials with visible roughness variation, no external assets.
for material in [turn,wall]:
 nt=material.node_tree;p=nt.nodes.get('Principled BSDF')
 noise=nt.nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=24;noise.inputs['Detail'].default_value=2
 ramp=nt.nodes.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].color=(.30,.30,.30,1);ramp.color_ramp.elements[1].color=(.53,.53,.53,1)
 nt.links.new(noise.outputs['Fac'],ramp.inputs[0]);nt.links.new(ramp.outputs['Color'],p.inputs['Roughness'])
bpy.context.view_layer.update();CAM.data.background_images[0].alpha=.5
result={'new_architecture_objects':len(ARCH.objects),'new_detail_objects':len(DETAIL.objects),'gold_center':e['center']}
