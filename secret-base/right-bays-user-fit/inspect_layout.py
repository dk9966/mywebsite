import bpy,json,math,numpy as np
from pathlib import Path
from mathutils import Matrix
P=Path(__file__).resolve().parent
FRAME=Matrix.Translation((21.299999237,0,0))@Matrix.Rotation(-math.atan2(12,19),4,'Z');INV=FRAME.inverted()
def capture():
    out={}
    for ob in bpy.context.scene.objects:
        if ob.type=='MESH':
            out[ob.name]={'points':np.array([tuple(INV@(ob.matrix_world@v.co)) for v in ob.data.vertices]),'matrix':np.array(ob.matrix_world)}
        elif ob.type in {'LIGHT','CAMERA','EMPTY'}:out[ob.name]={'matrix':np.array(ob.matrix_world)}
    return out
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'right-bays-rock-ledge/preview-ledge.blend'));before=capture()
bpy.ops.wm.open_mainfile(filepath=str(P/'user-layout-snapshot.blend'));after=capture()
changes=[]
for name,a in after.items():
    if name not in before:changes.append({'name':name,'new':True});continue
    b=before[name]
    if 'points' in a and a['points'].shape==b['points'].shape:
        dif=a['points']-b['points'];delta=dif.mean(axis=0);err=float(np.linalg.norm(dif-delta,axis=1).max())
        if np.linalg.norm(dif,axis=1).max()>1e-5:changes.append({'name':name,'shift':delta.tolist(),'non_translation_error':err})
    elif np.max(abs(a['matrix']-b['matrix']))>1e-5:changes.append({'name':name,'matrix_before':b['matrix'].tolist(),'matrix_after':a['matrix'].tolist()})
summary={'changes':changes,'removed':[name for name in before if name not in after],'floor_vertices':{name:after[name]['points'].tolist() for name in ['Lower | continuous floor footprint','Upper | continuous floor footprint']}}
(P/'user-layout-diff.json').write_text(json.dumps(summary,indent=2))
groups={}
for c in changes:
    key=str([round(x,4) for x in c.get('shift',[])])+':'+str(round(c.get('non_translation_error',0),4))
    groups.setdefault(key,[]).append(c['name'])
print('DIFF_GROUPS',json.dumps({k:{'count':len(v),'examples':v[:8]} for k,v in groups.items()}),flush=True)
print('REMOVED',summary['removed'],flush=True)
