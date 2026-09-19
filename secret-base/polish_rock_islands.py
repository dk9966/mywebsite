# Runs within rework_rock_islands.py with the geometry/material helpers.
for key,x,y,r,top in specs:
    vs=[];fs=[]
    # Small, clustered outcrops obscure portions of the circular fascia.
    for j in range(27):
        a=math.tau*j/27
        if math.sin(a*3+.7)<-.25:continue
        rr=r*1.005
        prism(vs,fs,x+math.cos(a)*rr,y+math.sin(a)*rr,top-random.uniform(.5,.9),top+random.uniform(-.035,.12),.22,.16,a)
    mesh('Rock | '+key+' embedded deck shoulder',vs,fs,rocks)
    coll=bpy.data.collections['deck_'+key]
    for o in coll.objects:
        if o.type=='LIGHT' and 'lantern' in o.name:
            if 'rock_original_power' not in o:o['rock_original_power']=o.data.energy
            o.data=o.data.copy();o.data.energy=max(o['rock_original_power']*3,5);o.data.color=(1,.42,.12)
        if o.type=='MESH' and any(t in o.name for t in ['lantern_glass','brazier_flames']):
            for slot in o.material_slots:
                if not slot.material or not slot.material.use_nodes:continue
                mat=slot.material.copy();slot.material=mat
                for node in mat.node_tree.nodes:
                    if node.type=='BSDF_PRINCIPLED':
                        node.inputs['Emission Color'].default_value=(1,.40,.08,1);node.inputs['Emission Strength'].default_value=5
    # Low, soft local mist banks break the continuous blue chasm wash.
    mat=bpy.data.materials.new('Rock | '+key+' low cloud');mat.use_nodes=True;nt=mat.node_tree;nt.nodes.clear()
    out=nt.nodes.new('ShaderNodeOutputMaterial');vol=nt.nodes.new('ShaderNodeVolumePrincipled')
    vol.inputs['Color'].default_value=(.18,.38,.6,1);vol.inputs['Emission Color'].default_value=(.04,.25,.6,1)
    co=nt.nodes.new('ShaderNodeTexCoord');tex=nt.nodes.new('ShaderNodeTexNoise');tex.inputs['Scale'].default_value=4;tex.inputs['Detail'].default_value=3
    nt.links.new(co.outputs['Generated'],tex.inputs['Vector'])
    dist=nt.nodes.new('ShaderNodeVectorMath');dist.operation='DISTANCE';dist.inputs[1].default_value=(.5,.5,.5);nt.links.new(co.outputs['Generated'],dist.inputs[0])
    fall=nt.nodes.new('ShaderNodeMapRange');fall.inputs['From Min'].default_value=.12;fall.inputs['From Max'].default_value=.5;fall.inputs['To Min'].default_value=1;fall.inputs['To Max'].default_value=0;nt.links.new(dist.outputs['Value'],fall.inputs[0])
    mul=nt.nodes.new('ShaderNodeMath');mul.operation='MULTIPLY';nt.links.new(tex.outputs['Fac'],mul.inputs[0]);nt.links.new(fall.outputs[0],mul.inputs[1])
    for socket,factor in [('Density',.38),('Emission Strength',.055)]:
        n=nt.nodes.new('ShaderNodeMath');n.operation='MULTIPLY';n.inputs[1].default_value=factor;nt.links.new(mul.outputs[0],n.inputs[0]);nt.links.new(n.outputs[0],vol.inputs[socket])
    nt.links.new(vol.outputs[0],out.inputs['Volume'])
    vs=[(x+dx*5,y+dy*4,-2+dz*2.7) for dx,dy,dz in [(-1,-1,-1),(-1,-1,1),(-1,1,-1),(-1,1,1),(1,-1,-1),(1,-1,1),(1,1,-1),(1,1,1)]]
    mesh('Rock | '+key+' low mist bank',vs,[(0,4,6,2),(1,3,7,5),(0,1,5,4),(2,6,7,3),(0,2,3,1),(4,5,7,6)],[mat])
for m in bpy.data.materials:
    if m.use_nodes and 'workshop_cyan' in m.name:
        for node in m.node_tree.nodes:
            if node.type=='BSDF_PRINCIPLED':node.inputs['Emission Color'].default_value=(.04,.38,.8,1)
