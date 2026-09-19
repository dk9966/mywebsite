"""Continuous open-bottom cave vault and grounded island foundations.

Executed by build_cave_backdrop.py with its camera frame and material helpers.
The hanging folds are displacements of the vault itself, not separate cones.
"""
from mathutils import noise

profile=[(-10.6,-20),(-10.2,-12),(-10.35,-6),(-10.15,-1),(-10.5,4.4),(-9.1,6.4),(-6.4,6.8),(-3.2,7.1),(-.5,7.8),(2.1,7.3),(4.7,6.4),(7.2,6.7),(9.1,6.2),(10.35,4.3),(10.4,-1),(10.1,-6),(10.7,-12),(11,-20)]
path=[]
for a,b in zip(profile,profile[1:]):
    dist=math.hypot(b[0]-a[0],b[1]-a[1]);steps=math.ceil(dist/.52)
    for k in range(steps):
        t=k/steps;path.append((a[0]*(1-t)+b[0]*t,a[1]*(1-t)+b[1]*t))
path.append(profile[-1])
N=len(path);rows=46;verts=[];faces=[]
folds=[(-4.2,-6.3,5.2,1.6,3.0),(-3.7,-7.8,1.3,.7,1.2),
       (4.7,-6.0,5.65,1.85,3.0),(6.0,-8.2,1.1,.65,1.4),
       (-8.3,-3,.75,1.0,2.1),(8.1,-3.5,.8,.9,2.1),
       (-1.7,-3.2,1.0,.5,1.2),(.5,-7.8,1.15,.5,1.1),(2.5,-2.8,.75,.5,1.3)]
for j in range(rows):
    depth=-10.8+j*29/(rows-1)
    front=max(0,(depth+3)/12)
    for i,(xx,yy) in enumerate(path):
        x=xx*(1+front*.33);y=yy+front*3.8
        nv=noise.noise_vector(Vector((xx*.44,yy*.37,depth*.39)))
        x+=nv.x*.45;y+=nv.y*.4;d=depth+nv.z*.36
        # Broad roots grow continuously out of the same roof grid.
        if yy>5:
            for cx,cd,amp,wx,wd in folds:
                g=math.exp(-((xx-cx)/wx)**2-((depth-cd)/wd)**2)
                y-=amp*g
            y+=.16*math.sin(xx*3.5+depth*1.3)
        elif abs(xx)>9:
            # Uneven vertical folds move the side walls close to the platforms.
            x-=math.copysign(.42*math.sin(yy*1.1+depth*.4)+.37*math.sin(depth*1.5),x)
        verts.append(p(x,y,d))
# Sharply tapered formations are extruded from patches of the roof grid.
# The patch boundary is shared with the vault, so roots are genuinely connected.
patches=[];occupied=set()
for x_target,d_target,length,lean in [(-8.2,-1.2,1.05,-.16),(-6.4,-2.5,1.65,.2),(-3.1,-1.5,1.55,-.18),(-1.7,-3.7,1.8,.1),(.2,-2.0,1.05,-.13),(1.8,-4.1,1.55,.2),(3.2,-.7,1.2,-.12),(6.5,-1.7,1.05,-.2),(8.2,-2.7,.45,.15)]:
    pi=min(range(len(path)),key=lambda k:abs(path[k][0]-x_target) if path[k][1]>5 else 1000)
    pj=round((d_target+10.8)/29*(rows-1))
    i0=pi-1;j0=pj-1;size=2
    cells={(j,i) for j in range(j0,j0+size) for i in range(i0,i0+size)}
    if cells & occupied:continue
    occupied.update(cells)
    boundary=[j0*N+i for i in range(i0,i0+size)]
    boundary += [j*N+i0+size for j in range(j0,j0+size)]
    boundary += [(j0+size)*N+i for i in range(i0+size,i0,-1)]
    boundary += [j*N+i0 for j in range(j0+size,j0,-1)]
    patches.append((boundary,length,lean))
