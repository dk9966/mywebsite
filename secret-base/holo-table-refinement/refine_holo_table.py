"""Refine the selected cave holotable; run in the live, backed-up Blender scene."""
import bpy
import bmesh
import math
import json
from pathlib import Path
from mathutils import Vector, Matrix

OUT = Path('/Users/danielku/mywebsite/secret-base/holo-table-refinement')
COL = bpy.data.collections['175 | Lower bay holo table']
CENTER = bpy.data.objects['Holo table | floor plinth'].matrix_world.translation.copy()
FACTOR = 1.5
PREFIX = 'Holo table | '
assert not COL.get('clone_wars_refinement'), 'Refinement already applied; restore the backup to regenerate.'
assert bpy.context.mode == 'OBJECT'

# Fingerprint everything outside the authorized assembly before making edits.
def signature(o):
    return (o.data.as_pointer() if o.data else None,
            tuple(v for row in o.matrix_world for v in row),
            tuple(m.name if m else None for m in o.data.materials) if o.type == 'MESH' else (),
            o.hide_render, o.hide_viewport)

protected = {o.name: signature(o) for o in bpy.context.scene.objects if o not in set(COL.objects)}
source_parts = list(COL.objects)
source_radius = max(v.co.xy.length for v in bpy.data.objects[PREFIX+'top rim'].data.vertices)

