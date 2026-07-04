"""
hexgrid.py — pointy-top hex math in axial coordinates (q, r).

The crux of the game: the two VERTICAL edges (E = +1,0 and W = -1,0) are
BLOCKED. Only the four slanted edges are walkable, so every move reads as a
stair-step up or down the isometric-cube slope. The grid stays fully connected
because the east neighbour is reachable by a NE -> SE zig-zag.
"""

import math

# The four walkable slanted directions: NE, NW, SE, SW.
WALKABLE_DIRS = [(1, -1), (0, -1), (0, 1), (-1, 1)]
# The two blocked vertical edges: E, W.
BLOCKED_DIRS = [(1, 0), (-1, 0)]
# All six geometric neighbours (used only for adjacency/rendering, not movement).
ALL_DIRS = WALKABLE_DIRS + BLOCKED_DIRS

_SQRT3 = math.sqrt(3.0)


def walkable_neighbors(q, r):
    """The four tiles reachable in one step from (q, r)."""
    return [(q + dq, r + dr) for dq, dr in WALKABLE_DIRS]


def all_neighbors(q, r):
    """All six geometric neighbours (includes the blocked E/W tiles)."""
    return [(q + dq, r + dr) for dq, dr in ALL_DIRS]


def axial_distance(a, b):
    """Hex distance ignoring movement restrictions (used for rough heuristics)."""
    aq, ar = a
    bq, br = b
    return (abs(aq - bq) + abs(aq + ar - bq - br) + abs(ar - br)) // 2


def hex_to_pixel(q, r, size):
    """Centre pixel of a pointy-top hex at (q, r), before camera transform."""
    x = size * _SQRT3 * (q + r / 2.0)
    y = size * 1.5 * r
    return x, y


def pixel_to_hex(x, y, size):
    """Inverse of hex_to_pixel with cube rounding -> nearest (q, r)."""
    q = (_SQRT3 / 3.0 * x - 1.0 / 3.0 * y) / size
    r = (2.0 / 3.0 * y) / size
    return _axial_round(q, r)


def _axial_round(q, r):
    """Round fractional axial coords to the nearest hex (via cube rounding)."""
    x, z = q, r
    yy = -x - z
    rx, ry, rz = round(x), round(yy), round(z)
    dx, dy, dz = abs(rx - x), abs(ry - yy), abs(rz - z)
    if dx > dy and dx > dz:
        rx = -ry - rz
    elif dy > dz:
        ry = -rx - rz
    else:
        rz = -rx - ry
    return int(rx), int(rz)


def hex_corners(cx, cy, size):
    """Six corner points of a pointy-top hex centred at (cx, cy).

    Order (clockwise from top): top, upper-right, lower-right,
    bottom, lower-left, upper-left. Corner index maps to the cube faces used
    by the renderer.
    """
    pts = []
    for i in range(6):
        ang = math.radians(60 * i - 90)   # -90 deg = straight up (screen y is down)
        pts.append((cx + size * math.cos(ang), cy + size * math.sin(ang)))
    return pts


def chunk_of(q, r, chunk_size):
    """Chunk key (cq, cr) that owns tile (q, r)."""
    return (q // chunk_size, r // chunk_size)


def chunk_tiles(cq, cr, chunk_size):
    """Iterate the (q, r) of every tile in chunk (cq, cr)."""
    for dr in range(chunk_size):
        for dq in range(chunk_size):
            yield (cq * chunk_size + dq, cr * chunk_size + dr)
