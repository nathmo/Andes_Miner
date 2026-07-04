"""
worldgen.py — deterministic, pure-Python procedural generation.

No C extensions (numpy / noise), so it compiles cleanly to WASM under pygbag.
We use seeded value noise with fractal Brownian motion (fBm). Everything is a
pure function of (q, r, seed), so the same seed reproduces the same map and we
never have to store unmodified tiles.
"""

import math
import config


def _hash01(ix, iy, seed):
    """Deterministic pseudo-random value in [0, 1) for integer lattice point."""
    h = (ix * 374761393 + iy * 668265263 + seed * 1442695040888963407) & 0xFFFFFFFF
    h = (h ^ (h >> 13)) * 1274126177 & 0xFFFFFFFF
    h ^= h >> 16
    return (h & 0xFFFFFF) / float(0x1000000)


def _smooth(t):
    return t * t * (3.0 - 2.0 * t)


def _value_noise(x, y, seed):
    """Bilinearly-interpolated, smoothed value noise in [0, 1)."""
    x0, y0 = math.floor(x), math.floor(y)
    fx, fy = x - x0, y - y0
    sx, sy = _smooth(fx), _smooth(fy)
    n00 = _hash01(x0, y0, seed)
    n10 = _hash01(x0 + 1, y0, seed)
    n01 = _hash01(x0, y0 + 1, seed)
    n11 = _hash01(x0 + 1, y0 + 1, seed)
    ix0 = n00 + (n10 - n00) * sx
    ix1 = n01 + (n11 - n01) * sx
    return ix0 + (ix1 - ix0) * sy


def fbm(x, y, seed, octaves=config.NOISE_OCTAVES):
    """Fractal noise in [0, 1): sums octaves of value noise."""
    total = 0.0
    amp = 1.0
    freq = 1.0
    norm = 0.0
    for _ in range(octaves):
        total += amp * _value_noise(x * freq, y * freq, seed)
        norm += amp
        amp *= 0.5
        freq *= 2.0
    return total / norm


def rock_at(q, r, seed):
    """The rock-type key that naturally generates at (q, r) for this seed."""
    # Base rock hardness field.
    base = fbm(q * config.NOISE_BASE_FREQ, r * config.NOISE_BASE_FREQ, seed)

    # Ore-vein field (separate seed offset, lower frequency = big rare blobs).
    vein = fbm(q * config.NOISE_VEIN_FREQ, r * config.NOISE_VEIN_FREQ, seed + 91)
    if vein > config.VEIN_T:
        # Inside a vein: a rare high patch is lithium ore, else iron vs copper.
        li = fbm(q * config.NOISE_VEIN_FREQ * 1.7, r * config.NOISE_VEIN_FREQ * 1.7, seed + 991)
        if li > config.LITHIUM_T:
            return "spodumene"
        pick = fbm(q * config.NOISE_VEIN_FREQ, r * config.NOISE_VEIN_FREQ, seed + 613)
        return "basalt" if pick >= 0.5 else "rhyolite"

    # Otherwise a plain rock, harder toward the low end of the base field.
    if base < config.GRANITE_T:
        return "granite"
    if base < config.DIORITE_T:
        return "diorite"
    return "andesite"


def villages(seed, n=config.NUM_VILLAGES):
    """Deterministic village sites, scattered widely across the slope (big lateral
    spread) to reward exploring sideways. Pure function of the seed."""
    out = []
    for i in range(n):
        hq = _hash01(i * 17 + 5, 3, seed + 5551)
        hr = _hash01(2, i * 23 + 11, seed + 7777)
        q = int(round((hq - 0.5) * config.VILLAGE_SPREAD_Q))
        r = int(round((hr - 0.5) * config.VILLAGE_SPREAD_R))
        if abs(q) + abs(r) < 9:                 # keep clear of the HQ start area
            q += 14 if q >= 0 else -14
        out.append((q, r))
    return list(dict.fromkeys(out))             # dedupe, keep order