def material(name, color, metallic=.5, roughness=.38, emission=0):
    m = bpy.data.materials.new('holoTable_CW_' + name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    p = m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value = (*color, 1)
    p.inputs['Metallic'].default_value = metallic
    p.inputs['Roughness'].default_value = roughness
    p.inputs['Emission Color'].default_value = (*color, 1)
    p.inputs['Emission Strength'].default_value = emission
    return m

alloy = material('satin armored alloy', (.050, .062, .081), .72, .34)
alloy_alt = material('alternate armor', (.042, .051, .068), .7, .38)
edge = material('machined edge', (.092, .114, .145), .8, .29)
black = material('recessed graphite', (.008, .012, .019), .35, .48)
key_shell = material('key surrounds', (.020, .029, .041), .68, .32)
ice = material('ivory blue key lens', (.55, .78, .87), .15, .3, .85)
blue = material('cyan status key', (.025, .37, .68), .12, .3, 1.05)
red = material('red status key', (.58, .020, .014), .12, .33, .65)
screen = material('small blue display', (.012, .085, .145), .24, .27, .35)
white = material('soft white side lamp', (.60, .76, .87), .08, .26, 1.6)

def mesh_object(name, verts, faces, mat, existing=None, bevel=0, smooth=False):
    mesh = bpy.data.meshes.new(PREFIX + name + ' mesh')
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    bm = bmesh.new(); bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(mesh); bm.free()
    obj = existing or bpy.data.objects.new(PREFIX + name, mesh)
    if existing:
        obj.data = mesh
        obj.modifiers.clear()
    else:
        COL.objects.link(obj)
    obj.matrix_world = Matrix.Translation(CENTER)
    mesh.materials.append(mat)
    for p in mesh.polygons:
        p.use_smooth = smooth
    if bevel:
        mod = obj.modifiers.new('Rounded machined edges', 'BEVEL')
        mod.width = bevel; mod.segments = 3
        mod.harden_normals = True
        normal = obj.modifiers.new('Weighted surface normals', 'WEIGHTED_NORMAL')
        normal.keep_sharp = True; normal.weight = 40
    return obj

def lathe(name, profile, mat, start=0, end=math.tau, steps=128, existing=None, bevel=0):
    full = abs(end-start-math.tau) < 1e-6
    n = steps if full else steps+1
    verts = [(r*math.cos(start+(end-start)*i/steps),
              r*math.sin(start+(end-start)*i/steps),z)
             for i in range(n) for r,z in profile]
    k = len(profile); faces=[]
    for i in range(steps):
        j=(i+1)%n
        for p in range(k):
            q=(p+1)%k
            faces.append((i*k+p,j*k+p,j*k+q,i*k+q))
    if not full:
        faces.extend([tuple(reversed(range(k))),tuple((n-1)*k+p for p in range(k))])
    obj=mesh_object(name,verts,faces,mat,existing,bevel,True)
    if not full:
        for p in list(obj.data.polygons)[-2:]:p.use_smooth=False
    return obj

def annulus(name, ri, ro, z0, z1, mat, start=0, end=math.tau, steps=128, existing=None):
    return lathe(name, [(ri,z0),(ro,z0),(ro,z1),(ri,z1)],mat,start,end,steps,existing)

def box(name, center, size, mat, basis=None, bevel=.002):
    basis=basis or Matrix.Identity(3)
    verts=[Vector(center)+basis@Vector((x*size[0]/2,y*size[1]/2,z*size[2]/2))
           for x,y,z in [(-1,-1,-1),(-1,-1,1),(-1,1,-1),(-1,1,1),
                         (1,-1,-1),(1,-1,1),(1,1,-1),(1,1,1)]]
    faces=[(0,4,6,2),(1,3,7,5),(0,1,5,4),(2,6,7,3),(0,2,3,1),(4,5,7,6)]
    return mesh_object(name,verts,faces,mat,bevel=bevel)

# Horizontal scaling preserves the scene position and pedestal/table height.
for obj in source_parts:
    if obj.type=='MESH':
        obj.data=obj.data.copy()
        world=obj.matrix_world.copy(); inv=world.inverted()
        for vert in obj.data.vertices:
            p=world@vert.co
            p.x=CENTER.x+(p.x-CENTER.x)*FACTOR
            p.y=CENTER.y+(p.y-CENTER.y)*FACTOR
            vert.co=inv@p
        obj.data.update()
    elif obj.type=='LIGHT' and hasattr(obj.data,'size'):
        obj.data=obj.data.copy();obj.data.size*=FACTOR

# Rounded upper shoulder, straight fascia, and rounded/tapered lower shoulder.
# The maximum outer radius is exactly the old top-rim radius times 1.5.
R=source_radius*FACTOR
profile=[(.949,.328),(.950,.339),(.955,.347),(.965,.351),(.979,.350),
         (1.000,.344),(1.165,.302),(1.192,.295),(1.213,.286),
         (1.228,.274),(R,.259),(R,.219),(1.234,.207),
         (1.224,.197),(1.208,.190),(1.184,.184),(1.056,.160),
         (1.002,.154),(.972,.154),(.955,.159),(.949,.170)]
lathe('top rim',[(r-.004,z-.002) for r,z in profile],black,
      existing=bpy.data.objects[PREFIX+'top rim'])
for i in range(16):
    a=i*math.tau/16
    lathe('armored band panel %02d'%i,profile,alloy if i%2 else alloy_alt,
          a+.006,a+math.tau/16-.006,12,
          existing=bpy.data.objects[PREFIX+'armored band panel %02d'%i],bevel=.0015)

lathe('inner lip',[(.938,.290),(.938,.338),(.941,.350),(.948,.357),
                  (.958,.358),(.969,.352),(.974,.342),(.974,.310)],edge,
      existing=bpy.data.objects[PREFIX+'inner lip'])
lathe('underside plate',[(0,.168),(1.02,.168),(1.055,.173),(1.09,.183),
                         (1.09,.190),(0,.190)],alloy,
      existing=bpy.data.objects[PREFIX+'underside plate'])
annulus('upper fascia trim',R-.009,R+.001,.268,.274,edge)
annulus('lower fascia trim',R-.017,R-.005,.198,.203,edge)

# Preserve the original softly mottled glass material and recessed optical field.
glass=bpy.data.objects[PREFIX+'misty holo glass']
glass.data.materials[0]=glass.data.materials[0].copy()
glass.data.materials[0].name='holoTable_CW_original_misty_glass'

# Retain the replaced controls in an excluded collection for direct recovery.
archive=bpy.data.collections.new('175a | Original holo controls - hidden backup')
bpy.context.scene.collection.children.link(archive)
replaced=[o for o in source_parts if any(t in o.name for t in ['rim control panel','panel key','rim light arc','band strip light'])]
for obj in replaced:
    COL.objects.unlink(obj);archive.objects.link(obj)
    obj.hide_render=True;obj.hide_set(True)
archive.hide_render=True;archive.hide_viewport=True

# Cyan projector strips sit on the inside of the raised bezel, as in the references.
for i in range(8):
    a=i*math.tau/8
    lathe('inward projector light %02d'%i,
          [(.9345,.325),(.937,.325),(.937,.338),(.9345,.338)],
          blue,a+.14,a+.59,24)

slope=(.302-.344)/(1.165-1.0)
def upper_z(r):return .344+slope*(r-1.0)

# Each cassette is aligned with its armor sector and the tilted upper surface.
for station in range(8):
    a=(station*2+.5)*math.tau/16
    radial=Vector((math.cos(a),math.sin(a),0))
    tangent=Vector((-math.sin(a),math.cos(a),0))
    outward=Vector((radial.x,radial.y,slope)).normalized()
    normal=tangent.cross(-outward).normalized()
    basis=Matrix((tangent,-outward,normal)).transposed()
    anchor=radial*1.094+Vector((0,0,upper_z(1.094)))
    def control(name,x,y,z,size,mat,bevel=.0018):
        return box('console %02d | '%station+name,anchor+basis@Vector((x,y,z)),size,mat,basis,bevel)
    control('metal bezel',0,0,.003,(.212,.165,.010),edge,.005)
    control('inset dark panel',0,0,.008,(.195,.151,.005),black,.003)
    # Three large ivory keys, three shorter blue keys, a tiny screen and red indicator.
    for key,x in enumerate([-.063,0,.063]):
        control('key socket %d'%key,x,-.027,.012,(.052,.076,.005),key_shell,.003)
        control('ivory key %d'%key,x,-.027,.016,(.034,.059,.007),ice,.003)
        control('cyan key %d'%key,x,.028,.015,(.034,.022,.006),blue,.002)
    control('telemetry screen',-.030,.057,.013,(.100,.014,.003),screen,.001)
    for j in range(4):
        control('screen mark %d'%j,-.067+j*.020,.058,.015,(.011,.003,.001),blue,.0003)
    control('red status indicator',.065,.057,.015,(.030,.014,.005),red,.002)
    for x in [-.093,.093]:
        for y in [-.067,.066]:
            control('captive fastener',x,y,.012,(.006,.006,.003),edge,.001)

    # Recessed upright fascia lamps with a dark metal surround and central divider.
    b=a
    radial2=Vector((math.cos(b),math.sin(b),0));tan2=Vector((-math.sin(b),math.cos(b),0))
    basis2=Matrix((tan2,Vector((0,0,1)),radial2)).transposed()
    lamp=radial2*(R+.0005)+Vector((0,0,.238))
    box('fascia lamp %02d | bezel'%station,lamp,(.073,.071,.008),black,basis2,.004)
    box('fascia lamp %02d | frosted lens'%station,lamp+radial2*.0045,(.040,.055,.003),white,basis2,.003)
    box('fascia lamp %02d | divider'%station,lamp+radial2*.0065,(.004,.056,.002),edge,basis2,.0005)

COL['clone_wars_refinement']=True
COL['original_radius_m']=source_radius
COL['radius_scale']=FACTOR
COL['radius_m']=R
COL['design']='Rounded sloped upper/lower armor; eight recessed Republic-style control cassettes.'
bpy.context.view_layer.update()
assert protected=={name:signature(bpy.data.objects[name]) for name in protected}, 'Unrelated scene object changed'
actual=max(v.co.xy.length for v in bpy.data.objects[PREFIX+'armored band panel 00'].data.vertices)
assert abs(actual/source_radius-FACTOR)<1e-5

# Save reusable source inside the blend and leave a useful unselected close view.
text=bpy.data.texts.get('refine_holo_table.py') or bpy.data.texts.new('refine_holo_table.py')
text.clear();text.write(Path(__file__).read_text())
for o in bpy.context.selected_objects:o.select_set(False)
target=CENTER+Vector((0,0,.19))
eye=target+Vector((-.8,-3.6,2.35))
for a in bpy.context.screen.areas:
    if a.type=='VIEW_3D':
        s=a.spaces.active
        s.region_3d.view_perspective='PERSP'
        s.region_3d.view_location=target
        s.region_3d.view_rotation=(eye-target).to_track_quat('Z','Y')
        s.region_3d.view_distance=4.4
        s.overlay.show_overlays=False

audit={'source_radius_m':source_radius,'new_radius_m':R,'radius_factor':actual/source_radius,
       'center':list(CENTER),'control_panels':8,'ivory_keys':24,'cyan_keys':24,
       'red_indicators':8,'rounded_upper_and_lower_profile':profile,
       'unrelated_objects_preserved':len(protected),'original_controls_archived':len(replaced),
       'active_table_objects':len(COL.objects),'backup':str(OUT/'before-holo-table-refinement.blend')}
(OUT/'audit.json').write_text(json.dumps(audit,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath,compress=True)
result=audit
