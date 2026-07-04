"""
pathfinding.py — A* over the 4-direction walkable graph.

Agents may only step across the four slanted edges (NE/NW/SE/SW) and only onto
passable tiles (rubble/excavated/road). To work a solid tile (mine a rock,
construct a building), an agent paths to an adjacent passable tile instead of
onto the target itself.
"""

import heapq
import hexgrid


def _heuristic(a, b):
    # Admissible-ish: real moves are diagonal, so axial distance underestimates.
    return hexgrid.axial_distance(a, b)


def find_path(world, start, goal, max_expand=4000):
    """A* from start (q,r) to goal (q,r), stepping only through passable tiles.
    Returns a list of (q,r) from the tile AFTER start to goal, or None."""
    if start == goal:
        return []
    open_heap = [(0, start)]
    came = {start: None}
    gscore = {start: 0}
    expanded = 0
    while open_heap:
        _, cur = heapq.heappop(open_heap)
        if cur == goal:
            return _reconstruct(came, goal)
        expanded += 1
        if expanded > max_expand:
            return None
        cq, cr = cur
        for (nq, nr) in hexgrid.walkable_neighbors(cq, cr):
            nxt = (nq, nr)
            if nxt != goal and not world.get_tile(nq, nr).passable():
                continue
            ng = gscore[cur] + 1
            if nxt not in gscore or ng < gscore[nxt]:
                gscore[nxt] = ng
                came[nxt] = cur
                heapq.heappush(open_heap, (ng + _heuristic(nxt, goal), nxt))
    return None


def find_path_adjacent(world, start, target, max_expand=4000):
    """Path to the best passable tile adjacent (one walkable step) to `target`.
    Used to reach a solid tile we intend to work. Returns (path, stand_tile) or
    (None, None)."""
    candidates = []
    for (nq, nr) in hexgrid.walkable_neighbors(*target):
        t = world.get_tile(nq, nr)
        if t.passable() or (nq, nr) == start:
            candidates.append((nq, nr))
    if not candidates:
        return None, None
    best = None
    best_len = None
    for stand in candidates:
        if stand == start:
            return [], stand
        path = find_path(world, start, stand, max_expand)
        if path is not None and (best_len is None or len(path) < best_len):
            best, best_len = (path, stand), len(path)
    if best:
        return best
    return None, None


def _reconstruct(came, goal):
    path = []
    cur = goal
    while came[cur] is not None:
        path.append(cur)
        cur = came[cur]
    path.reverse()
    return path
