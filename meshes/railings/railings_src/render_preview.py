"""Render a labelled contact sheet straight from the exported .glb.

Everything is read back out of the file -- geometry, UVs, materials, textures --
so what you see is what the asset actually contains, not what the build script
intended. This mirrors the bridge and the pillar, where an earlier previewer
reused the build script's in-memory state and happily rendered things the
exported file did not contain.

Nine panels: every module on its own in three-quarter, two straight-on
elevations to check proportions against the reference sheet, and two
assemblies. The assemblies are the ones that earn their place -- a module that
tiles badly still looks perfect on its own, and the only way to see a wrong
module length, a post straddling a seam or a half collar that fails to meet its
neighbour is to place several copies on the grid and look at the joins.

The corner panel additionally exercises the thing the kit exists for: turning
90 degrees around an island. It is the only view that puts a rotated module
next to an unrotated one.

Run:  python render_preview.py [output.png]
"""
import io
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import config as cfg
from glb import read_glb, accessor
from raster import render

W, H = 620, 400


def P(name, x=0.0, z=0.0, rot=0.0, flip=False, sx=1.0):
    """One placed copy: module name, grid position, Y rotation, X scale.

    `sx` exists for Rail_Span, the one node meant to be stretched. It is
    applied before rotation, in the module's own local X, which is the only
    axis along which that node is constant and therefore the only one it is
    safe to scale.
    """
    return dict(name=name, x=x, z=z, rot=rot, flip=flip, sx=sx)



def walk(fn, n, step=1.0):
    """Sample a path at a constant *chord* of `step`, not a constant parameter.

    Modules are rigid 1 m chords, so they have to be laid on the curve the way
    a chain is: each one spans exactly 1 m straight-line from the last post to
    the next. Sampling the parameter evenly instead would stretch the spacing
    wherever the curve runs fast and the posts would drift out of the joints.
    Bisection on arc position is plenty here -- the paths are smooth and there
    are only a handful of links.
    """
    import numpy as _np
    pts, t = [_np.array(fn(0.0))], 0.0
    for _ in range(n):
        lo, hi = t, t + 1.0
        while _np.linalg.norm(_np.array(fn(hi)) - pts[-1]) < step:
            hi += 1.0
        for _ in range(60):
            mid = 0.5 * (lo + hi)
            if _np.linalg.norm(_np.array(fn(mid)) - pts[-1]) < step:
                lo = mid
            else:
                hi = mid
        t = 0.5 * (lo + hi)
        pts.append(_np.array(fn(t)))
    return pts


def chain(fn, n, module='Rail_Middle'):
    """Lay `n` modules nose to tail along a path, one per unit chord.

    A module's seam post sits at its own x = -0.5, so the post lands on the
    path point and the module body spans forward to the next one. Heading is
    atan2(-dz, dx) to match the renderer's Y rotation, which turns local +X
    toward world (cos, -sin).
    """
    import numpy as _np
    pts = walk(fn, n)
    out = []
    for a, b in zip(pts[:-1], pts[1:]):
        d = b - a
        mid = 0.5 * (a + b)
        out.append(P(module, float(mid[0]), float(mid[1]),
                     rot=float(_np.degrees(_np.arctan2(-d[1], d[0])))))
    return out


