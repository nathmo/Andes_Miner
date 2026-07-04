"""
config.py — ALL tunable numbers and the colour palette live here.

Change balance, costs, speeds, and colours in this one file without touching
game logic anywhere else. Grouped by topic. Times are in seconds, speeds in
pixels/second (at zoom 1.0), distances in hex steps.
"""

# ------------------------------------------------------------------ window / loop
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 800
FPS = 60
TITLE = "Andes — Overseer"

# Real-time simulation speed multipliers the player can toggle (1x/2x/3x).
SPEED_STEPS = [1.0, 2.0, 3.0]

AUTOSAVE_INTERVAL = 90.0          # seconds between auto-saves
SAVE_FILE = "andes_save.json"

# ------------------------------------------------------------------ hex geometry
HEX_SIZE = 34                     # centre-to-vertex radius at zoom 1.0 (pointy-top)
CHUNK_SIZE = 16                   # hexes per chunk edge (chunk = CHUNK_SIZE x CHUNK_SIZE)

MIN_ZOOM = 0.35
MAX_ZOOM = 2.4
ZOOM_STEP = 1.12                  # multiplier per wheel notch

# ------------------------------------------------------------------ camera
CAM_PAN_SPEED = 500               # px/sec for WASD / arrow panning (screen space)
CAM_EDGE_PAN = False              # edge-of-screen panning (off by default)
CAM_EDGE_MARGIN = 24

# ------------------------------------------------------------------ palette (RGB)
COL_BG = (26, 28, 34)
COL_GRID = (0, 0, 0)
COL_TEXT = (232, 236, 242)
COL_TEXT_DIM = (150, 156, 168)
COL_PANEL = (34, 38, 46)
COL_PANEL_LIGHT = (48, 54, 64)
COL_PANEL_EDGE = (70, 78, 92)
COL_BUTTON = (58, 66, 80)
COL_BUTTON_HOVER = (78, 90, 108)
COL_BUTTON_ON = (86, 132, 96)
COL_ACCENT = (240, 200, 90)

COL_MARK = (240, 90, 80)          # tile marked for mining
COL_CLEAN_MARK = (110, 205, 235)  # rubble tile scheduled for cleaning
COL_ROAD_MARK = (240, 205, 120)   # excavated tile scheduled for road building
COL_MINEABLE = (240, 200, 90)     # subtle hint: markable rock in range
COL_SELECT_RECT = (240, 220, 120)
COL_PATH = (120, 200, 240)

COL_ROAD = (96, 92, 86)
COL_EXCAVATED = (120, 108, 96)
COL_RUBBLE = (92, 84, 78)

COL_ORE_IRON = (208, 120, 72)
COL_ORE_COPPER = (110, 190, 150)

# Cube-face shading multipliers applied to a rock's base colour.
SHADE_TOP = 1.00                  # top face  (lightest — catches the light)
SHADE_LEFT = 0.72                 # left face (mid shade)
SHADE_RIGHT = 0.50                # right face (darkest — in shadow)

# ------------------------------------------------------------------ rock types
# key: (display name, base RGB, mine_time seconds at hand-speed, ore or None, ore_amount)
ROCK_TYPES = {
    "andesite":  ("Andesite",  (150, 150, 158), 1.6, None,     0),  # easy
    "diorite":   ("Diorite",   (198, 200, 206), 3.0, None,     0),  # medium
    "granite":   ("Granite",   (196, 158, 150), 5.0, None,     0),  # hard
    "basalt":    ("Basalt",    ( 74,  76,  92), 3.0, "iron",   2),  # medium, iron-rich
    "rhyolite":  ("Rhyolite",  (206, 172, 132), 1.8, "copper", 2),  # easy, copper-rich
}

