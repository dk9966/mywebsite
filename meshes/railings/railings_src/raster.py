"""A small software PBR rasteriser, used to check the asset without a GPU.

It is deliberately faithful about the things that matter for judging a
material: tangent-space normal mapping, GGX specular, and a cheap analytic
environment for reflections. An earlier version skipped normal mapping, which
made previews look far cleaner than the real asset -- hence the care here.

This is the bridge's module with one addition: a material may now carry a
constant ``flat_emis`` instead of a ``lut``. The bridge had no light sources,
so every emissive surface in it was an edge highlight driven by the UV1 lookup
table and the ``lut is None`` branch simply meant "not emissive". This kit has
lenses -- flat glowing blocks with no falloff -- and without this branch they
would render as unlit dark boxes, which is exactly the class of lying preview
this file exists to prevent.
"""
import numpy as np

def env(d, sun=np.array([0.55,0.62,0.42])):
    """cheap analytic environment: cool sky above, dark floor below, one sun blob"""
    s=sun/np.linalg.norm(sun)
    up=np.clip(d[...,1],-1,1)
    sky=np.stack([0.055+0.10*np.clip(up,0,1), 0.075+0.13*np.clip(up,0,1), 0.115+0.19*np.clip(up,0,1)],-1)
    grnd=np.stack([0.020+0*up,0.021+0*up,0.026+0*up],-1)
    e=np.where((up>0)[...,None],sky,grnd)
    cs=np.clip(d@s,0,1)
    e=e+ (cs**320)[...,None]*np.array([4.2,3.9,3.4]) + (cs**14)[...,None]*np.array([0.30,0.29,0.26])
    d2=d.copy(); d2[...,1]*=-1
    cs2=np.clip(d2@s,0,1)
    e=e+(cs2**40)[...,None]*np.array([0.05,0.055,0.07])
    return e

ENV_AVG=np.array([0.055,0.068,0.092])

