"""Curve four roof ends onto the circular housing and add a native radius slider."""
import bpy, bmesh, math, json
from pathlib import Path
from mathutils import Vector

P=Path('/Users/danielku/mywebsite/secret-base/rounded-roof-light')
S=bpy.context.scene
C=bpy.data.collections['165 | Circular workshop light and four roof slopes']
root=bpy.data.objects['Lower | circular roof assembly']
ctrl=bpy.data.objects['SCENE SLIDERS']
control=ctrl.modifiers['Scene Sliders']
assert not root.get('rounded_roof_revision')
R=1.46
H=1.15
radius=control.node_group.interface.new_socket(name='Light radius (m)',in_out='INPUT',socket_type='NodeSocketFloat')
radius.default_value=R
radius.min_value=.85
radius.max_value=2.10
radius.description='Radius of the circular light housing. The rounded roof ends and nearby rock follow automatically.'
control[radius.identifier]=R
rpath='modifiers["Scene Sliders"]["'+radius.identifier+'"]'
root['radius_control']='Light radius (m)'

def driver(owner,path,expression='r'):
    f=owner.driver_add(path)
    f.driver.type='SCRIPTED'
    f.driver.expression=expression
    v=f.driver.variables.new();v.name='r';v.type='SINGLE_PROP'
    v.targets[0].id=ctrl;v.targets[0].data_path=rpath

g=bpy.data.node_groups['Lower | roof crown height deformation']
rs=g.interface.new_socket(name='Crown radius',in_out='INPUT',socket_type='NodeSocketFloat')
rs.default_value=R
gi=next(n for n in g.nodes if n.bl_idname=='NodeGroupInput')
sp=next(n for n in g.nodes if n.bl_idname=='GeometryNodeSetPosition')
height_offset=sp.inputs['Offset'].links[0].from_socket
attr=g.nodes.new('GeometryNodeInputNamedAttribute');attr.data_type='FLOAT_VECTOR'
attr.inputs['Name'].default_value='crown_radius_vector'
sub=g.nodes.new('ShaderNodeMath');sub.operation='SUBTRACT';sub.inputs[1].default_value=R
g.links.new(gi.outputs['Crown radius'],sub.inputs[0])
scale=g.nodes.new('ShaderNodeVectorMath');scale.operation='SCALE'
g.links.new(attr.outputs['Attribute'],scale.inputs[0]);g.links.new(sub.outputs[0],scale.inputs['Scale'])
add=g.nodes.new('ShaderNodeVectorMath');add.operation='ADD'
g.links.new(height_offset,add.inputs[0]);g.links.new(scale.outputs[0],add.inputs[1])
g.links.new(add.outputs[0],sp.inputs['Offset'])
for o in C.objects:
    if o.type!='MESH':continue
    a=o.data.attributes.new('crown_radius_vector','FLOAT_VECTOR','POINT')
    for d,v in zip(a.data,o.data.vertices):d.vector=(v.co.x/R,v.co.y/R,0)
    mod=o.modifiers['Follow circular light height']
    mod[rs.identifier]=R
    driver(mod,'["'+rs.identifier+'"]')
light=bpy.data.lights['Lower | circular crown downlight']
driver(light,'size','2.50*r/1.46')

def replace(o,verts,faces,weights,vectors):
    old=o.data;old.use_fake_user=True
    o['before_rounded_roof_mesh']=old.name
    me=bpy.data.meshes.new(o.name+' | rounded rim fit')
    me.from_pydata(verts,[],faces)
    for m in old.materials:me.materials.append(m)
    bm=bmesh.new();bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
    a=me.attributes.new('crown_height_weight','FLOAT','POINT')
    for d,w in zip(a.data,weights):d.value=w
    a=me.attributes.new('crown_radius_vector','FLOAT_VECTOR','POINT')
    for d,v in zip(a.data,vectors):d.vector=v
    o.data=me

lower=bpy.data.objects['Lower | plain octagon']
inv=root.matrix_world.inverted()
outline=[inv@lower.matrix_world@lower.data.vertices[8+i].co for i in [6,5,4,3,2]]
for p in outline:p.z=0
angles=[]
for p in outline:
    angle=math.atan2(p.y,p.x)
    if angles:
        while angle-angles[-1]>math.pi:angle-=math.tau
        while angle-angles[-1]<-math.pi:angle+=math.tau
    angles.append(angle)
