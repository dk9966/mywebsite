exec(compile(open('/Users/danielku/mywebsite/secret-base/refine_wired_depth.py').read().split('# Remove unsupported')[0],'helpers','exec'))
# Match the first reference's asymmetrical platform arrangement.
centers={k:bpy.data.objects['island_pillar_'+k].matrix_world.translation.copy() for k in ['contact','experience','project','about']}
forward=Vector((D.x,D.y,0)).normalized()
moves={'contact':R*-1.6,'experience':R*.8+forward*2.4}
for key,delta in moves.items():
 root=bpy.data.objects['island_pillar_'+key]
 root.location+=delta
 support=bpy.data.objects['Cave | bedrock foundation island_pillar_'+key];support.location+=delta
 for o in bpy.data.objects:
  if o.name=='Pillar | fine raised stone '+key and not o.parent:o.location+=delta
 # Deform connected bridge smoothly between fixed central deck and translated satellite.
 a=centers['project'];b=centers[key];direction=b-a;direction.z=0;length=direction.length;direction.normalize()
 def warp(v):
  t=max(0,min(1,((v-a).dot(direction)-2.9)/max(.7,length-5.0)));t=t*t*(3-2*t);return v+delta*t
 for o in bpy.data.collections['bridge_project_'+key].objects:
  mw=o.matrix_world.copy();im=mw.inverted()
  if o.type=='MESH':
   if o.data.users>1:o.data=o.data.copy()
   for v in o.data.vertices:v.co=im@warp(mw@v.co)
   o.data.update()
  elif o.type=='CURVE':
   if o.data.users>1:o.data=o.data.copy()
   for sp in o.data.splines:
    for v in sp.points:v.co=(*(im@warp(mw@Vector(v.co[:3]))),v.co.w)
  elif o.type=='LIGHT':o.matrix_world.translation=warp(mw.translation)
# Translate individual supporting blocks with their original nearest pedestal.
for o in col.objects:
 if o.type!='MESH' or not any(k in o.name for k in ['embedded short basalt block','footing cap rubble','broad oblique basalt fracture']):continue
 center=sum((o.matrix_world@v.co for v in o.data.vertices),Vector())/len(o.data.vertices)
 key=min(centers,key=lambda k:(Vector((center.x,center.y,0))-Vector((centers[k].x,centers[k].y,0))).length)
 if key in moves:o.location+=moves[key]
for o in col.objects:
 if o.type=='LIGHT' and 'near frame rim' in o.name:o.data.energy=450
# Clear the left industrial landing of an obsolete displaced threshold line.
for o in col.objects:
 if o.type=='CURVE' and 'luminous threshold' in o.name:
  pts=[Vector(pt.co[:3]) for pt in o.data.splines[0].points]
  if sum((v-C).dot(R) for v in pts)/len(pts)<0:o.hide_render=True
s.render.resolution_percentage=100;s.eevee.taa_render_samples=96
s.render.filepath='/Users/danielku/mywebsite/secret-base/wired-review/iteration-12.png'
bpy.ops.wm.save_as_mainfile(filepath='/Users/danielku/mywebsite/secret-base/base.blend')
