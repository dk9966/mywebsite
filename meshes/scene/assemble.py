"""Assemble the meshes/ kit into a world, per layout.json.

This does NOT merge anything into one big GLB. It produces an *instance list*:
which model, at which transform. Each model is still one file, loaded once and
reused -- see README for why that beats a combined export (27.7 MB vs 3.9 MB
for this scene).

    python assemble.py            # write instances.json + render a preview
    python assemble.py --no-render

The same instances.json is what the three.js side should read.
"""
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'pillars', 'island_pillar_src'))

from glb import read_glb, accessor          # noqa: E402

BRIDGE_MODULE = 4.0        # bridge.glb spans x -2..2
BRIDGE_HALF_W = 1.0        # and z -1..1
DECK_TOP = 0.30            # top surface of the bridge deck
RAIL_MODULE = 1.0          # Rail_Span is 1 unit along x
RAIL_INSET = 0.90          # rails sit just inside the deck edge
LAMP_EVERY = 4             # rail modules between lamps
RAIL_GAP_MARGIN = 0.9      # extra clearance either side of a bridge entrance


def load_layout():
    return json.load(open(os.path.join(HERE, 'layout.json')))


def deck_height(island, pillar_tops):
    """Y of the island's walkable surface = pillar base + that variant's height."""
    return island['pos'][1] + pillar_tops[island['pillar']]


def bridge_drop(deck_y):
    """Bridge origin so its *deck surface* lands on the platform.

    bridge.glb spans y 0..0.3, so its walking surface is 0.3 above its origin.
    Placing the origin at deck height leaves the bridge floating by that much.
    """
    return deck_y - DECK_TOP


def pillar_metrics(layout):
    """Height and top-platform radius of each pillar variant, from the GLBs."""
    out = {}
    for key, rel in layout['models'].items():
        if not key.startswith('pillar_'):
            continue
        g, b = read_glb(os.path.join(HERE, rel))
        P = np.vstack([np.asarray(accessor(g, b, p['attributes']['POSITION']), float)
                       for p in g['meshes'][0]['primitives']])
        y = P[:, 1]
        r = np.hypot(P[:, 0], P[:, 2])
        top = y.max()
        out[key.split('_', 1)[1]] = dict(
            height=float(top - y.min()),
            top_radius=float(r[y > top - 0.02 * (top - y.min())].max()),
        )
    return out


def bridge_angle(a_pos, b_pos):
    """Compass direction from island a toward island b, in the ring's frame."""
    return math.atan2(b_pos[2] - a_pos[2], b_pos[0] - a_pos[0])


def rim_railings(island, deck_y, radius, open_angles):
    """Railing right around a platform edge, with a gap at every bridge.

    `open_angles` are the directions bridges leave in. Each one gets an opening
    wide enough for the deck plus a margin, worked out from the radius rather
    than guessed -- a fixed angular gap would be too wide on a big island and
    too narrow on a small one.
    """
    out = []
    n = max(8, int(round(2 * math.pi * radius / RAIL_MODULE)))
    step = 2 * math.pi / n
    half = [math.asin(min(0.95, (BRIDGE_HALF_W + RAIL_GAP_MARGIN) / radius))
            for _ in open_angles]

    for i in range(n):
        th = i * step
        blocked = False
        for ang, h in zip(open_angles, half):
            d = abs((th - ang + math.pi) % (2 * math.pi) - math.pi)
            if d < h:
                blocked = True
                break
        if blocked:
            continue
        pos = [island[0] + radius * math.cos(th), deck_y,
               island[2] + radius * math.sin(th)]
        # module runs along local +x; align it with the circle's tangent
        yaw = -th - math.pi / 2
        out.append(dict(model='railings', node='Rail_Span',
                        position=[round(v, 4) for v in pos],
                        rotation_y=round(yaw, 5),
                        scale=[round(step * radius / RAIL_MODULE, 4), 1.0, 1.0]))
    return out


def build():
    layout = load_layout()
    metrics = pillar_metrics(layout)
    tops = {k: v['height'] for k, v in metrics.items()}
    radii = {k: v['top_radius'] for k, v in metrics.items()}

    ps = layout.get('pillar_scale', 1.0)
    tops = {k: v * ps for k, v in tops.items()}
    radii = {k: v * ps for k, v in radii.items()}

    instances = []
    for name, isl in layout['islands'].items():
        instances.append(dict(model='pillar_' + isl['pillar'], name=name,
                              position=isl['pos'], rotation_y=0.0,
                              scale=[ps, ps, ps]))

    # bridges: one purpose-built mesh per span (see build_bridges.py), placed
    # at its start point. Each already contains its own railings, sloped to
    # match, so there is nothing to line up here.
    spans_path = os.path.join(HERE, 'spans.json')
    spans = json.load(open(spans_path)) if os.path.exists(spans_path) else {}
    if not spans:
        print('  ! no spans.json - run build_bridges.py first')

    open_dirs = {name: [] for name in layout['islands']}
    for br in layout['bridges']:
        a, b = layout['islands'][br['a']], layout['islands'][br['b']]
        open_dirs[br['a']].append(bridge_angle(a['pos'], b['pos']))
        open_dirs[br['b']].append(bridge_angle(b['pos'], a['pos']))

        key = 'bridge_%s_%s' % (br['a'], br['b'])
        sp = spans.get(key)
        if not sp:
            continue
        instances.append(dict(model=key, name=key,
                              position=sp['start'], rotation_y=sp['yaw'],
                              scale=[1.0, 1.0, 1.0]))
        layout['models'].setdefault(key, '../bridge/spans/%s.glb' % key)

    # railings around every island rim, leaving the bridge entrances clear
    for name, isl in layout['islands'].items():
        instances += rim_railings(isl['pos'], deck_height(isl, tops),
                                  radii[isl['pillar']], open_dirs[name])

    counts = {}
    for i in instances:
        counts[i['model']] = counts.get(i['model'], 0) + 1
    print('pillar variants: ' + ', '.join(
        '%s %.1f tall, top r %.2f' % (k, v['height'], v['top_radius'])
        for k, v in sorted(metrics.items())))
    print('instances: ' + ', '.join('%s x%d' % kv for kv in sorted(counts.items())))
    print('total %d instances from %d model files' % (len(instances), len(layout['models'])))

    # only ship a manifest entry for models actually placed -- the bridge
    # module is now consumed by build_bridges.py rather than instanced
    used = {i['model'] for i in instances}
    json.dump(dict(models={k: v for k, v in layout['models'].items() if k in used},
                   instances=instances),
              open(os.path.join(HERE, 'instances.json'), 'w'), indent=1)
    return layout, instances


if __name__ == '__main__':
    build()
