"""Tileable procedural noise helpers."""
import numpy as np


def fbm(N, beta=2.0, seed=0, lo=1.0):
    """Seamlessly tileable fractal noise in [0, 1].

    Built by shaping white noise in the frequency domain with a 1/f**beta
    falloff, so the result is periodic by construction -- no visible seam
    when the texture is tiled.
    """
    r = np.random.default_rng(seed).normal(size=(N, N))
    F = np.fft.fft2(r)
    fy = np.fft.fftfreq(N)[:, None] * N
    fx = np.fft.fftfreq(N)[None, :] * N
    f = np.sqrt(fx ** 2 + fy ** 2)
    f[0, 0] = 1
    F *= np.where(f < lo, 0, 1) / f ** beta
    a = np.real(np.fft.ifft2(F))
    a -= a.min()
    a /= a.max() + 1e-9
    return a


def worley(N, n=90, seed=1):
    """Tileable Worley/cellular noise. Returns (nearest, second-nearest) distance."""
    g = np.random.default_rng(seed).random((n, 2)) * N
    ys, xs = np.mgrid[0:N, 0:N]
    d1 = np.full((N, N), 1e9)
    d2 = np.full((N, N), 1e9)
    for p in g:
        for ox in (-N, 0, N):          # wrap in both axes for tileability
            for oy in (-N, 0, N):
                d = np.hypot(xs - (p[0] + ox), ys - (p[1] + oy))
                m = d < d1
                d2 = np.where(m, d1, np.minimum(d2, d))
                d1 = np.where(m, d, d1)
    return d1, d2


def to_normal(h, strength=2.0):
    """Height field -> tangent-space normal map (uint8 RGB)."""
    gy, gx = np.gradient(h.astype(np.float32))
    n = np.stack([-gx * strength, gy * strength, np.ones_like(h)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return ((n * 0.5 + 0.5) * 255).astype(np.uint8)