# ------------------------------------------------------------------ world gen
WORLD_SEED = 1337                 # default seed (New Game can randomise via args)
# Base rock selection thresholds on fbm noise in [0,1]:
#   n < GRANITE_T             -> granite
#   GRANITE_T <= n < DIORITE_T-> diorite
#   else                      -> andesite
GRANITE_T = 0.36
DIORITE_T = 0.62
# Ore veins: a separate low-freq noise; above the threshold a cell becomes an
# ore-rich rock, iron vs copper chosen by a third noise's sign.
VEIN_T = 0.66
NOISE_BASE_FREQ = 0.09            # higher = smaller rock-type blobs
NOISE_VEIN_FREQ = 0.05            # lower = bigger, rarer veins
NOISE_OCTAVES = 3

# ------------------------------------------------------------------ tiles / states
# TileState values (see tiles.py). Passable states for pathfinding:
PASSABLE_STATES = (1, 2, 3)       # RUBBLE, EXCAVATED, ROAD
MINE_ROAD_RANGE = 2               # rock is mineable if a ROAD is within N walkable steps

# Terrain traversal speed multipliers, keyed by TileState int (RUBBLE=1,
# EXCAVATED=2, ROAD=3). Roads speed everyone up; loose rubble slows them down.
TERRAIN_SPEED = {1: 0.55, 2: 1.0, 3: 1.6}

# Rock hardness display buckets, by mine_time seconds.
HARDNESS_SOFT_MAX = 2.2
HARDNESS_MED_MAX = 4.0

# ------------------------------------------------------------------ agents / labour
START_WORKERS = 3
WORKER_MOVE_SPEED = 62            # px/sec at zoom 1.0
WORKER_CARRY = 1                  # ore stacks a hand worker carries
HAND_MINE_MULT = 1.0             # hand tools baseline
HAND_CLEAN_TIME = 1.2             # seconds to clear one rubble tile by hand
BUILD_ROAD_TIME = 1.0             # seconds to lay one road tile
CONSTRUCT_TIME = 4.0             # seconds of on-site work to raise a building

# Cleaning rubble yields the "rubble" building material. This is the bootstrap
# resource: you can raise roads and your first oven from rubble alone, so you
# never get stuck needing metal before you can make metal.
CLEAN_RUBBLE_YIELD = 1
ROAD_COST = {"rubble": 1}        # rubble spent to lay one road tile

RECRUIT_COST = {"iron": 2}       # cost to hire one more worker

# Vehicle stats. jobs: which job kinds this unit can perform.
#   mine_mult / clean_mult scale the base times (higher = faster).
#   speed px/sec, carry = ore stacks per haul trip.
VEHICLES = {
    "transporter_s": dict(name="Small Transporter", tier="small", speed=95,  carry=3, mine_mult=0, clean_mult=0, jobs=("HAUL",),
                          cost={"iron": 2}, color=(90, 150, 220)),
    "miner_s":       dict(name="Small Mining Machine", tier="small", speed=70, carry=0, mine_mult=3, clean_mult=0, jobs=("MINE",),
                          cost={"iron": 3, "copper": 1}, color=(220, 150, 80)),
    "dozer_s":       dict(name="Small Bulldozer", tier="small", speed=80, carry=0, mine_mult=0, clean_mult=3, jobs=("CLEAN",),
                          cost={"iron": 2, "copper": 1}, color=(220, 200, 90)),
    "truck_m":       dict(name="Medium Truck", tier="medium", speed=115, carry=6, mine_mult=0, clean_mult=0, jobs=("HAUL",),
                          cost={"iron": 5, "copper": 2}, color=(70, 120, 200)),
    "excavator_m":   dict(name="Medium Excavator", tier="medium", speed=80, carry=0, mine_mult=6, clean_mult=0, jobs=("MINE",),
                          cost={"iron": 6, "copper": 3}, color=(230, 130, 60)),
    "dozer_m":       dict(name="Medium Bulldozer", tier="medium", speed=100, carry=0, mine_mult=0, clean_mult=6, jobs=("CLEAN",),
                          cost={"iron": 5, "copper": 2}, color=(230, 210, 70)),
    "mega":          dict(name="Mega Machine", tier="big", speed=100, carry=8, mine_mult=8, clean_mult=8, jobs=("MINE", "CLEAN", "HAUL"),
                          cost={"iron": 15, "copper": 10}, color=(200, 90, 200)),
}

