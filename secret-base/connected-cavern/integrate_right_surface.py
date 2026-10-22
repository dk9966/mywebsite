"""Keep the original right rock's exposed faces and weld the cave into one skin.

Manifold booleans split/intersect existing polygons without voxel remeshing.
A temporary back skin closes only the new sheet for joining, then is removed.
"""
import json,math,heapq
from pathlib import Path
import bpy,bmesh
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree

P=Path(__file__).resolve().parent
FRAME=Matrix.Translation((21.299999237,0,0))@Matrix.Rotation(-math.atan2(12,19),4,'Z');INV=FRAME.inverted()

def apply(ob,mod):
    bpy.context.view_layer.objects.active=ob;ob.hide_set(False);bpy.ops.object.modifier_apply(modifier=mod.name)

def union(ob,other):
    mod=ob.modifiers.new('Preserve exact polygon shapes at seam','BOOLEAN');mod.operation='UNION';mod.solver='MANIFOLD';mod.object=other
    apply(ob,mod);bpy.data.objects.remove(other,do_unlink=True)
    print('SHARP_UNION',len(ob.data.vertices),flush=True)

def components(bm):
    seen=set();parts=[]
    for v in bm.verts:
        if v in seen:continue
        seen.add(v);todo=[v];part=[]
        while todo:
            p=todo.pop();part.append(p)
            for e in p.link_edges:
                q=e.other_vert(p)
                if q not in seen:seen.add(q);todo.append(q)
        parts.append(part)
    return sorted(parts,key=len,reverse=True)

def connect_retained_faces(bm,keep,materials):
    """Connect exposed patches through the existing surface's hidden folds.

    Multi-source shortest paths favor inward faces and avoid outside planes.
    This retains original polygons instead of fabricating a smoothed patch.
    """
    bm.faces.ensure_lookup_table();bm.faces.index_update();faces=list(bm.faces);groups=[];unseen=set(keep)
    while unseen:
        start=unseen.pop();todo=[start];group=[start]
        while todo:
            f=todo.pop()
            for e in f.edges:
                for other in e.link_faces:
                    if other in unseen:unseen.remove(other);todo.append(other);group.append(other)
        groups.append(group)
    if len(groups)<2:return 0
    count=len(faces);dist=[float('inf')]*count;owner=[-1]*count;parent=[-1]*count;cost=[];queue=[]
    for f in faces:
        role=materials[f.material_index].get('surface_role','')
        if role=='remove':cost.append(float('inf'));continue
        c=f.calc_center_median();r=max(.001,math.hypot(c.x,c.y));out=(f.normal.x*c.x+f.normal.y*c.y)/r
        penalty=1+max(0.,out)*20+(35 if abs(f.normal.z)>.85 and (c.z>13.5 or c.z<-4) else 0)
        cost.append(penalty)
    for label,group in enumerate(groups):
        for f in group:
            dist[f.index]=0;owner[f.index]=label;heapq.heappush(queue,(0,f.index))
    crossings=[]
    while queue:
        d,i=heapq.heappop(queue)
        if d!=dist[i]:continue
        f=faces[i]
        for edge in f.edges:
            for neighbor in edge.link_faces:
                j=neighbor.index
                if j==i or math.isinf(cost[j]):continue
                if owner[j]>=0 and owner[j]!=owner[i]:crossings.append((d+dist[j]+(cost[i]+cost[j])/2,i,j))
                nd=d+(cost[i]+cost[j])/2
                if nd<dist[j]:dist[j]=nd;owner[j]=owner[i];parent[j]=i;heapq.heappush(queue,(nd,j))
    leaders=list(range(len(groups)))
    def leader(i):
        while leaders[i]!=i:leaders[i]=leaders[leaders[i]];i=leaders[i]
        return i
    before=len(keep)
    for _,i,j in sorted(crossings):
        aa,bb=leader(owner[i]),leader(owner[j])
        if aa==bb:continue
        leaders[aa]=bb
        for index in [i,j]:
            while index>=0 and faces[index] not in keep:keep.add(faces[index]);index=parent[index]
    print('CONNECTED_EXISTING_FOLDS',len(groups),'patches',len(keep)-before,'faces',flush=True)
    return len(keep)-before