rows=[0,.15,.3,.45,.6,.72,.78,.84,.90,.94,.97,.99,1]

def easing(t):
    if t<=.78:return t
    u=(t-.78)/.22
    return .78+.22*(u+u*u-u*u*u)

def cross(a,b):return a.x*b.y-a.y*b.x

def point(a,b,angle,t,offset=0):
    unit=Vector((math.cos(angle),math.sin(angle),0))
    extent=cross(a,b-a)/cross(unit,b-a)
    r=extent*(1-t)+R*t
    p=unit*r+Vector((0,0,easing(t)*(H-.075)+offset))
    return p,easing(t),unit*t

roofs=sorted((o for o in C.objects if 'roof_section' in o),key=lambda o:o['roof_section'])
for i,o in enumerate(roofs):
    a,b=outline[i:i+2]
    n=max(12,math.ceil(abs(angles[i+1]-angles[i])*40))
    vs=[];ws=[];rv=[];faces=[]
    width=n+1;layer=width*len(rows)
    for dz in [0,-.075]:
        for t in rows:
            for j in range(width):
                angle=angles[i]+(angles[i+1]-angles[i])*j/n
                p,w,v=point(a,b,angle,t,dz)
                vs.append(p);ws.append(w);rv.append(v)
    for k in range(len(rows)-1):
        for j in range(n):
            f=(k*width+j,k*width+j+1,(k+1)*width+j+1,(k+1)*width+j)
            faces.append(f);faces.append(tuple(v+layer for v in reversed(f)))
    perimeter=list(range(width))+[k*width+n for k in range(1,len(rows))]
    perimeter+=list(range(layer-2,layer-width-1,-1))
    perimeter+=[k*width for k in range(len(rows)-2,0,-1)]
    faces.extend((x,y,y+layer,x+layer) for x,y in zip(perimeter,perimeter[1:]+perimeter[:1]))
    replace(o,vs,faces,ws,rv)
    # Small edge treatment: the curved inner boundary remains accurate to the rim.
    o.modifiers['Fabricated edge radius'].width=.003
    o['curved_end_radius_m']=R
    o['arc_segments']=n
    o['inner_top_indices']=list(range(layer-width,layer))
    o['wall_top_indices']=list(range(width))
    o['roof_rows']=rows
    o['end_profile']='Circular arc with horizontal tangent at the crown; fixed wall edge.'

def rebuild_rib(o,a,b,angle,width,depth,offset):
    verts=[];weights=[];vectors=[];faces=[]
    side=Vector((-math.sin(angle),math.cos(angle),0))
    for t in rows:
        p,w,v=point(a,b,angle,t,offset)
        for sx,sz in [(-1,-1),(1,-1),(1,1),(-1,1)]:
            verts.append(p+side*sx*width/2+Vector((0,0,sz*depth/2)))
            weights.append(w);vectors.append(v)
    faces.extend([(3,2,1,0),tuple(range(len(verts)-4,len(verts)))])
    for k in range(len(rows)-1):
        for j in range(4):faces.append((k*4+j,k*4+(j+1)%4,(k+1)*4+(j+1)%4,(k+1)*4+j))
    replace(o,verts,faces,weights,vectors)
for i in range(4):
    rebuild_rib(bpy.data.objects['Lower | roof panel seam %d'%(i+1)],outline[i],outline[i+1],
                (angles[i]+angles[i+1])/2,.016,.010,.012)
for i in range(5):
    j=min(i,3)
    rebuild_rib(bpy.data.objects['Lower | roof joint rib %d'%(i+1)],outline[j],outline[j+1],angles[i],.075,.085,-.005)

root['rounded_roof_revision']=True
root['description']='Four curved roof panels with circular ends tangent to the adjustable light rim.'
ctrl['How to use']='Light height above walls (m) and Light radius (m) adjust the fixture, rounded roof ends, and nearby rock together.'
ctrl.update_tag();S.frame_set(S.frame_current);bpy.context.view_layer.update()
report={'roof_sections':4,'light_radius_default':R,'radius_range':[.85,2.10],
        'preserved_height':float(control['Socket_8']),'radius_socket':radius.identifier,
        'rounded_inner_edges':True,'horizontal_tangent_at_light':True}
(P/'roof-build.json').write_text(json.dumps(report,indent=2))
result=report
