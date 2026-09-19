"""Volume-first, non-overlapping rock partitions. Pure Python geometry helpers."""
import random, math

def volume(b):
    return (b[1]-b[0])*(b[3]-b[2])*(b[5]-b[4])

def subtract(box, cutter):
    """Subtract an axis-aligned cut as at most six disjoint solid boxes."""
    intersection = tuple(v for axis in range(3) for v in
        (max(box[2*axis],cutter[2*axis]),min(box[2*axis+1],cutter[2*axis+1])))
    if any(intersection[2*i]>=intersection[2*i+1] for i in range(3)):
        return [box]
    middle=list(box);result=[]
    for axis in range(3):
        j=2*axis
        if middle[j]<intersection[j]:
            part=middle.copy();part[j+1]=intersection[j];result.append(tuple(part));middle[j]=intersection[j]
        if middle[j+1]>intersection[j+1]:
            part=middle.copy();part[j]=intersection[j+1];result.append(tuple(part));middle[j+1]=intersection[j+1]
    return result

def carve(box, cutters):
    solids=[box]
    for cutter in cutters:
        solids=[p for b in solids for p in subtract(b,cutter)]
    return solids

def subdivide(box, rng, target=(1.6,1.9,2.2), depth=0):
    """Recursive shared planes; each leaf exactly partitions its parent."""
    dims=[box[2*i+1]-box[2*i] for i in range(3)]
    ratios=[dims[i]/target[i] for i in range(3)]
    if max(ratios)<1.45 or depth>18 or volume(box)<1.0:
        return [box]
    viable=[i for i in range(3) if dims[i]>target[i]*1.3]
    axis=max(viable,key=lambda i:ratios[i]*rng.uniform(.8,1.25))
    j=axis*2;split=round((box[j]+dims[axis]*rng.uniform(.32,.68))*10)/10
    split=max(box[j]+.38,min(box[j+1]-.38,split))
    left=list(box);right=list(box);left[j+1]=split;right[j]=split
    return subdivide(tuple(left),rng,target,depth+1)+subdivide(tuple(right),rng,target,depth+1)

def partitions(tag, bounds, kind='support', seed=416):
    """Carve coherent exterior pockets before creating any individual blocks."""
    rng=random.Random(seed+sum((i+1)*ord(c) for i,c in enumerate(tag)))
    x0,x1,y0,y1,z0,z1=bounds;w=x1-x0;d=y1-y0;h=z1-z0;cuts=[]
    if kind=='support':
        # The middle 50% of the support is never cut. All side columns start at z0.
        for side in [0,1]:
            xa,xb=(x0,x0+w*.24) if side==0 else (x1-w*.24,x1)
            cuts.append((xa,xb,y0,y0+d*.32,z1-rng.uniform(2,5),z1+.1))
            cuts.append((xa,xb,y1-d*.23,y1,z1-rng.uniform(1,4),z1+.1))
        for i in range(3):
            zz=z0+h*(.15+i*.23);xx=x0+w*rng.uniform(.05,.65)
            cuts.append((xx,min(x1,xx+w*.28),y0,y0+d*.13,zz,min(z1,zz+2.1)))
    elif kind=='wall':
        # Wide, shallow pockets form related ledges rather than floating blocks.
        for i in range(7):
            xx=x0+w*rng.uniform(0,.65);zz=z0+h*(i/8)
            cuts.append((xx,min(x1,xx+w*rng.uniform(.28,.5)),y0,y0+min(d*.22,1.6),zz,min(z1,zz+rng.uniform(3,6))))
        cuts.append((x0,x0+w*.18,y0,y0+d*.25,z1-5,z1+.1))
    else:
        # Ceiling pockets cut upward from the lower surface, leaving a solid cap.
        for i in range(5):
            xx=x0+w*rng.uniform(0,.7);yy=y0+d*rng.uniform(0,.65)
            cuts.append((xx,min(x1,xx+w*.3),yy,min(y1,yy+d*.34),z0-.1,z0+h*rng.uniform(.25,.6)))
    # Related exterior patches recess into the body, never float away from it.
    if kind in ('support','wall'):
        panels=subdivide((x0,x1,0,1,z0,z1),rng,(2.8,10,3.2))
        for p in panels:
            xx=(p[0]+p[1])/2;zz=(p[4]+p[5])/2
            level=round((math.sin(xx*.77+zz*.31)+math.cos(zz*.8-xx*.27)+2)*.65)
            depth=min(d*.23,1.6)*level/3
            if depth>.01:cuts.append((p[0],p[1],y0,y0+depth,p[4],p[5]))
        panels=subdivide((y0,y1,0,1,z0,z1),rng,(3.1,10,3.7))
        for p in panels:
            yy=(p[0]+p[1])/2;zz=(p[4]+p[5])/2
            level=round((math.sin(yy*.63+zz*.42)+math.cos(zz*.71)+2)*.6)
            depth=min(w*.19,1.3)*level/3
            if depth>.01:
                cuts.append((x0,x0+depth,p[0],p[1],p[4],p[5]))
                cuts.append((x1-depth,x1,p[0],p[1],p[4],p[5]))
    else:
        panels=subdivide((x0,x1,y0,y1,0,1),rng,(3.2,3.8,10))
        for p in panels:
            xx=(p[0]+p[1])/2;yy=(p[2]+p[3])/2
            level=round((math.sin(xx*.7)+math.cos(yy*.8+xx*.3)+2)*.6)
            depth=min(h*.6,2.0)*level/3
            if depth>.01:cuts.append((p[0],p[1],p[2],p[3],z0,z0+depth))
    solids=carve(bounds,cuts)
    leaves=[leaf for b in solids for leaf in subdivide(b,rng)]
    return leaves,solids,cuts