def integrate_surface(scene):
    new=bpy.data.objects.get('Cave | single interior wall surface') or bpy.data.objects.get('Cavern | single interior rock surface')
    if new is None:raise RuntimeError('No interior cave extension found')
    geo=new.users_collection[0]
    originals=list(bpy.data.collections['07 | Continuous approved-style cave wall'].objects)
    root=originals[0]
    for other in originals[1:]:union(root,other)
    # Source files can have an open sheet wound either way. Normalize only its
    # winding so temporary thickness is placed away from the chamber.
    bn=bmesh.new();bn.from_mesh(new.data);bmesh.ops.recalc_face_normals(bn,faces=list(bn.faces))
    score=sum(f.normal.x*f.calc_center_median().x+f.normal.y*f.calc_center_median().y for f in bn.faces if abs(f.normal.z)<.5)
    if score>0:bmesh.ops.reverse_faces(bn,faces=list(bn.faces))
    bn.to_mesh(new.data);bn.free()
    # Tag temporary faces so they can all be discarded after a welded seam is
    # made. The front material is an exact node copy of the original rock.
    front=new.data.materials[0].copy();front.name='Surface | original rock front';front['surface_role']='front'
    back=front.copy();back.name='Surface | temporary back';back['surface_role']='remove'
    rim=front.copy();rim.name='Surface | temporary rim';rim['surface_role']='remove'
    original_materials=list(root.data.materials);front_index=len(original_materials)
    new.data.materials.clear()
    for mat in original_materials+[front,back,rim]:new.data.materials.append(mat)
    for mat in [front,back,rim]:root.data.materials.append(mat)
    for face in new.data.polygons:face.material_index=front_index
    mod=new.modifiers.new('Temporary closure for seam intersection','SOLIDIFY');mod.thickness=.075;mod.offset=-1;mod.use_even_offset=True;mod.material_offset=1;mod.material_offset_rim=2
    apply(new,mod)
    union(root,new)
    # Every object in this scene already uses the same local cave frame.
    if root.matrix_world!=FRAME:
        T=INV@root.matrix_world
        for v in root.data.vertices:v.co=T@v.co
        root.matrix_world=FRAME
    bm=bmesh.new();bm.from_mesh(root.data);bm.faces.ensure_lookup_table();bm.verts.ensure_lookup_table()
    tree=BVHTree.FromBMesh(bm)
    origins=[Vector(p) for p in [(0,0,2),(0,0,6.9),(0,0,10.5),(0,-5,9),(-4,-4,8),(3,-4,8),(0,4,12),(-3,3,10),(6.2,-2.1,7.8),(7,-1.7,8.1),(9.5,5.2,10.7),(11.6,8.1,11.2),(8,3.5,10.2)]]
    origins+=[INV@ob.location for ob in scene.objects if ob.type=='CAMERA' and ob.data.type=='PERSP' and ob.name.startswith(('Interior |','Surface |'))]
    # Exclude any sample that accidentally lies inside a rock projection.
    origins=[p for p in origins if (lambda h: h[0] is not None and (p-h[0]).dot(h[1])>-.005)(tree.find_nearest(p))]
    keep=set();discard=[];counts={'front':0,'original_exposed':0,'exterior_removed':0}
    def visible(p,c,normal):
        v=p-c
        if normal.dot(v)<1e-6:return False
        distance=v.length
        if distance<1e-5:return True
        hit=tree.ray_cast(p,-v/distance,distance+.01)
        return hit[0] is not None and hit[3]>=distance-.008
    for i,face in enumerate(bm.faces):
        mat=root.data.materials[face.material_index];role=mat.get('surface_role','')
        if role=='front':keep.add(face);counts['front']+=1;continue
        if role=='remove':discard.append(face);counts['exterior_removed']+=1;continue
        c=face.calc_center_median();n=face.normal
        radial=Vector((0,0,c.z))
        # A small lateral offset reveals the risers between neighboring rock
        # steps. Horizontal ledges use actual interior viewpoints below the rim.
        test=visible(radial,c,n)
        if not test:
            direction=c-radial;distance=direction.length
            if distance>.001:
                hit=tree.ray_cast(radial,direction/distance,distance+.01)
                test=hit[0] is not None and hit[3]>=distance-.12
        if not test and abs(n.z)<.80:
            test=visible(radial+Vector((n.x,n.y,0))*.35,c,n)
        if not test:
            for p in origins:
                if visible(p,c,n):test=True;break
        if not test and face.calc_area()>.1:
            # Large clipped polygons can be partly visible while their center
            # is occluded. Preserve those exact faces conservatively.
            for vertex in face.verts:
                point=c.lerp(vertex.co,.65)
                if any(visible(p,point,n) for p in origins):test=True;break
        if test:keep.add(face);counts['original_exposed']+=1
        else:discard.append(face);counts['exterior_removed']+=1
    # Include hidden connecting folds surrounded by retained faces. They are
    # part of the inner surface, even if a tiny rock chip hides their centroid.
    for _ in range(2):
        added=[]
        for face in discard:
            if root.data.materials[face.material_index].get('surface_role','')=='remove':continue
            neighbors={f for edge in face.edges for f in edge.link_faces if f is not face}
            if len(neighbors)>=2 and sum(f in keep for f in neighbors)>=len(neighbors)-1:added.append(face)
        if not added:break
        keep.update(added);discard=[f for f in discard if f not in keep]
    added_connections=connect_retained_faces(bm,keep,root.data.materials)
    # Restore original folds enclosed by the selected interior skin. Visibility
    # sampling alone can miss a tiny crease behind a chip; that must not become
    # a puncture. The large outside region and temporary closure stay removed.
    remaining={f for f in bm.faces if f not in keep};filled=0;outside=[]
    while remaining:
        first=remaining.pop();part=[first];stack=[first]
        while stack:
            face=stack.pop()
            for edge in face.edges:
                for neighbor in edge.link_faces:
                    if neighbor in remaining:remaining.remove(neighbor);stack.append(neighbor);part.append(neighbor)
        temporary=any(root.data.materials[f.material_index].get('surface_role')=='remove' for f in part)
        area=sum(f.calc_area() for f in part)
        if not temporary and area<80:
            keep.update(part);filled+=len(part)
        else:outside.append((len(part),round(area,3),temporary))
    print('RESTORED_OCCLUDED_FOLDS',filled,'EXTERIOR_REGIONS',sorted(outside,reverse=True)[:8],flush=True)
    discard=[f for f in bm.faces if f not in keep]
    bmesh.ops.delete(bm,geom=discard,context='FACES')
    # Boolean seam vertices are already welded. A broad merge tolerance would
    # collapse fine folds in the source rock into nonmanifold edges.
    # Do not merge coincident vertices: the exact mesher deliberately splits
    # touching folds that would otherwise create four-face edges.
    parts=components(bm);part_sizes=[len(p) for p in parts]
    # The retained visible patches have already been connected above. Any
    # detached remainder restored by the hole pass is an enclosed cavity left
    # inside the original solid rocks, not part of the chamber wall.
    dust=[v for part in parts[1:] for v in part]
    if dust:bmesh.ops.delete(bm,geom=dust,context='VERTS')
    # Close small seam-only boundary loops. Leave the two long, intentionally
    # open upper/lower contours of the cave untouched.
    remaining={e for e in bm.edges if e.is_boundary};patches=0
    while remaining:
        first=remaining.pop();loop=[first];stack=[first]
        while stack:
            edge=stack.pop()
            for vertex in edge.verts:
                for neighbor in vertex.link_edges:
                    if neighbor in remaining:remaining.remove(neighbor);stack.append(neighbor);loop.append(neighbor)
        if len(loop)>100 or sum(e.calc_length() for e in loop)>5:continue
        neighbors=[f for e in loop for f in e.link_faces]
        result=bmesh.ops.holes_fill(bm,edges=loop,sides=0)
        for face in result['faces']:
            face.material_index=neighbors[0].material_index if neighbors else 0
            face.smooth=False
        bmesh.ops.triangulate(bm,faces=result['faces']);patches+=len(result['faces'])
    # The former solids also have broad planar end caps (including a hidden
    # rock floor under the upper metal deck). They can be visible to an audit
    # ray yet are not part of the vertical interior skin. Remove their complete
    # coplanar patches, retaining the small real cliff shelves and room soffits.
    cap_faces=set()
    seeds=[f for f in bm.faces if f.normal.z>.94 and f.calc_area()>18 and f.calc_center_median().x>3]
    for seed in seeds:
        if seed in cap_faces:continue
        normal=seed.normal.copy();plane=normal.dot(seed.verts[0].co);stack=[seed];cap_faces.add(seed)
        while stack:
            face=stack.pop()
            for edge in face.edges:
                for neighbor in edge.link_faces:
                    if neighbor not in cap_faces and normal.dot(neighbor.normal)>.99999 and abs(normal.dot(neighbor.calc_center_median())-plane)<.0001:
                        cap_faces.add(neighbor);stack.append(neighbor)
    cap_count=len(cap_faces)
    if cap_faces:bmesh.ops.delete(bm,geom=list(cap_faces),context='FACES')
    parts_after_caps=components(bm)
    if len(parts_after_caps)>1:bmesh.ops.delete(bm,geom=[v for part in parts_after_caps[1:] for v in part],context='VERTS')
    bm.to_mesh(root.data);bm.free()
    root.name='Cavern | single connected interior surface'
    for col in list(root.users_collection):col.objects.unlink(root)
    geo.objects.link(root)
    root['construction']='One connected interior skin. Original visible rock polygons preserved; hidden exterior and temporary closure removed. No remeshing or smoothing.'
    root['extraction_report']=json.dumps({'counts':counts,'connected_fold_faces':added_connections,'restored_occluded_fold_faces':filled,'components_before_dust_removal':part_sizes,'discarded_cavity_vertices':len(dust),'closed_small_seam_loops':patches,'removed_solid_cap_faces':cap_count})
    # Both materials have identical shader nodes; unify the material assignment
    # after the front/back selection so the whole surface uses the source rock.
    material=bpy.data.objects['Central rock mound | continuous cross-column extrusions'].data.materials[0]
    root.data.materials[front_index]=material
    print('INTERIOR_EXTRACTION',root['extraction_report'],flush=True)
    return root

if __name__=='__main__':
    bpy.ops.wm.open_mainfile(filepath=str(P/'preview-integration-source.blend'));bpy.context.preferences.filepaths.save_version=0
    S=bpy.context.scene;surface=integrate_surface(S)
    bpy.ops.wm.save_as_mainfile(filepath=str(P/'preview-integrated-surface.blend'),compress=True)
    S.render.resolution_x=1400;S.render.resolution_y=840;S.cycles.samples=24;S.render.filepath=str(P/'preview-integrated-overview.png');bpy.ops.render.render(write_still=True)
