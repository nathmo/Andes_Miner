"""
tiles.py — rock types, tile state, and the Tile object.

Tile lifecycle:  ROCK --mine--> RUBBLE --clean--> EXCAVATED --build--> ROAD
Mining ore-rich rock and cleaning rubble both leave a physical *drop* on the
tile (ore / rubble) that a hauler must carry to storage. `tile.drops` is a dict
of resource-key -> amount (e.g. {"rubble": 1} or {"copper_ore": 2}).
"""

import config

# Tile states.
ROCK = 0
RUBBLE = 1
EXCAVATED = 2
ROAD = 3

STATE_NAME = {ROCK: "Rock", RUBBLE: "Rubble", EXCAVATED: "Excavated", ROAD: "Road"}


class Tile:
    __slots__ = ("q", "r", "rock", "state", "marked", "drops", "building", "job")

    def __init__(self, q, r, rock, state=ROCK):
        self.q = q
        self.r = r
        self.rock = rock            # rock-type key (see config.ROCK_TYPES)
        self.state = state
        self.marked = False         # queued by the overseer for mining
        self.drops = {}             # resource-key -> amount of piles sitting here
        self.building = None        # Building instance sitting on this tile (or None)
        self.job = None             # active job reserving this tile (or None)

    # -- convenience -------------------------------------------------------
    @property
    def rockinfo(self):
        return config.ROCK_TYPES[self.rock]

    @property
    def name(self):
        return self.rockinfo[0]

    @property
    def base_color(self):
        return self.rockinfo[1]

    @property
    def excavated_color(self):
        """Dug-floor colour, tinted toward this rock so excavated andesite and
        excavated basalt read differently. Shared with make_assets."""
        base = self.rockinfo[1]
        mix = tuple(int(0.55 * e + 0.45 * b) for e, b in zip(config.COL_EXCAVATED, base))
        return tuple(int(c * 0.88) for c in mix)

    @property
    def mine_time(self):
        return self.rockinfo[2]

    @property
    def hardness_label(self):
        mt = self.mine_time
        if mt <= config.HARDNESS_SOFT_MAX:
            return "Soft"
        if mt <= config.HARDNESS_MED_MAX:
            return "Medium"
        return "Hard"

    @property
    def ore_type(self):
        return self.rockinfo[3]     # None / "iron" / "copper"

    @property
    def ore_amount(self):
        return self.rockinfo[4]

    def passable(self):
        return self.state in config.PASSABLE_STATES

    def is_rock(self):
        return self.state == ROCK

    def __repr__(self):
        return f"Tile({self.q},{self.r},{self.rock},{STATE_NAME[self.state]})"
