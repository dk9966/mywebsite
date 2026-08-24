"""Minimal glTF 2.0 binary (.glb) reader and writer.

Only what this asset needs: a single buffer, float/uint accessors and
PNG/JPEG images stored in buffer views.
"""
import json
import struct
import numpy as np

_CT = {5125: '<u4', 5126: '<f4', 5123: '<u2'}
_NC = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4}


def read_glb(path):
    """Return (gltf_json, bin_chunk)."""
    d = open(path, 'rb').read()
    magic, ver, total = struct.unpack('<4sII', d[:12])
    if magic != b'glTF' or ver != 2 or total != len(d):
        raise ValueError('not a valid glb: %s' % path)
    jl, jt = struct.unpack('<I4s', d[12:20])
    assert jt == b'JSON'
    g = json.loads(d[20:20 + jl])
    bl, bt = struct.unpack('<I4s', d[20 + jl:28 + jl])
    assert bt == b'BIN\x00'
    return g, d[28 + jl:28 + jl + bl]


def accessor(g, bin_, ai):
    a = g['accessors'][ai]
    v = g['bufferViews'][a['bufferView']]
    off = v.get('byteOffset', 0) + a.get('byteOffset', 0)
    n = _NC[a['type']]
    return np.frombuffer(bin_, _CT[a['componentType']], a['count'] * n, off).reshape(-1, n)


def read_mesh(path):
    """Convenience: first primitive of the first mesh -> (indices, positions)."""
    g, bin_ = read_glb(path)
    prim = g['meshes'][0]['primitives'][0]
    idx = accessor(g, bin_, prim['indices']).reshape(-1, 3).astype(np.int64)
    pos = accessor(g, bin_, prim['attributes']['POSITION']).astype(np.float64)
    return idx, pos


class GLBWriter:
    """Accumulates buffer views / accessors, then serialises a .glb."""

    ARRAY_BUFFER = 34962
    ELEMENT_ARRAY_BUFFER = 34963

    def __init__(self):
        self.buf = bytearray()
        self.views = []
        self.accessors = []

    def _pad(self):
        while len(self.buf) % 4:
            self.buf.append(0)

    def add_view(self, data, target=None):
        self._pad()
        v = {'buffer': 0, 'byteOffset': len(self.buf), 'byteLength': len(data)}
        if target:
            v['target'] = target
        self.buf.extend(data)
        self.views.append(v)
        return len(self.views) - 1

    def add_image(self, path):
        return self.add_view(open(path, 'rb').read())

    def add_accessor(self, arr, type_, component_type, target):
        a = np.ascontiguousarray(arr)
        d = {'bufferView': self.add_view(a.tobytes(), target),
             'componentType': component_type, 'count': len(arr), 'type': type_}
        if type_ != 'SCALAR':                      # min/max required for POSITION
            d['min'] = arr.min(0).tolist()
            d['max'] = arr.max(0).tolist()
        self.accessors.append(d)
        return len(self.accessors) - 1

    def add_f32(self, arr, type_):
        return self.add_accessor(arr.astype('<f4'), type_, 5126, self.ARRAY_BUFFER)

    def add_indices(self, arr):
        return self.add_accessor(arr.astype('<u4'), 'SCALAR', 5125,
                                 self.ELEMENT_ARRAY_BUFFER)

    def write(self, path, gltf):
        self._pad()
        gltf['bufferViews'] = self.views
        gltf['accessors'] = self.accessors
        gltf['buffers'] = [{'byteLength': len(self.buf)}]
        js = json.dumps(gltf, separators=(',', ':')).encode()
        js += b' ' * ((4 - len(js) % 4) % 4)
        total = 12 + 8 + len(js) + 8 + len(self.buf)
        out = (b'glTF' + struct.pack('<II', 2, total)
               + struct.pack('<I', len(js)) + b'JSON' + js
               + struct.pack('<I', len(self.buf)) + b'BIN\x00' + bytes(self.buf))
        open(path, 'wb').write(out)
        return total