# Straight-on elevations use a long lens from far away rather than an
# orthographic camera: the rasteriser is perspective-only, and at 5 m with a
# 8 degree lens the convergence over a 1 m module is well under a pixel.
VIEWS = [
    dict(label='1  Rail_Middle  (repeatable, 1.00 m)', fov=30,
         cam=(0.60, 0.42, 1.30), tgt=(0.00, 0.130, 0.0),
         place=[P('Rail_Middle')]),
    dict(label='2  Rail_Middle  elevation', fov=9,
         cam=(0.0, 0.135, 5.00), tgt=(0.0, 0.135, 0.0),
         place=[P('Rail_Middle')]),
    dict(label='3  Rail_End  /  Rail_Lamp', fov=32,
         cam=(0.95, 0.72, 1.75), tgt=(0.05, 0.190, -0.5),
         place=[P('Rail_End', 0.0, 0.45), P('Rail_Lamp', 0.0, -0.45)]),
    dict(label='4  Post_Corner  +  Rail_Span scaled to 0.45 m', fov=34,
         cam=(0.72, 0.52, 1.05), tgt=(-0.20, 0.150, 0.0),
         place=[P('Post_Corner'), P('Rail_Span', -0.325, sx=0.45)]),
    dict(label='5  straight run: Lamp + 3x Middle + End', fov=30,
         cam=(0.60, 0.95, 5.05), tgt=(1.98, 0.150, 0.0),
         place=[P('Rail_Lamp', 0.0, flip=True), P('Rail_Middle', 1.0),
                P('Rail_Middle', 2.0), P('Rail_Middle', 3.0),
                P('Rail_End', 4.0)]),
    dict(label='6  90 deg corner on a Post_Corner', fov=34,
         cam=(1.60, 1.10, 1.60), tgt=(-0.50, 0.150, -0.50),
         place=[P('Post_Corner'),
                P('Rail_Middle', -0.5), P('Rail_Middle', -1.5),
                P('Rail_Middle', 0.0, -0.5, rot=90),
                P('Rail_Middle', 0.0, -1.5, rot=90)]),
    # a 3.2 m radius arc: 10 identical straight modules, each rotated ~18 deg
    # against its neighbour. Nothing here is bent.
    dict(label='7  curved run: arc, r = 3.2 m (10x Rail_Middle)', fov=32,
         cam=(1.20, 4.20, 4.20), tgt=(0.40, 0.150, -3.00),
         place=chain(lambda t: (3.2 * np.sin(t), 3.2 * np.cos(t) - 3.2), 10)),
    # and an S: same modules, no two joints at the same angle
    dict(label='8  squiggly run: S-curve (8x Rail_Middle)', fov=38,
         cam=(3.60, 3.40, 5.60), tgt=(3.90, 0.150, 0.0),
         place=chain(lambda t: (t, 0.85 * np.sin(t * 1.15)), 8)),
]


def load(path):
    """Read every node back, keyed by node name."""
    g, bin_ = read_glb(path)

    def image(i, srgb=True):
        v = g['bufferViews'][g['images'][i]['bufferView']]
        raw = bin_[v['byteOffset']:v['byteOffset'] + v['byteLength']]
        a = np.asarray(Image.open(io.BytesIO(raw)).convert('RGB')) / 255.0
        return a ** 2.2 if srgb else a          # sRGB maps -> linear

    def material(mi):
        m = g['materials'][mi]
        pbr = m.get('pbrMetallicRoughness', {})
        d = {}
        f = pbr.get('baseColorFactor', [1, 1, 1, 1])
        d['base'] = np.array(f[:3])[None, None, :] * np.ones((2, 2, 3))
        r = pbr.get('roughnessFactor', 1.0)
        d['orm'] = np.stack([np.ones((2, 2)), np.full((2, 2), r),
                             np.zeros((2, 2))], -1)
        strength = (m.get('extensions', {})
                     .get('KHR_materials_emissive_strength', {})
                     .get('emissiveStrength', 1.0))
        if 'emissiveTexture' in m:
            d['lut'] = image(g['textures'][m['emissiveTexture']['index']]['source'])
            d['emis'] = [c * strength for c in m['emissiveFactor']]
        else:
            # a flat lens: no LUT, so it is drawn as a constant emissive block
            d['lut'] = None
            d['flat_emis'] = np.array(m['emissiveFactor']) * strength
        return d

    out = {}
    for node in g['nodes']:
        A, I, U0, U1, TA, NM, M, off = [], [], [], [], [], [], [], 0
        for prim in g['meshes'][node['mesh']]['primitives']:
            at = prim['attributes']
            pos = accessor(g, bin_, at['POSITION']).astype(np.float64)
            tris = accessor(g, bin_, prim['indices']).astype(int).reshape(-1, 3)
            A.append(pos)
            U0.append(accessor(g, bin_, at['TEXCOORD_0']).astype(np.float64))
            U1.append(accessor(g, bin_, at['TEXCOORD_1']).astype(np.float64))
            TA.append(accessor(g, bin_, at['TANGENT']).astype(np.float64))
            NM.append(accessor(g, bin_, at['NORMAL']).astype(np.float64))
            I.append(tris + off)
            M += [prim['material']] * len(tris)
            off += len(pos)
        out[node['name']] = (np.vstack(A), np.vstack(I), np.vstack(U0),
                             np.vstack(U1), np.vstack(TA), np.vstack(NM),
                             np.array(M))
    return out, {i: material(i) for i in range(len(g['materials']))}


