"""Read-only diagnostic: calculate and bound a proposed local rock pull."""
import bpy,json,math
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent
w=bpy.data.objects['150 | continuous cave with oblique carved rooms']
deck=bpy.data.objects['Upper | beveled square gallery']
assert not w.modifiers['Upper right | continuous forward rock fit'].show_viewport
mx=deck.matrix_world.inverted()@w.matrix_world
ev=w.evaluated_get(bpy.context.evaluated_depsgraph_get())
coords=[mx@v.co for v in ev.data.vertices]
source=(P/'pull_rock_forward.py').read_text()
calculation=source[source.index('def smooth(t):'):source.index("attr=w.data.attributes.get('upper_forward_rock_delta')")]
exec(compile(calculation,str(P/'pull_rock_forward.py'),'exec'))
changed=[(i,(q-p).length) for i,(p,q) in enumerate(zip(coords,new)) if (q-p).length>1e-6]
outside=[i for i,d in changed if not (-3.51<=coords[i].x<=6.31 and -6.41<=coords[i].y<=2.11 and 9.14<=coords[i].z<=14.76)]
result={'changed_vertices':len(changed),'max_displacement_m':max(d for i,d in changed),'outside_local_bounds':len(outside),'changed_bounds':[[min(coords[i][a] for i,d in changed),max(coords[i][a] for i,d in changed)] for a in range(3)],'top_five':[{'source':list(coords[i]),'delta':list(new[i]-coords[i])} for i,d in sorted(changed,key=lambda t:-t[1])[:5]]}
(P/'preflight.json').write_text(json.dumps(result,indent=2))