for j in range(rows-1):
    for i in range(N-1):
        if (j,i) in occupied:continue
        a=j*N+i;b=a+1;c=a+N;d=c+1
        faces.extend([(a,c,b),(b,c,d)] if (i+j)%2 else [(a,c,d),(a,d,b)])
for boundary,length,lean in patches:
    center=sum((verts[k] for k in boundary),Vector())/len(boundary)
    previous=boundary
    for fraction,drop in [(.69,.28),(.28,.72)]:
        current=[]
        for k in boundary:
            bend=lean*(1.5 if drop<.5 else .45)
            v=center+(verts[k]-center)*fraction-U*(length*drop)+R*bend+D*(.06 if drop<.5 else -.04)
            current.append(len(verts));verts.append(v)
        for k in range(len(boundary)):
            a=previous[k];b=previous[(k+1)%len(boundary)];c=current[k];d=current[(k+1)%len(boundary)]
            faces.extend([(a,b,c),(b,d,c)])
        previous=current
    tip=len(verts);verts.append(center-U*length+R*lean+D*.07)
    for k in range(len(previous)):faces.append((previous[k],previous[(k+1)%len(previous)],tip))
vault=mesh('Cave | continuous sculpted walls and hanging roof',verts,faces,rocks)
vault['construction']='One connected triangulated vault; all hanging folds share roof vertices. Open chasm below.'
# Correct orientation for visible cave interior.
import bmesh
bm=bmesh.new();bm.from_mesh(vault.data);bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS');bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(vault.data);bm.free()

# Each existing pillar now rests on a real crag extending into a shared deep floor.
# Foundations remain independent of side walls and preserve the original objects.
for island in [o for o in s.objects if o.name.startswith('island_pillar') and not o.hide_render]:
    points=[island.matrix_world@v.co for v in island.data.vertices]
    cx,cy=island.matrix_world.translation.xy
    bottom=[v for v in points if v.z<.18]
    radius=max(math.hypot(v.x-cx,v.y-cy) for v in bottom)
    ns=32;vs=[];fs=[]
    angular=[random.uniform(.90,1.12) for _ in range(ns)]
    levels=[(.12,1.08),(-.38,1.12),(-.85,1.15),(-1.6,1.07),(-2.15,1.13),(-2.7,1.16),(-3.3,1.12),(-3.8,1.1),(-4.5,1.18),(-5.2,1.21),(-6,1.17),(-6.8,1.19),(-8.5,1.35),(-11,1.4),(-15,1.7),(-19,1.85)]
    for j,(z,mult) in enumerate(levels):
        for k in range(ns):
            a=k*2*math.pi/ns
            rr=radius*mult*angular[k]*(1 if j==0 else random.uniform(.94,1.08))
            point=Vector((cx+math.cos(a)*rr+math.sin(j*.8)*.14,cy+math.sin(a)*rr+math.cos(j*.7)*.16,z+(random.uniform(-.05,.02) if j==0 else random.uniform(-.33,.33))))
            screen_x=(point-C).dot(R)
            if abs(screen_x)>9.4:point-=R*(screen_x-math.copysign(9.4,screen_x))
            vs.append(point)
    fs.append(tuple(reversed(range(ns))))
    for j in range(len(levels)-1):
        for k in range(ns):
            a=j*ns+k;b=j*ns+(k+1)%ns;c=(j+1)*ns+k;d=(j+1)*ns+(k+1)%ns
            fs.extend([(a,b,c),(b,d,c)])
    o=mesh('Cave | bedrock foundation '+island.name,vs,fs,rocks)
    o['supports']=island.name
    bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free()
# Deep ground intersects all foundation roots well below the composition.
vs=[];fs=[]
for j in range(18):
    for i in range(25):
        x=0+i*2;y=-20+j*2.5;z=-18+noise.noise(Vector((x*.13,y*.13,0)))*1.2
        vs.append((x,y,z))
for j in range(17):
    for i in range(24):
        a=j*25+i;fs.extend([(a,a+1,a+25),(a+1,a+26,a+25)])
mesh('Cave | deep continuous bedrock ground',vs,fs,rocks)
