"""
world.py — the infinite, lazily-generated world of hex tiles.

Chunks are generated on demand from worldgen and cached. Only tiles the player
has changed are "modified"; those are what save.py persists (the rest is
regenerated from the seed). Also owns tile-state transitions, the road-range
mineable rule, and the HQ / starting area.
"""

import config
import hexgrid
import worldgen
from tiles import Tile, ROCK, RUBBLE, EXCAVATED, ROAD


class World:
    def __init__(self, seed=config.WORLD_SEED):
        self.seed = seed
        self.chunks = {}                 # (cq, cr) -> {(q, r): Tile}
        self.modified = set()            # (q, r) of tiles that diverge from gen
        self.hq = (0, 0)                 # HQ tile (haul destination)
        self.road_tiles = set()          # cache of ROAD (q, r) for range checks
        self.villages = worldgen.villages(seed)   # goal outposts to connect by road
        self._setup_start_area()

    # ------------------------------------------------------------------ chunks
    def _ensure_chunk(self, cq, cr):
        key = (cq, cr)
        chunk = self.chunks.get(key)
        if chunk is None:
            chunk = {}
            for (q, r) in hexgrid.chunk_tiles(cq, cr, config.CHUNK_SIZE):
                chunk[(q, r)] = Tile(q, r, worldgen.rock_at(q, r, self.seed))
            self.chunks[key] = chunk
        return chunk

    def get_tile(self, q, r):
        cq, cr = hexgrid.chunk_of(q, r, config.CHUNK_SIZE)
        return self._ensure_chunk(cq, cr)[(q, r)]

    def loaded_tiles_in_view(self, q_lo, q_hi, r_lo, r_hi):
        """Yield tiles whose axial coords fall in the given inclusive box."""
        for r in range(r_lo, r_hi + 1):
            for q in range(q_lo, q_hi + 1):
                yield self.get_tile(q, r)

    def _mark_modified(self, tile):
        self.modified.add((tile.q, tile.r))

    # ------------------------------------------------------------------ start
    def _setup_start_area(self):
        """Carve a small excavated patch with a short road around the HQ so the
        first mining jobs are legal immediately."""
        hq_q, hq_r = self.hq
        # A compact blob of excavated tiles around HQ.
        patch = [(hq_q, hq_r)]
        for (nq, nr) in hexgrid.walkable_neighbors(hq_q, hq_r):
            patch.append((nq, nr))
            for (nq2, nr2) in hexgrid.walkable_neighbors(nq, nr):
                patch.append((nq2, nr2))
        for (q, r) in set(patch):
            t = self.get_tile(q, r)
            t.state = EXCAVATED
            self._mark_modified(t)
        # Lay road on HQ and its immediate walkable neighbours.
        for (q, r) in [self.hq] + hexgrid.walkable_neighbors(hq_q, hq_r):
            t = self.get_tile(q, r)
            t.state = ROAD
            self.road_tiles.add((q, r))
            self._mark_modified(t)

    # ------------------------------------------------------------------ queries
    def dist_to_road(self, q, r, limit):
        """Walkable-step distance from (q, r) to the nearest ROAD, searched only
        through passable tiles, capped at `limit`. Returns None if farther."""
        if (q, r) in self.road_tiles:
            return 0
        frontier = [(q, r)]
        seen = {(q, r)}
        dist = 0
        while frontier and dist < limit:
            dist += 1
            nxt = []
            for (cq, cr) in frontier:
                for (nq, nr) in hexgrid.walkable_neighbors(cq, cr):
                    if (nq, nr) in seen:
                        continue
                    seen.add((nq, nr))
                    nt = self.get_tile(nq, nr)
                    if nt.state == ROAD:
                        return dist
                    if nt.passable():
                        nxt.append((nq, nr))
            frontier = nxt
        return None

    def road_within(self, q, r, k):
        """True if a ROAD lies within k walkable steps of (q, r), searching across
        any tiles (so a road dug up next to a buried village still counts)."""
        if (q, r) in self.road_tiles:
            return True
        frontier = [(q, r)]
        seen = {(q, r)}
        for _ in range(k):
            nxt = []
            for (cq, cr) in frontier:
                for n in hexgrid.walkable_neighbors(cq, cr):
                    if n in seen:
                        continue
                    seen.add(n)
                    if self.get_tile(*n).state == ROAD:
                        return True
                    nxt.append(n)
            frontier = nxt
        return False

    def mineable(self, tile, reach=None):
        """A solid rock is mineable if a ROAD lies within `reach` walkable steps
        through passable tiles (road -> [excavated] -> rock). Reach defaults to the
        baseline MINE_ROAD_RANGE; higher-tier machines pass a larger reach."""
        if reach is None:
            reach = config.MINE_ROAD_RANGE
        if tile.state != ROCK:
            return False
        # The rock itself is a wall; check its passable walkable-neighbours.
        for (nq, nr) in hexgrid.walkable_neighbors(tile.q, tile.r):
            nt = self.get_tile(nq, nr)
            if nt.state == ROAD:
                return True
            if nt.passable():
                d = self.dist_to_road(nq, nr, reach - 1)
                if d is not None:
                    return True
        return False

    # ------------------------------------------------------------------ transitions
    def mine(self, tile):
        """Rock -> Rubble; drop ore on the tile if the rock was ore-rich."""
        tile.state = RUBBLE
        tile.marked = False
        if tile.ore_type:
            key = tile.ore_type      # full resource key (iron_ore / copper_ore / lithium_salt)
            tile.drops[key] = tile.drops.get(key, 0) + tile.ore_amount
        self._mark_modified(tile)

    def clean(self, tile):
        """Rubble -> Excavated, leaving a rubble pile on the tile to be hauled."""
        tile.state = EXCAVATED
        tile.drops["rubble"] = tile.drops.get("rubble", 0) + config.CLEAN_RUBBLE_YIELD
        self._mark_modified(tile)

    def build_road(self, tile):
        """Excavated -> Road."""
        tile.state = ROAD
        self.road_tiles.add((tile.q, tile.r))
        self._mark_modified(tile)

    def take_drop(self, tile):
        """Remove and return every pile sitting on a tile as a dict (or {})."""
        drops = tile.drops
        if drops:
            tile.drops = {}
            self._mark_modified(tile)
        return drops

    def take_drop_capped(self, tile, cap):
        """Remove up to `cap` total units from a tile's piles; return what was
        taken as a dict. Leaves any remainder on the tile."""
        taken = {}
        left = cap
        for res in list(tile.drops.keys()):
            if left <= 0:
                break
            amt = min(tile.drops[res], left)
            if amt <= 0:
                continue
            taken[res] = taken.get(res, 0) + amt
            tile.drops[res] -= amt
            left -= amt
            if tile.drops[res] <= 0:
                del tile.drops[res]
        if taken:
            self._mark_modified(tile)
        return taken