# ------------------------------------------------------------------ buildings
# process: consume `inp` from the global stockpile every `time` s -> produce `out`.
BUILDINGS = {
    "workshop":    dict(name="Vehicle Workshop", cost={"iron": 5, "copper": 3}, color=(120, 130, 150),
                        process=None, note="Unlocks vehicle manufacturing"),
    "oven":        dict(name="Simple Oven", cost={"rubble": 5}, color=(180, 110, 80),
                        process=[
                            dict(inp={"iron_ore": 2}, out={"iron": 1}, time=4.0),
                            dict(inp={"copper_ore": 2}, out={"copper": 1}, time=4.0),
                        ], note="Ore -> metal, poor yield (2:1)"),
    "crusher":     dict(name="Crusher", cost={"iron": 4, "copper": 2}, color=(130, 120, 110),
                        process=[
                            dict(inp={"iron_ore": 1}, out={"iron_crushed": 1}, time=2.0),
                            dict(inp={"copper_ore": 1}, out={"copper_crushed": 1}, time=2.0),
                        ], note="Crushes ore to boost furnace yield"),
    "arc_furnace": dict(name="Arc Furnace", cost={"iron": 8, "copper": 4}, color=(200, 120, 90),
                        process=[
                            dict(inp={"iron_crushed": 1}, out={"iron": 1}, time=3.0),
                            dict(inp={"copper_crushed": 1}, out={"copper": 1}, time=3.0),
                            dict(inp={"iron_ore": 1}, out={"iron": 1}, time=4.0),
                            dict(inp={"copper_ore": 1}, out={"copper": 1}, time=4.0),
                        ], note="Crushed (or raw) ore -> metal, double yield"),
}

# A building type is auto-disabled ("obsolete") while any of these built+enabled
# types exist, so ore isn't wasted in the poor-yield oven once you have the arc
# furnace. The player can still force it back on from the building panel.
OBSOLETED_BY = {
    "oven": ["arc_furnace"],
}

# Resources tracked in the global stockpile (order = HUD display order).
RESOURCES = ["rubble", "iron_ore", "copper_ore", "iron_crushed", "copper_crushed", "iron", "copper"]
RESOURCE_LABEL = {
    "rubble": "Rubble",
    "iron_ore": "Fe ore", "copper_ore": "Cu ore",
    "iron_crushed": "Fe crushed", "copper_crushed": "Cu crushed",
    "iron": "Iron", "copper": "Copper",
}
RESOURCE_COLOR = {
    "rubble": (150, 140, 128),
    "iron_ore": COL_ORE_IRON, "copper_ore": COL_ORE_COPPER,
    "iron_crushed": (230, 150, 110), "copper_crushed": (150, 210, 175),
    "iron": (215, 215, 220), "copper": (225, 150, 95),
}

# Starting stockpile so the player can bootstrap the first vehicles/buildings.
START_INVENTORY = {"iron": 0, "copper": 0}

# ------------------------------------------------------------------ money & upkeep
# Sell any stockpiled resource for "jammies" (the game's money). Spend jammies on
# iced coffee, which your workers drink as their salary. Wages are ACTION-based,
# not timed: a worker drinks 1 iced coffee for every WAGE_ACTIONS_PER_COFFEE jobs
# it personally completes, so idle (or striking) workers cost nothing and there
# is no clock pressure. Run out of coffee and a worker pauses until you can pay.
JAMMIES_START = 100
SELL_BATCH = 5                    # units sold per click
SELL_PRICES = {                  # jammies earned per unit sold
    "rubble": 1, "iron_ore": 2, "copper_ore": 2,
    "iron_crushed": 3, "copper_crushed": 3, "iron": 6, "copper": 7,
}
COFFEE_START = 20                 # iced coffees in stock at the start
COFFEE_PRICE = 1                 # jammies per iced coffee
COFFEE_BATCH = 3                 # coffees bought per click
WAGE_ACTIONS_PER_COFFEE = 10     # jobs a worker finishes per iced coffee it drinks