def _rotate_y(v, deg):
    """Rotate the XZ components of an (N, >=3) array about the Y axis."""
    if not deg:
        return v
    c, s = np.cos(np.radians(deg)), np.sin(np.radians(deg))
    x, z = v[:, 0].copy(), v[:, 2].copy()
    v[:, 0] = x * c + z * s
    v[:, 2] = -x * s + z * c
    return v


def assemble(nodes, placement):
    """Concatenate placed copies of nodes into one scene.

    Rotation is orientation preserving, so winding is untouched. Mirroring is
    not: it reverses triangle winding and flips the tangent frame's handedness,
    and both have to be undone or the mirrored piece renders inside out with
    its normal-mapped shading backwards. Nothing carries a normal map today,
    but getting it wrong here would quietly poison any preview taken after one
    is added.
    """
    A, I, U0, U1, TA, NM, M, off = [], [], [], [], [], [], [], 0
    for p in placement:
        pos, i, u0, u1, ta, nm, m = nodes[p['name']]
        pos, ta, nm, i = pos.copy(), ta.copy(), nm.copy(), i.copy()
        if p['sx'] != 1.0:
            pos[:, 0] *= p['sx']
        if p['flip']:
            pos[:, 0] = -pos[:, 0]
            nm[:, 0] = -nm[:, 0]
            ta[:, 0] = -ta[:, 0]
            ta[:, 3] = -ta[:, 3]
            i = i[:, ::-1]
        _rotate_y(pos, p['rot'])
        _rotate_y(nm, p['rot'])
        _rotate_y(ta, p['rot'])
        pos[:, 0] += p['x']
        pos[:, 2] += p['z']
        A.append(pos)
        I.append(i + off)
        U0.append(u0)
        U1.append(u1)
        TA.append(ta)
        NM.append(nm)
        M.append(m)
        off += len(pos)
    return (np.vstack(A), np.vstack(I), np.vstack(U0), np.vstack(U1),
            np.vstack(TA), np.vstack(NM), np.concatenate(M))


def _font(size):
    for p in ('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
              '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    out = sys.argv[1] if len(sys.argv) > 1 else cfg.PREVIEW_PNG
    nodes, mats = load(cfg.OUTPUT_GLB)
    font = _font(15)

    tiles = []
    for v in VIEWS:
        geo = assemble(nodes, v['place'])
        frame = render(*geo[:4], geo[6], mats, tang=geo[4], vnorm=geo[5],
                       W=W, H=H, cam=v['cam'], tgt=v['tgt'], fov=v['fov'])
        img = Image.fromarray(frame)
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, W - 1, 22], fill=(26, 29, 36))
        d.text((9, 4), v['label'], font=font, fill=(196, 206, 224))
        d.rectangle([0, 0, W - 1, H - 1], outline=(58, 64, 78))
        tiles.append(np.asarray(img))
        print('  rendered %s' % v['label'])

    rows = [np.concatenate(tiles[i:i + 4], 1) for i in range(0, len(tiles), 4)]
    Image.fromarray(np.concatenate(rows, 0)).save(out)
    print('wrote %s  (%d panels, %dx%d)' % (out, len(tiles), W * 4, H * 2))


if __name__ == '__main__':
    main()
