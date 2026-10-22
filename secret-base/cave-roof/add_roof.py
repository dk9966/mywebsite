import bpy,bmesh,math,random,json
from mathutils import Vector
from mathutils.geometry import delaunay_2d_cdt
w=bpy.data.objects['150 | continuous cave with oblique carved rooms']
source=bpy.data.meshes[w['roof_source_mesh']] if 'roof_source_mesh' in w else w.data
bm=bmesh.new();bm.from_mesh(source);bm.verts.ensure_lookup_table()
rim=[v for v in bm.verts if v.is_boundary and v.co.z>15]
rimset=set(rim);edges=[e for e in bm.edges if e.is_boundary and all(v in rimset for v in e.verts)]
assert len(edges)==len(rim)
pts=[Vector((v.co.x,v.co.y)) for v in rim]; heights=[v.co.z for v in rim]
lookup={v:i for i,v in enumerate(rim)}
constraints=[tuple(lookup[v] for v in e.verts) for e in edges]
def roof_z(x,y):
    d=min(math.hypot(x-v.co.x,y-v.co.y) for v in rim)
    return 17.1+2.1*(1-math.exp(-d/3))+.28*math.sin(x*.7+y*.32)+.19*math.cos(y*.9-x*.36)
# Uneven, broad-rooted dripstone clusters, integrated into the ceiling mesh.
spikes=[(-7.3,3.2,1.15,5.2),(-4.0,6.3,1.35,6.0),(-2.35,6.7,.60,4.4),(1.2,7.6,.95,5.3),(4.2,2.0,.85,4.5),(-.6,-2.2,.72,3.8)]
rng=random.Random(925)
for x,y,r,l in spikes:
    z=roof_z(x,y)
    rings=[]
    for scale,drop,shift in [(1,0,0),(.56,.7,.08),(.23,l*.67,.17)]:
        ring=[]
        for k in range(7):
            a=2*math.pi*k/7
            rr=r*scale*(1+rng.uniform(-.15,.15))
            ring.append(len(pts));pts.append(Vector((x+rr*math.cos(a)+shift,y+rr*math.sin(a))))
            heights.append(z-drop+rng.uniform(-.12,.12))
        constraints.extend((ring[k],ring[(k+1)%7]) for k in range(7));rings.append(ring)
    pts.append(Vector((x+.24,y-.10)));heights.append(z-l)
for row in range(34):
    y=-19+row*1.03
    for col in range(27):
        x=-15+col*1.03+(row%2)*.5
        x+=rng.uniform(-.2,.2);yy=y+rng.uniform(-.2,.2)
        if min(math.hypot(x-v.co.x,yy-v.co.y) for v in rim)<.45:continue
        if any(math.hypot(x-a,yy-b)<r*1.25 for a,b,r,l in spikes):continue
        pts.append(Vector((x,yy)));heights.append(roof_z(x,yy))
# CDT inside the closed rim; every perimeter vertex is reused verbatim.
vs,es,fs,orig,_,_=delaunay_2d_cdt(pts,constraints,[],0,1e-6,True)
# Filter by polygon winding, since the outer roof is concave.
ordered=[rim[0]];prev=None
while True:
    nxt=[e.other_vert(ordered[-1]) for e in ordered[-1].link_edges if e in edges and e.other_vert(ordered[-1])!=prev]
    v=nxt[0]
    if v==ordered[0]:break
    prev=ordered[-1];ordered.append(v)
def inside(x,y):
    c=False
    for a,b in zip(ordered,ordered[1:]+ordered[:1]):
        ax,ay=a.co.x,a.co.y;bx,by=b.co.x,b.co.y
        if (ay>y)!=(by>y) and x<(bx-ax)*(y-ay)/(by-ay)+ax:c=not c
    return c
mapped=[]
for p,ids in zip(vs,orig):
    idx=next((i for i in ids if i<len(rim)),None)
    if idx is not None:mapped.append(rim[idx]);continue
    idx=ids[0] if ids else None
    mapped.append(bm.verts.new((p.x,p.y,heights[idx] if idx is not None else roof_z(p.x,p.y))))
newfaces=[]
for f in fs:
    c=sum((vs[i] for i in f),Vector((0,0)))/len(f)
    if inside(c.x,c.y):
        face=bm.faces.new([mapped[i] for i in reversed(f)]);face.smooth=False;newfaces.append(face)
# Remove only unused new CDT points outside the wall contour.
loose=[v for v in bm.verts if not v.link_edges]
bmesh.ops.delete(bm,geom=loose,context='VERTS')
assert all(len(e.link_faces)==2 for e in edges),'Roof seam is not welded'
for f in newfaces:
    if f.normal.z>0:f.normal_flip()
newmesh=bpy.data.meshes.new('Cave | walls and welded vaulted dripstone roof')
bm.to_mesh(newmesh);bm.free();newmesh.materials.clear()
for m in source.materials:newmesh.materials.append(m)
w.data=newmesh
source.use_fake_user=True
w['roof_source_mesh']=source.name
w['roof_description']='Continuous faceted vault welded to all upper wall rim edges; six integrated irregular stalactites. Original camera retained.'
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
result={'roof_faces':len(newfaces),'welded_rim_edges':len(edges),'stalactites':len(spikes),'file':bpy.data.filepath}
