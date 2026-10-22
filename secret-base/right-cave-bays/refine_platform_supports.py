"""Bring the garage's rock face forward and build seated industrial brackets."""
import argparse, ast, json, math, sys
from pathlib import Path
import bpy, bmesh
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

P=Path(__file__).resolve().parent
FRAME=Matrix.Translation((21.299999237,0,0))@Matrix.Rotation(-math.atan2(12,19),4,'Z')
INV=FRAME.inverted()

def smooth(a,b,x):
    t=max(0.,min(1.,(x-a)/(b-a)))
    return t*t*(3-2*t)

def cave_tree(objects):
    vs=[];fs=[]
    for ob in objects:
        offset=len(vs);local=INV@ob.matrix_world
        vs.extend(local@v.co for v in ob.data.vertices)
        fs.extend(tuple(i+offset for i in p.vertices) for p in ob.data.polygons)
    return BVHTree.FromPolygons(vs,fs)

def apply_support_revision(scene,layout=None):
    if scene.get('engineered_supports_revision'):
        return json.loads(scene['engineered_supports_revision'])
    audit=layout or json.loads((P/'right-bays-audit.json').read_text())
    lp=[Vector(p) for p in audit['lower_floor_polygon']];Z=audit['lower_floor_height']
    rear0,rear1=lp[2],lp[3];u=(rear1-rear0).normalized();v=Vector((-u.y,u.x));origin=(rear0+rear1)/2
    rock_objects=[o for o in bpy.data.collections['07 | Continuous approved-style cave wall'].objects if o.type=='MESH']
    # Bake only new cave volumes, leaving all approved central geometry intact.
    dg=bpy.context.evaluated_depsgraph_get()
    baked=[]
    for ob in rock_objects:
        me=bpy.data.meshes.new_from_object(ob.evaluated_get(dg));transform=INV@ob.matrix_world
        for vertex in me.vertices:vertex.co=transform@vertex.co
        baked.append((ob,me))
    for ob,me in baked:ob.modifiers.clear();ob.data=me;ob.matrix_world=FRAME
    before=cave_tree(rock_objects)
    points=[]
    for edge in range(6,9):
        aa,bb=lp[edge],lp[edge+1];along=(bb-aa).normalized();inside=Vector((along.y,-along.x,0))
        for t in [.22,.76]:
            tip=aa.lerp(bb,t);hit=before.ray_cast(Vector((*tip,Z-1.04)),inside,8)
            points.append({'edge':edge,'t':t,'tip':tip,'side':Vector((*along,0)),'inside':inside,'old_gap':hit[3]})
    front=[((q-origin).dot(u),(q-origin).dot(v)) for q in lp[6:10]]
    front.sort();xlo,xhi=front[0][0]-.20,front[-1][0]+.20
    movable=[ob for ob in rock_objects if 'forward right cave wall' not in ob.name]
    original=cave_tree(movable)
    def interp(pairs,x):
        if x<=pairs[0][0]:return pairs[0][1]
        for (xa,ya),(xb,yb) in zip(pairs,pairs[1:]):
            if x<=xb:return ya+(yb-ya)*(x-xa)/max(1e-6,xb-xa)
        return pairs[-1][1]
    shifts=[];fronts=[]
    for j in range(23):
        xx=xlo+(xhi-xlo)*j/22
        start=origin+u*xx-v*12
        hit=original.ray_cast(Vector((*start,Z-1.10)),Vector((*v,0)),24)
        if hit[0] is None:continue
        old_y=(hit[0].xy-origin).dot(v);wanted_y=interp(front,xx)+.74
        shifts.append((xx,max(0.,min(7.0,old_y-wanted_y))))
        fronts.append((xx,old_y))
    if not shifts:raise RuntimeError('No rock surface found beneath garage')
    shift=max(d for _,d in shifts)
    moved=0
    for ob in rock_objects:
        if 'forward right cave wall' in ob.name:continue
        for vertex in ob.data.vertices:
            p=vertex.co;xy=p.xy-origin;xx=xy.dot(u);yy=xy.dot(v)
            wz=1-smooth(Z-.36,Z-.10,p.z)
            wx=smooth(xlo-.9,xlo,xx)*(1-smooth(xhi,xhi+.9,xx))
            old_front=interp(fronts,xx)
            wy=1-smooth(old_front+.75,old_front+5.0,yy)
            delta=interp(shifts,xx)*wz*wx*wy
            if delta>1e-5:p.x-=v.x*delta;p.y-=v.y*delta;moved+=1
        ob.data.update()
    tree=cave_tree(rock_objects)
    for ob in list(scene.objects):
        if any(key in ob.name for key in ['Garage | apron underside edge girder','Garage | rock-anchored diagonal bracket','Garage | rock-anchored horizontal bracket']):
            bpy.data.objects.remove(ob,do_unlink=True)
    col=bpy.data.collections.new('12 | Engineered garage cantilever brackets');scene.collection.children.link(col)
    steel=bpy.data.materials['Metal | satin blue steel'];dark=bpy.data.materials['Metal | dark structural steel'];trim=bpy.data.materials['Metal | machined edge highlights'];panel=bpy.data.materials['Metal | outer walkway alloy']
    ns={'bpy':bpy,'bmesh':bmesh,'math':math,'Matrix':Matrix,'Vector':Vector,'FRAME':FRAME,'DECK':col}
    source=ast.parse((P.parent/'central-metal-platform/build_metal_platform.py').read_text())
    exec(compile(ast.Module(body=[n for n in source.body if isinstance(n,ast.FunctionDef) and n.name in {'mesh','box','cylinder'}],type_ignores=[]),'support_geometry','exec'),ns)
    mesh,box,cylinder=ns['mesh'],ns['box'],ns['cylinder']
    def oriented_box(name,center,size,xx,yy,zz,ma=steel):
        ob=box('Support | '+name,(0,0,0),size,ma,col,bevel=.002)
        basis=Matrix((xx,yy,zz)).transposed().to_4x4();ob.matrix_world=FRAME@Matrix.Translation(center)@basis
        return ob
    def ibeam(name,p,q,side,width=.15,depth=.18,flange=.020):
        axis=(q-p).normalized();sx=(side-axis*side.dot(axis)).normalized();sy=axis.cross(sx).normalized();center=(p+q)/2;length=(q-p).length
        oriented_box(name+' web',center,(.022,depth-flange*2,length),sx,sy,axis,dark)
        for sign in [-1,1]:oriented_box(name+' flange',center+sy*sign*(depth/2-flange/2),(width,flange,length),sx,sy,axis,steel)
    def plate(name,poly,side,thick=.020):
        n=len(poly);vs=[tuple(p+side*offset) for offset in [-thick/2,thick/2] for p in poly]
        faces=[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
        return mesh('Support | '+name,vs,faces,steel,col,.002)
    def bolt(name,point,axis,radius=.020):
        cylinder('Support | '+name+' washer',point,radius*1.4,.007,dark,col,axis,16)
        cylinder('Support | '+name+' hex nut',point+axis*.011,radius,.018,trim,col,axis,6)
    # A continuous, deep I-section edge girder receives every joist.
    for edge in range(6,9):
        aa,bb=lp[edge],lp[edge+1];p=Vector((*aa,Z-.47));q=Vector((*bb,Z-.47))
        along=(bb-aa).normalized();cross=Vector((along.y,-along.x,0))
        ibeam('apron edge girder',p,q,cross,width=.15,depth=.22)
    contacts=[]
    for index,entry in enumerate(points):
        side,inside=entry['side'],entry['inside'];tip=Vector((*entry['tip'],Z-.46));probe=Vector((*entry['tip'],Z-1.10))
        hit=tree.ray_cast(probe,inside,8)
        if hit[0] is None:raise RuntimeError('No rock anchor found for garage bracket %d'%index)
        rock_point=hit[0];anchor=rock_point-inside*.018
        upper=Vector((anchor.x,anchor.y,Z-.46));lower=Vector((anchor.x,anchor.y,Z-1.10))
        # Substantial horizontal seat and diagonal compression strut.
        ibeam('bracket %d underside joist'%index,tip,upper+inside*.15,side,.15,.16)
        ibeam('bracket %d diagonal'%index,tip-Vector((0,0,.08)),lower,side,.15,.14)
        # Vertical bearing plate and grout seat bridge the rough rock surface.
        mid=(upper+lower)/2
        oriented_box('bracket %d grout seat'%index,mid+inside*.080,(.33,.20,.85),side,inside,Vector((0,0,1)),dark)
        oriented_box('bracket %d rock anchor plate'%index,mid-inside*.045,(.28,.055,.81),side,inside,Vector((0,0,1)),panel)
        for dx in [-.092,.092]:
            for dz in [-.305,.305]:bolt('rock anchor',mid+side*dx+Vector((0,0,dz))-inside*.082,-inside,.024)
        # Paired triangular gussets and through-bolts at the front knee.
        for sign in [-1,1]:
            c=tip+side*sign*.086
            plate('bracket %d upper gusset'%index,[c+inside*.025+Vector((0,0,.02)),c+inside*.32+Vector((0,0,.02)),c+inside*.28-Vector((0,0,.22))],side)
            for xy in [(.11,-.01),(.255,-.01),(.245,-.13)]:bolt('gusset fastener',c+inside*xy[0]+Vector((0,0,xy[1]))+side*sign*.014,side*sign,.015)
            c=lower+side*sign*.086
            plate('bracket %d lower gusset'%index,[c-inside*.01-Vector((0,0,.055)),c-inside*.01+Vector((0,0,.23)),c-inside*.24+Vector((0,0,.16))],side)
            for dz in [.025,.15]:bolt('lower clevis',c-inside*.06+Vector((0,0,dz))+side*sign*.014,side*sign,.017)
        contacts.append({'bracket':index,'original_rock_gap':entry['old_gap'],'final_rock_gap':hit[3],'rock_anchor':list(rock_point),'bearing_embed_depth':.18})
    # Low-level light reveals the structural profiles without adding neon.
    ld=bpy.data.lights.new('Bays | underside reflected cool fill','AREA');ld.energy=55;ld.shape='RECTANGLE';ld.size=3.4;ld.size_y=1.3;ld.color=(.52,.65,.78)
    lo=bpy.data.objects.new(ld.name,ld);bpy.data.collections['10 | Wide perspective camera and cave practicals'].objects.link(lo)
    focus=Vector((*((lp[6]+lp[9])/2),Z-.85));position=focus-Vector((*v,0))*3+Vector((0,0,.3))
    lo.location=FRAME@position;lo.rotation_euler=(FRAME@focus-lo.location).to_track_quat('-Z','Y').to_euler()
    report={'maximum_rock_forward_displacement':shift,'rock_face_offset_profile':shifts,'moved_rock_vertices':moved,'brackets':contacts,'approved_center_unchanged':True}
    scene['engineered_supports_revision']=json.dumps(report)
    (P/'support-connections.json').write_text(json.dumps(report,indent=2))
    return report

def render_support_closeup(scene,path,samples=64):
    audit=json.loads((P/'right-bays-audit.json').read_text())
    lp=[Vector(p) for p in audit['lower_floor_polygon']];Z=audit['lower_floor_height']
    mid=(lp[6]+lp[9])/2;edge=(lp[9]-lp[6]).normalized();inside=Vector((edge.y,-edge.x))
    target=Vector((*(mid+inside*.45),Z-.80))
    position=Vector((*(mid-inside*5.1+edge*3.3),Z-.15))
    camera=bpy.data.objects.get('Bays | lower support inspection camera')
    if camera is None:
        camera=bpy.data.objects.new('Bays | lower support inspection camera',bpy.data.cameras.new('Bays | lower support inspection camera'))
        bpy.data.collections['10 | Wide perspective camera and cave practicals'].objects.link(camera)
    camera.location=FRAME@position;camera.rotation_euler=(FRAME@target-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.type='PERSP';camera.data.lens=48;camera.data.sensor_width=36
    old=(scene.camera,scene.render.resolution_x,scene.render.resolution_y,scene.render.use_border,scene.render.use_crop_to_border,scene.render.filepath,scene.cycles.samples)
    scene.camera=camera;scene.render.resolution_x=1400;scene.render.resolution_y=1050;scene.render.use_border=False;scene.render.use_crop_to_border=False;scene.render.filepath=str(path);scene.cycles.samples=samples
    bpy.ops.render.render(write_still=True)
    scene.camera,scene.render.resolution_x,scene.render.resolution_y,scene.render.use_border,scene.render.use_crop_to_border,scene.render.filepath,scene.cycles.samples=old

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--final',action='store_true');args=ap.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    bpy.ops.wm.open_mainfile(filepath=str(P/'preview-supports-base.blend'));bpy.context.preferences.filepaths.save_version=0
    S=bpy.context.scene;report=apply_support_revision(S);print('SUPPORT_REVISION',json.dumps(report),flush=True)
    if args.final:
        audit=json.loads((P/'right-bays-audit.json').read_text());audit['engineered_supports']=report
        audit['terrain_source']='Approved connected pillar rock, baked to editable cave meshes with the lower garage bearing face advanced toward the cantilever brackets'
        (P/'right-bays-audit.json').write_text(json.dumps(audit,indent=2))
    for name in ['build_right_bays.py','refine_platform_supports.py']:
        for text in list(bpy.data.texts):
            if text.name.startswith(name):bpy.data.texts.remove(text)
        text=bpy.data.texts.new(name);text.write((P/name).read_text())
    prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='METAL';prefs.get_devices()
    for dev in prefs.devices:dev.use=(dev.type=='METAL')
    S.cycles.device='GPU';S.cycles.samples=64 if args.final else 24
    width=2000 if args.final else 1500;S.render.resolution_x=width;S.render.resolution_y=round(width*654/1199);S.render.use_border=False;S.render.use_crop_to_border=False
    tag='right-bays' if args.final else 'preview-supports';out=P/('central-pillar-right-cave-bays.blend' if args.final else tag+'.blend')
    S.render.filepath=str(P/(tag+'-overview.png'));bpy.ops.wm.save_as_mainfile(filepath=str(out),compress=True);bpy.ops.render.render(write_still=True)
    S.render.resolution_x=2400;S.render.resolution_y=round(2400*654/1199);S.render.use_border=True;S.render.use_crop_to_border=True
    S.render.border_min_x=.667;S.render.border_max_x=1.;S.render.border_min_y=.06;S.render.border_max_y=.99;S.render.filepath=str(P/(tag+'-detail.png'));bpy.ops.render.render(write_still=True)
    S.render.use_border=False;S.render.use_crop_to_border=False;S.render.resolution_x=width;S.render.resolution_y=round(width*654/1199);S.render.filepath=str(P/(tag+'-overview.png'))
    render_support_closeup(S,P/(tag+'-supports.png'),64 if args.final else 24)
    bpy.ops.wm.save_as_mainfile(filepath=str(out),compress=True)
