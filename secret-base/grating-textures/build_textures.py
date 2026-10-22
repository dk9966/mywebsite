"""Bake exact existing bar footprints into compact shared color/alpha + normal maps.

This is a deterministic geometry bake, not an artistic approximation. UV frames
follow each circular sector or bridge axis. Pixel-edge bevels provide the tiny
normal changes previously produced by the geometry bevel modifiers.
"""
import hashlib, json, math
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import distance_transform_edt, gaussian_filter
from scipy.spatial import ConvexHull, Delaunay

P = Path(__file__).resolve().parent
OUT = P / 'textures'
OUT.mkdir(exist_ok=True)
source = json.loads((P / 'source-geometry.json').read_text())
ppm, aa, pad = 768, 3, .004
cache, records = {}, []
colors = {'Metal | brushed grating steel': [.019,.026,.033],
          'Bridge | graphite open steel grating': [.052,.075,.091]}

def srgb(x):
    return np.where(x <= .0031308, x*12.92, 1.055*np.maximum(x,0)**(1/2.4)-.055)

for obj in source:
    name = obj['name']
    v = np.array(obj['vertices'])
    circular = name.startswith('Metal | recessed open grate')
    bridge = name == 'Bridge | fine open welded grating'
    angle = 0.
    if circular:
        sector = int(name[-2:])
        a = sector*math.pi/4 + (.075 if sector%2 else .020)
        b = (sector+1)*math.pi/4 - (.075 if (sector+1)%2 else .020)
        angle = (a+b)/2
    elif bridge:
        angle = math.atan2(-.625,1)
    basis = np.array([[math.cos(angle),-math.sin(angle)],
                      [math.sin(angle),math.cos(angle)]])
    q = v[:,:2] @ basis
    lo, hi = q.min(0)-pad, q.max(0)+pad
    span = np.round(hi-lo,4)
    size = np.maximum(16, np.ceil(span*ppm).astype(int))
    # Quantize well below a texel, so translated/rotated copies share textures.
    polygons=[]
    for face in obj['faces']:
        f=np.array(face)
        normal=np.cross(v[f[1]]-v[f[0]],v[f[2]]-v[f[0]])
        if normal[2] <= 1e-9: continue
        xy=np.round(q[f]-lo,4)
        polygons.append(xy)
    assert polygons, name
    high=Image.new('L',tuple(size*aa))
    draw=ImageDraw.Draw(high)
    for poly in polygons:
        xy=poly/span*(size*aa-1)
        draw.polygon([tuple(p) for p in xy], fill=255)
    # Arrays and PNGs are stored bottom-up here; flip when saving PNG below.
    alpha=np.array(high.resize(tuple(size),Image.Resampling.LANCZOS))
    key=hashlib.sha256(alpha.tobytes()+obj['material'].encode()+str(tuple(size)).encode()).hexdigest()[:16]
    # Eight central wedges are rotations of the same original fabrication.
    # Use the same canonical bake after checking their oriented bounds.
    if circular and 'circle' in cache:
        ref=cache['circle']
        assert np.max(np.abs(span-ref['span']))<.0002
        key=ref['key']
    elif circular:
        cache['circle']={'key':key,'span':span}
    if key not in cache:
        mask=alpha>127
        dist=distance_transform_edt(mask, sampling=(span[1]/size[1],span[0]/size[0]))
        # A restrained rounded shoulder, roughly matching the old 0.8 mm bevel.
        bevel=.00085 if circular else .0006
        h=np.minimum(dist,bevel)
        h=gaussian_filter(h,.55)
        gy,gx=np.gradient(h,span[1]/size[1],span[0]/size[0])
        normal=np.dstack((-gx,-gy,np.ones_like(gx)))
        normal/=np.linalg.norm(normal,axis=2,keepdims=True)
        normal=(np.clip(normal*.5+.5,0,1)*255).round().astype(np.uint8)
        rgb=(srgb(np.array(colors[obj['material']]))*255).round().astype(np.uint8)
        rgba=np.empty((*alpha.shape,4),dtype=np.uint8)
        rgba[:,:,:3]=rgb;rgba[:,:,3]=alpha
        Image.fromarray(rgba[::-1]).save(OUT/(key+'-color.png'),optimize=True)
        Image.fromarray(normal[::-1]).save(OUT/(key+'-normal.png'),optimize=True)
        cache[key]={'size':size.tolist(),'uses':0}
    cache[key]['uses']+=1

    # Curved strips keep the central opening empty even in solid viewport mode.
    if circular:
        a=sector*math.pi/4+(.075 if sector%2 else .020)
        b=(sector+1)*math.pi/4-(.075 if (sector+1)%2 else .020)
        pts=np.array([(r*math.cos(t),r*math.sin(t)) for t in np.linspace(a,b,19)
                      for r in (1.327,2.255)])
        faces=[(i*2,i*2+1,i*2+3,i*2+2) for i in range(18)]
        verts=np.column_stack((pts,np.full(len(pts),v[:,2].max())))
    else:
        hull=ConvexHull(np.round(q,6))
        border=q[hull.vertices]
        if bridge:
            # Preserve the slight slope and live endpoint deformation, rather
            # than flattening this bridge onto a single horizontal card.
            us=np.linspace(q[:,0].min(),q[:,0].max(),20)
            vs=np.linspace(q[:,1].min(),q[:,1].max(),9)
            candidates=np.array([(u,w) for u in us for w in vs])
            inside=np.all(candidates@hull.equations[:,:2].T+hull.equations[:,2]<=1e-7,axis=1)
            points=np.unique(np.round(np.vstack((border,candidates[inside])),6),axis=0)
            faces=[tuple(f) for f in Delaunay(points).simplices]
            T=math.sqrt(3.620207**2-.67**2)
            z=6.871178627+(6.824491024-6.871178627)*np.clip((points[:,0]-T)/1.12,0,1)-.004
        else:
            points=border
            faces=[tuple(range(len(points)))]
            z=np.full(len(points),v[:,2].max())
        verts=np.column_stack((points@basis.T,z))
    # Boolean cutters need a closed volume. A sub-millimeter sheet maintains
    # their curved live joints; the rest of the grates are single surfaces.
    closed=any(m['type']=='BOOLEAN' for m in obj['mods'])
    if closed:
        from collections import Counter
        edges=Counter(tuple(sorted((f[i],f[(i+1)%len(f)]))) for f in faces for i in range(len(f)))
        directed={(min(f[i],f[(i+1)%len(f)]),max(f[i],f[(i+1)%len(f)])):(f[i],f[(i+1)%len(f)]) for f in faces for i in range(len(f))}
        count=len(verts)
        verts=np.vstack((verts,verts-np.array([0,0,.0008])))
        faces=faces+[tuple(i+count for i in reversed(f)) for f in faces]
        for edge,n in edges.items():
            if n==1:
                i,j=directed[edge]
                faces.append((j,i,i+count,j+count))
    uv=(verts[:,:2]@basis-lo)/span
    attributes={}
    if bridge:
        from scipy.interpolate import LinearNDInterpolator, NearestNDInterpolator
        for attr,values in obj['attributes'].items():
            # These weights vary in the span plane, never through bar thickness.
            unique,ind=np.unique(np.round(q,6),axis=0,return_index=True)
            data=np.array(values)[ind]
            qq=verts[:,:2]@basis
            values=LinearNDInterpolator(unique,data)(qq)
            nan=np.isnan(values)
            values[nan]=NearestNDInterpolator(unique,data)(qq[nan])
            attributes[attr]=values.tolist()
    records.append({'name':name,'texture':key,'vertices':verts.tolist(),'faces':[[int(i) for i in f] for f in faces],
                    'uv':uv.tolist(),'attributes':attributes,'material':obj['material'],
                    'before_triangles':obj['before_evaluated_triangles']})

(P/'replacement-geometry.json').write_text(json.dumps(records))
textures={k:v for k,v in cache.items() if k!='circle'}
for path in OUT.glob('*.png'):
    if path.name.split('-')[0] not in textures:
        path.unlink()
(P/'texture-manifest.json').write_text(json.dumps(textures,indent=2))
print(json.dumps({'objects':len(records),'textures':len(textures),
                  'texels':sum(v['size'][0]*v['size'][1] for v in textures.values()),
                  'file_bytes':sum(p.stat().st_size for p in OUT.glob('*.png'))}))