def render(pos, idx, uv0, uv1, matid, mats, tang=None, vnorm=None, W=520,H=900,
           cam=(7,4.2,8.5), tgt=(0,3.0,0), fov=26.0, bg=(0.045,0.05,0.062), exposure=1.0):
    cam=np.array(cam,float); tgt=np.array(tgt,float)
    f=tgt-cam; f/=np.linalg.norm(f)
    r=np.cross(f,[0,1,0]); r/=np.linalg.norm(r); u=np.cross(r,f)
    M=np.stack([r,u,-f])
    V=(pos-cam)@M.T; z=-V[:,2]
    fl=1.0/np.tan(np.radians(fov)/2)
    S=np.stack([(V[:,0]*fl/np.maximum(z,1e-6))*(H/2)+W/2,
                (-V[:,1]*fl/np.maximum(z,1e-6))*(H/2)+H/2, z],1)
    tri=S[idx]; wtri=pos[idx]
    n=np.cross(wtri[:,1]-wtri[:,0],wtri[:,2]-wtri[:,0]); n/=np.linalg.norm(n,axis=1,keepdims=True)+1e-12
    L=np.array([0.55,0.62,0.42]); L/=np.linalg.norm(L)
    LC=np.array([2.55,2.42,2.15])
    L2=np.array([-0.62,0.30,-0.55]); L2/=np.linalg.norm(L2); LC2=np.array([0.16,0.20,0.34])
    zb=np.full((H,W),1e9); cb=np.zeros((H,W,3)); cb[:]=bg
    for t in np.argsort(-tri[:,:,2].mean(1)):
        p=tri[t]
        if np.any(p[:,2]<=0.05): continue
        a=(p[1,0]-p[0,0])*(p[2,1]-p[0,1])-(p[2,0]-p[0,0])*(p[1,1]-p[0,1])
        if a>=0: continue
        x0=max(int(np.floor(p[:,0].min())),0); x1=min(int(np.ceil(p[:,0].max()))+1,W)
        y0=max(int(np.floor(p[:,1].min())),0); y1=min(int(np.ceil(p[:,1].max()))+1,H)
        if x1<=x0 or y1<=y0: continue
        X,Y=np.meshgrid(np.arange(x0,x1)+.5,np.arange(y0,y1)+.5)
        w0=((p[1,0]-p[0,0])*(Y-p[0,1])-(X-p[0,0])*(p[1,1]-p[0,1]))/a
        w1=((X-p[0,0])*(p[2,1]-p[0,1])-(p[2,0]-p[0,0])*(Y-p[0,1]))/a
        w2=1-w0-w1
        m=(w0>=-1e-6)&(w1>=-1e-6)&(w2>=-1e-6)
        if not m.any(): continue
        zz=w2*p[0,2]+w1*p[1,2]+w0*p[2,2]
        sub=zb[y0:y1,x0:x1]; m&= zz<sub
        if not m.any(): continue
        mat=mats[matid[t]]; N=n[t]
        Tg=None
        if tang is not None and mat.get('nrm') is not None:
            tv=tang[idx[t,0]]
            Tg=tv[:3]-N*(tv[:3]@N); Tg/=np.linalg.norm(Tg)+1e-12
            Bt=np.cross(N,Tg)*tv[3]
        wp=(w2[...,None]*wtri[t,0]+w1[...,None]*wtri[t,1]+w0[...,None]*wtri[t,2])
        Vd=cam-wp; Vd/=np.linalg.norm(Vd,axis=-1,keepdims=True)
        def samp(T,uu,vv,wrap=True):
            th,tw=T.shape[:2]
            uu=uu%1.0 if wrap else np.clip(uu,0,1); vv=vv%1.0 if wrap else np.clip(vv,0,1)
            return T[np.clip(((1-vv)*th).astype(int),0,th-1),np.clip((uu*tw).astype(int),0,tw-1)]
        t0=uv0[idx[t]]
        uu=w2*t0[0,0]+w1*t0[1,0]+w0*t0[2,0]; vv=w2*t0[0,1]+w1*t0[1,1]+w0*t0[2,1]
        alb=samp(mat['base'],uu,vv)
        orm=samp(mat['orm'],uu,vv)
        rough=np.clip(orm[...,1],0.05,1.0); ao=orm[...,0]
        # interpolate the shading normal; falls back to the flat face normal
        if vnorm is not None:
            vn = vnorm[idx[t]]
            Nsm = (w2[...,None]*vn[0] + w1[...,None]*vn[1] + w0[...,None]*vn[2])
            Nsm = Nsm/(np.linalg.norm(Nsm,axis=-1,keepdims=True)+1e-12)
        else:
            Nsm = None
        if Tg is not None:
            tn=samp(mat['nrm'],uu,vv)*2.0-1.0
            tn[...,:2]*=mat.get('nscale',1.0)
            base = Nsm if Nsm is not None else np.broadcast_to(N, wp.shape)
            Ns=(tn[...,0:1]*Tg[None,None,:]+tn[...,1:2]*Bt[None,None,:]+tn[...,2:3]*base)
            Ns/=np.linalg.norm(Ns,axis=-1,keepdims=True)+1e-12
        elif Nsm is not None:
            Ns=Nsm
        else:
            Ns=np.broadcast_to(N,wp.shape)
        NdL=np.clip(Ns@L,0,1)[...,None]; NdL2=np.clip(Ns@L2,0,1)[...,None]
        NdV=np.clip(np.sum(Vd*Ns,-1,keepdims=True),1e-4,1)
        out=alb*(NdL*LC[None,None,:]+NdL2*LC2[None,None,:])/np.pi*2.6
        # analytic specular (GGX) for the two lights
        for Ldir,Lc,nd in ((L,LC,NdL),(L2,LC2,NdL2)):
            Hv=Ldir+Vd; Hv/=np.linalg.norm(Hv,axis=-1,keepdims=True)
            NdH=np.clip(np.sum(Hv*Ns,-1,keepdims=True),0,1)
            VdH=np.clip(np.sum(Hv*Vd,-1,keepdims=True),1e-4,1)
            r2=rough[...,None]; al=r2**2; al2=al*al
            D=al2/(np.pi*((NdH**2*(al2-1)+1)**2)+1e-9)
            k=al/2
            G=(nd/(nd*(1-k)+k+1e-9))*(NdV/(NdV*(1-k)+k+1e-9))
            F=0.04+0.96*(1-VdH)**5
            spec=D*G*F*nd/(4*np.maximum(NdV,1e-4)+1e-9)
            out=out+spec*Lc[None,None,:]
        # image-based-ish reflection
        R=2*np.sum(Vd*Ns,-1,keepdims=True)*Ns-Vd
        e=env(R)
        e=e*(1-rough[...,None])+ENV_AVG*rough[...,None]*1.0
        Fv=0.04+0.96*(1-NdV)**5
        out=out+e*Fv*ao[...,None]
        out=out+alb*ENV_AVG[None,None,:]*ao[...,None]*3.0
        if mat.get('lut') is not None:
            t1=uv1[idx[t]]
            e1=w2*t1[0,0]+w1*t1[1,0]+w0*t1[2,0]; e2=w2*t1[0,1]+w1*t1[1,1]+w0*t1[2,1]
            lv=samp(mat['lut'],np.clip(e1,0,1),1-np.clip(e2,0,1),wrap=False)
            out=out+lv*np.array(mat['emis'])[None,None,:]
        elif mat.get('flat_emis') is not None:
            out=out+np.asarray(mat['flat_emis'])[None,None,:]
        sub[m]=zz[m]; zb[y0:y1,x0:x1]=sub
        reg=cb[y0:y1,x0:x1]; reg[m]=out[m]; cb[y0:y1,x0:x1]=reg
    img=np.clip(cb*exposure,0,None)
    img=img*(1+img/0.36)/(1+img)          # filmic-ish
    return (np.clip(img,0,1)**(1/2.2)*255).astype(np.uint8)
