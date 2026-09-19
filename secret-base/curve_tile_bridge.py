"""Shorten existing Experience bridge by 25%, arch it, replace overlapping tiles.
One-shot, starting from base.experience-iteration-1.blend. No scene reset/render.
"""
import bpy, math
from mathutils import Vector, Matrix
scene=bpy.context.scene
spec=scene['experience_bridge_specs']
assert not spec.get('curved',False), 'Already curved'
CX=21.299999237060547;F=6.871178627
YP=float(spec['project_end_y']);OLDYE=float(spec['experience_end_y'])
OLDL=YP-OLDYE; L=OLDL*.75;YE=YP-L;SHIFT=YE-OLDYE
ARCH=.20
bc=bpy.data.collections['bridge_project_experience']
project=bpy.data.objects['island_pillar_project']
exp=bpy.data.objects['island_pillar_experience']

def floor(y):
    t=max(0,min(1,(YP-y)/L))
    return F-.5*t+ARCH*math.sin(math.pi*t)
def oldfloor(y):return F+(y-YP)*.5/OLDL

# Freeze coordinates first because some bridge lamps belong to Experience.
snap={o:[o.matrix_world@v.co for v in o.data.vertices] for o in bc.objects if o.type=='MESH'}
lightpos={o:o.matrix_world.copy() for o in bc.objects if o.type=='LIGHT'}
mw=exp.matrix_world.copy();mw.translation.y+=SHIFT;exp.matrix_world=mw
bpy.context.view_layer.update()

def replace_mesh(ob,vs,faces):
    me=bpy.data.meshes.new(ob.name+'_curved_mesh')
    me.from_pydata(vs,[],faces);me.update()
    for mat in ob.data.materials:me.materials.append(mat)
    ob.data=me
    ob.matrix_world=Matrix.Identity(4)

def sweep(x0,x1,y0,y1,z0,z1,n):
    vs=[];fs=[]
    for i in range(n+1):
        y=y0+(y1-y0)*i/n;z=floor(y)
        vs += [(x0,y,z+z0),(x1,y,z+z0),(x1,y,z+z1),(x0,y,z+z1)]
    for i in range(n):
        for k in range(4):fs.append((4*i+k,4*i+(k+1)%4,4*(i+1)+(k+1)%4,4*(i+1)+k))
    fs.extend([(3,2,1,0),(4*n,4*n+1,4*n+2,4*n+3)])
    return vs,[tuple(reversed(face)) for face in fs]

for ob,pts in snap.items():
    name=ob.name
    if name.startswith('bridge_paver_'):
        bpy.data.objects.remove(ob,do_unlink=True);continue
    rigid=any(k in name for k in ('abutment','newel','threshold','anchor','lantern'))
    end='experience' if 'experience' in name else 'project'
    if rigid:
        delta=Vector((0,SHIFT if end=='experience' else 0,0))
        coords=[p+delta for p in pts]
    elif 'knee' in name:
        delta=SHIFT if end=='experience' else 0
        f=F-.5 if end=='experience' else F
        coords=[]
        for p in pts:
            q=p.copy();q.y+=delta
            w=max(0,min(1,(p.z-(f-.96))/.71))
            q.z+=w*(floor(q.y)-oldfloor(p.y))
            coords.append(q)
    else:
        y0=min(p.y for p in pts);y1=max(p.y for p in pts)
        if y1-y0>OLDL*.8:
            x0=min(p.x for p in pts);x1=max(p.x for p in pts)
            z0=min(p.z-oldfloor(p.y) for p in pts);z1=max(p.z-oldfloor(p.y) for p in pts)
            if name=='bridge_structural_deck':z0-=.04;z1-=.04
            vs,fs=sweep(x0,x1,YP+(y0-YP)*.75,YP+(y1-YP)*.75,z0,z1,80)
            replace_mesh(ob,vs,fs);continue
        coords=[]
        for p in pts:
            q=p.copy();q.y=YP+(p.y-YP)*.75;q.z=p.z-oldfloor(p.y)+floor(q.y);coords.append(q)
    # Existing faces remain valid; convert world positions back to current local.
    inv=ob.matrix_world.inverted()
    for v,p in zip(ob.data.vertices,coords):v.co=inv@p
    ob.data.update()

for ob,mw in lightpos.items():
    if 'experience' in ob.name:mw.translation.y+=SHIFT
    elif ob.name=='bridge_soft_fill':mw.translation.y=YP+(mw.translation.y-YP)*.75
    ob.matrix_world=mw

# Separate tile solids sit on a recessed slab: no coplanar overlapping faces.
base=bpy.data.materials['stationFloorSatin']
for name,factor in [('bridge_tile_dark',.88),('bridge_tile_light',1.08)]:
    mat=bpy.data.materials.get(name)
    if mat is None:
        mat=base.copy();mat.name=name
        node=mat.node_tree.nodes.get('Principled BSDF')
        color=list(node.inputs['Base Color'].default_value)
        node.inputs['Base Color'].default_value=tuple(c*factor for c in color[:3])+(color[3],)

for col in range(1):
    step=L/14;offset=col*step/2
    for i in range(-1,15):
        a=max(YE,YE+i*step+offset);b=min(YP,YE+(i+1)*step+offset)
        if b-a<.025:continue
        x0=CX-.351
        x1=CX+.351
        # One tile across the width, with 8mm joints along the curved span.
        vs,fs=sweep(x0,x1,a+.004,b-.004,-.041,0,4)
        me=bpy.data.meshes.new('bridge_tile_mesh');me.from_pydata(vs,[],fs);me.update()
        ob=bpy.data.objects.new('bridge_tile_%s_%02d'%(col,i+1),me);bc.objects.link(ob)
        matname='bridge_tile_dark' if (i+col)%4==0 else 'bridge_tile_light' if (i+col)%4==2 else 'stationFloorSatin'
        me.materials.append(bpy.data.materials[matname])
        ob.parent=project;ob.matrix_parent_inverse=project.matrix_world.inverted()
        mod=ob.modifiers.new('Tile edge chamfer','BEVEL');mod.width=.002;mod.segments=1

spec['old_span']=OLDL;spec['span']=L;spec['span_reduction']=.25;spec['experience_end_y']=YE
spec['experience_center_y']=exp.matrix_world.translation.y;spec['curved']=True;spec['arch_above_chord']=ARCH
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath='/Users/danielku/mywebsite/secret-base/base.curved-iteration-1.blend',copy=True)
