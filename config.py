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

# Rolling backups: every BACKUP_INTERVAL a snapshot is taken and rotated Hanoi-style
# across BACKUP_SLOTS, so you keep roughly 2, 4, 8, ... 256-min-old restore points.
BACKUP_INTERVAL = 120.0          # real seconds between rolling backups
BACKUP_SLOTS = 8
BACKUP_FILE = "andes_backup_{}.json"

# Day/night: the sun rises and sets over DAY_LENGTH sim-seconds. Sun output (0 at
# night, 1 at noon) both dims the world and scales Solar Array yield.
DAY_LENGTH = 120.0
NIGHT_MAX_ALPHA = 115            # deepest-night darkening overlay alpha

# ------------------------------------------------------------------ hex geometry
HEX_SIZE = 34                     # centre-to-vertex radius at zoom 1.0 (pointy-top)
CHUNK_SIZE = 16                   # hexes per chunk edge (chunk = CHUNK_SIZE x CHUNK_SIZE)

MIN_ZOOM = 0.35
MAX_ZOOM = 2.4
ZOOM_STEP = 1.12                  # multiplier per wheel notch

# Splash intro: open far out on the summit, then zoom down to HQ on SPACE.
SPLASH_SUMMIT_R = 24              # how far up the slope the opening view sits
SPLASH_ZOOM_DUR = 1.8            # seconds for the zoom-in animation

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
# key: (display name, base RGB, mine_time s, drop resource-key or None, drop amount)
ROCK_TYPES = {
    "andesite":  ("Andesite",  (150, 150, 158), 1.6, None,           0),  # easy
    "diorite":   ("Diorite",   (198, 200, 206), 3.0, None,           0),  # medium
    "granite":   ("Granite",   (196, 158, 150), 5.0, None,           0),  # hard
    "basalt":    ("Basalt",    ( 74,  76,  92), 3.0, "iron_ore",     2),  # medium, iron-rich
    "rhyolite":  ("Rhyolite",  (206, 172, 132), 1.8, "copper_ore",   2),  # easy, copper-rich
    "spodumene": ("Spodumene", (176, 202, 176), 3.6, "lithium_salt", 1),  # rare, lithium ore
}

# ------------------------------------------------------------------ world gen
WORLD_SEED = 1337                 # default seed (New Game can randomise via args)

# Villages: the overarching goal is to connect these outposts to your road network.
# Spread wide so they sit far apart (quadrupled) — connecting one is a real trek.
NUM_VILLAGES = 7
VILLAGE_SPREAD_Q = 256           # lateral (E-W) scatter of village sites
VILLAGE_SPREAD_R = 64            # vertical (up/down slope) scatter
VILLAGE_CONNECT_RANGE = 2       # a road within N steps counts the village as linked
# Base rock selection thresholds on fbm noise in [0,1]:
#   n < GRANITE_T             -> granite
#   GRANITE_T <= n < DIORITE_T-> diorite
#   else                      -> andesite
GRANITE_T = 0.36
DIORITE_T = 0.62
# Ore veins: a separate low-freq noise; above the threshold a cell becomes an
# ore-rich rock, iron vs copper chosen by a third noise's sign.
VEIN_T = 0.66
LITHIUM_T = 0.72                  # inside a vein, above this a patch becomes spodumene (rare)
NOISE_BASE_FREQ = 0.09            # higher = smaller rock-type blobs
NOISE_VEIN_FREQ = 0.05            # lower = bigger, rarer veins
NOISE_OCTAVES = 3

# ------------------------------------------------------------------ tiles / states
# TileState values (see tiles.py). Passable states for pathfinding:
PASSABLE_STATES = (1, 2, 3)       # RUBBLE, EXCAVATED, ROAD
MINE_ROAD_RANGE = 2               # baseline reach (hand workers / small miner): road within N steps
MAX_MINE_REACH = 4               # largest tier reach (mega); keeps far MINE jobs valid to claim

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
# Tiers get MUCH pricier and a bit slower as they grow (item 16), so a single
# top machine can't saturate everything — you're nudged to run several.
VEHICLES = {
    "transporter_s": dict(name="Small Transporter", tier="small", speed=85,  carry=1, mine_mult=0, clean_mult=0, jobs=("HAUL",),
                          cost={"iron": 2}, color=(90, 150, 220)),
    "miner_s":       dict(name="Small Mining Machine", tier="small", speed=64, carry=0, mine_mult=2.5, clean_mult=0, mine_reach=2, jobs=("MINE",),
                          cost={"iron": 3, "copper": 1}, color=(220, 150, 80)),
    "dozer_s":       dict(name="Small Bulldozer", tier="small", speed=72, carry=0, mine_mult=0, clean_mult=2.5, jobs=("CLEAN",),
                          cost={"iron": 2, "copper": 1}, color=(220, 200, 90)),
    "truck_m":       dict(name="Medium Truck", tier="medium", speed=105, carry=3, mine_mult=0, clean_mult=0, jobs=("HAUL",),
                          cost={"iron": 6, "copper": 3, "silicon": 1}, color=(70, 120, 200)),
    "excavator_m":   dict(name="Medium Excavator", tier="medium", speed=74, carry=0, mine_mult=4.5, clean_mult=0, mine_reach=3, jobs=("MINE",),
                          cost={"iron": 9, "copper": 5, "silicon": 1}, color=(230, 130, 60)),
    "dozer_m":       dict(name="Medium Bulldozer", tier="medium", speed=90, carry=0, mine_mult=0, clean_mult=4.5, jobs=("CLEAN",),
                          cost={"iron": 8, "copper": 4, "silicon": 1}, color=(230, 210, 70)),
    "paver_m":       dict(name="Medium Road Paver", tier="medium", speed=88, carry=1, mine_mult=0, clean_mult=0, jobs=("BUILD_ROAD",),
                          cost={"iron": 8, "copper": 4, "silicon": 1}, color=(140, 142, 150)),
    "mega":          dict(name="Mega Machine", tier="big", speed=92, carry=9, mine_mult=6, clean_mult=6, mine_reach=4, jobs=("MINE", "CLEAN", "HAUL"),
                          cost={"iron": 30, "copper": 22, "silicon": 3, "lithium": 2}, color=(200, 90, 200)),
}

# ------------------------------------------------------------------ buildings
# process: consume `inp` from the global stockpile every `time` s -> produce `out`.
# buildable=False marks a structure the player can't place (it starts on the map).
BUILDINGS = {
    "depot":       dict(name="Storage Depot", cost={}, color=(168, 150, 116), buildable=False,
                        process=None, note="Central storage — haulers deliver ore & rubble here"),
    "workshop":    dict(name="Vehicle Workshop", cost={"iron": 5, "copper": 3}, color=(120, 130, 150),
                        process=None, note="Unlocks vehicle manufacturing"),
    "oven":        dict(name="Simple Oven", cost={"rubble": 5}, color=(180, 110, 80),
                        process=[
                            dict(inp={"iron_ore": 2}, out={"iron": 1}, time=6.0),
                            dict(inp={"copper_ore": 2}, out={"copper": 1}, time=6.0),
                        ], note="Ore -> metal, poor yield (2:1)"),
    "crusher":     dict(name="Crusher", cost={"iron": 6, "copper": 3}, color=(130, 120, 110),
                        process=[
                            dict(inp={"iron_ore": 1}, out={"iron_crushed": 1}, time=3.0),
                            dict(inp={"copper_ore": 1}, out={"copper_crushed": 1}, time=3.0),
                        ], note="Crushes ore to boost furnace yield"),
    "arc_furnace": dict(name="Arc Furnace", cost={"iron": 12, "copper": 6}, color=(200, 120, 90),
                        process=[
                            dict(inp={"iron_crushed": 1}, out={"iron": 1}, time=4.0),
                            dict(inp={"copper_crushed": 1}, out={"copper": 1}, time=4.0),
                            dict(inp={"iron_ore": 1}, out={"iron": 1}, time=6.0),
                            dict(inp={"copper_ore": 1}, out={"copper": 1}, time=6.0),
                        ], note="Crushed (or raw) ore -> metal, double yield"),
    "planner":     dict(name="Mining Planner", cost={"iron": 10, "copper": 6}, color=(88, 158, 168),
                        process=None, note="Drag-select ore: auto-mines and auto-roads out to reach it"),
    "cable_station": dict(name="Cable Car Station", cost={"iron": 4, "copper": 2}, color=(120, 150, 172),
                        process=None, on="road",
                        note="On a road, far out: haulers unload here and it cables ore to HQ"),
    "silica_kiln": dict(name="Silica Kiln", cost={"iron": 4, "copper": 2}, color=(150, 160, 172),
                        process=[dict(inp={"rubble": 2}, out={"sio2": 1}, time=3.0)],
                        note="Bakes waste rubble into silica (SiO2)"),
    "solar_foundry": dict(name="Solar Foundry", cost={"iron": 6, "copper": 4}, color=(80, 120, 180),
                        process=[dict(inp={"sio2": 2, "copper": 1}, out={"solar_panel": 1}, time=6.0)],
                        note="SiO2 + copper -> solar panels"),
    "solar_array": dict(name="Solar Array", cost={"solar_panel": 2, "iron": 2}, color=(60, 100, 170),
                        process=None, power_gen=True,
                        note="Generates power from sunlight, cutting your grid bill"),
    "electrolysis": dict(name="Electrolysis Plant", cost={"iron": 8, "copper": 5}, color=(150, 190, 175),
                        process=[dict(inp={"lithium_salt": 1}, out={"lithium": 1}, time=5.0)],
                        note="Lithium salt -> lithium metal"),
    "battery_factory": dict(name="Battery Factory", cost={"iron": 12, "copper": 7, "silicon": 2}, color=(110, 200, 120),
                        process=[dict(inp={"lithium": 2, "copper": 1}, out={"battery_cell": 1}, time=8.0)],
                        note="Lithium + copper -> battery cells (power-hungry)"),
    "battery": dict(name="Grid Battery", cost={"battery_cell": 3, "iron": 4}, color=(90, 185, 110),
                        process=None, storage=True,
                        note="Stores surplus solar to run machines after dark"),
    "warehouse": dict(name="Warehouse", cost={"iron": 6, "rubble": 8}, color=(170, 140, 95),
                        process=None,
                        note="Auto-sells to keep cash & coffee above set thresholds"),
}

# ------------------------------------------------------------------ warehouse auto-trade
AUTO_CASH_MIN = 20               # warehouse tops cash up above this by selling
AUTO_COFFEE_MIN = 5            # ...and keeps coffee above this by buying
AUTO_TRADE_INTERVAL = 1.0     # seconds between auto-trade actions
AUTO_SELL_FIXED = ["rubble", "iron_ore", "copper_ore", "sio2"]   # default sell order
AUTO_SELL_KEEP = {"iron": 5, "copper": 5, "silicon": 2, "lithium": 2}  # never auto-sell below

COL_CABLE = (150, 170, 190)      # the straight cable line drawn back to HQ

# ------------------------------------------------------------------ energy / grid
# Processing machines draw power while running. Solar Arrays generate it; any
# shortfall is auto-bought from the grid with jammies. No cash -> machines stop.
KWH_PRICE = 0.04                 # jammies per unit of grid power per second
SOLAR_ARRAY_OUTPUT = 8.0         # power one Solar Array makes at full sun
BUILDING_POWER = {               # power drawn while a building is processing
    "oven": 4, "crusher": 6, "arc_furnace": 12,
    "silica_kiln": 8, "solar_foundry": 10, "electrolysis": 14, "battery_factory": 16,
}
BATTERY_CAPACITY = 60.0          # energy stored per Grid Battery
BATTERY_CHARGE_EFF = 0.9        # fraction of surplus solar that makes it into storage

# Grid carbon intensity (kg CO2 / MWh). Starts dirty; reinjecting surplus clean
# power greens it for everyone, otherwise it drifts back toward the dirty start.
GRID_CARBON_START = 420.0
CARBON_MIN = 30.0
CARBON_EXPORT_DECAY = 0.9       # greening per unit of exported power
CARBON_REVERT = 0.5            # re-dirtying per second when not exporting
CO2_SCALE = 0.0009             # kg CO2 per (power-second * carbon intensity)
EMISS_HISTORY = 64             # samples kept for the emissions graph

# ------------------------------------------------------------------ auto-planner
# With a built Mining Planner, box-selecting rock also plans dig+road corridors
# out to ore beyond road range. Caps keep a huge selection from stalling a frame.
PLAN_MAX_ROUTES = 40             # corridors planned per box-select
PLAN_MAX_EXPAND = 2500           # Dijkstra node budget per corridor

# A building type is auto-disabled ("obsolete") while any of these built+enabled
# types exist, so ore isn't wasted in the poor-yield oven once you have the arc
# furnace. The player can still force it back on from the building panel.
OBSOLETED_BY = {
    "oven": ["arc_furnace"],
}

# Resources tracked in the global stockpile (order = HUD display order). The HUD
# only shows resources you currently hold, so the list can grow without clutter.
RESOURCES = ["rubble", "iron_ore", "copper_ore", "iron_crushed", "copper_crushed",
             "iron", "copper", "sio2", "silicon", "lithium_salt", "lithium",
             "solar_panel", "battery_cell"]
RESOURCE_LABEL = {
    "rubble": "Rubble",
    "iron_ore": "Fe ore", "copper_ore": "Cu ore",
    "iron_crushed": "Fe crushed", "copper_crushed": "Cu crushed",
    "iron": "Iron", "copper": "Copper",
    "sio2": "Silica", "silicon": "Silicon",
    "lithium_salt": "Li salt", "lithium": "Lithium",
    "solar_panel": "Solar", "battery_cell": "Battery",
}
# Short symbols for tight cost strings (e.g. "5Fe 3Cu"). Iron/copper use their
# chemical symbols (Fe/Cu); anything missing falls back to its first two letters.
RESOURCE_ABBR = {
    "rubble": "Ru", "iron_ore": "FeO", "copper_ore": "CuO",
    "iron_crushed": "FeX", "copper_crushed": "CuX",
    "iron": "Fe", "copper": "Cu", "sio2": "SiO", "silicon": "Si",
    "lithium_salt": "LiS", "lithium": "Li", "solar_panel": "Sp", "battery_cell": "Bc",
}
RESOURCE_COLOR = {
    "rubble": (150, 140, 128),
    "iron_ore": COL_ORE_IRON, "copper_ore": COL_ORE_COPPER,
    "iron_crushed": (230, 150, 110), "copper_crushed": (150, 210, 175),
    "iron": (215, 215, 220), "copper": (225, 150, 95),
    "sio2": (200, 205, 215), "silicon": (128, 132, 148),
    "lithium_salt": (170, 205, 170), "lithium": (150, 215, 195),
    "solar_panel": (70, 120, 195), "battery_cell": (120, 205, 120),
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
    "sio2": 2, "silicon": 8, "lithium_salt": 3, "lithium": 10,
    "solar_panel": 12, "battery_cell": 20,
}
COFFEE_START = 20                 # iced coffees in stock at the start
COFFEE_PRICE = 1                 # jammies per iced coffee
COFFEE_BATCH = 3                 # coffees bought per click
WAGE_ACTIONS_PER_COFFEE = 10     # jobs a worker finishes per iced coffee it drinks

# Buy materials from the market: the metals (iron, copper) to unblock building
# when you're mining-starved, plus silicon/lithium you can't make early. Buy price
# sits above sell price (a spread). Higher-tier vehicles need some bought in.
BUYABLE = ["iron", "copper", "silicon", "lithium"]
BUY_BATCH = 3                     # units bought per click
BUY_PRICES = {                   # base jammies per unit bought (item 23 makes it drift)
    "silicon": 12, "lithium": 16, "sio2": 4, "iron": 10, "copper": 12,
}

# ------------------------------------------------------------------ stock market
# Prices drift: a random walk that mean-reverts to the base, plus a production
# trend (selling a resource depresses its price, buying lifts it). A floor keeps
# everything worth at least 1 jammy so you can always sell for coffee money.
MARKET_TICK = 2.0                # seconds between price updates
PRICE_MIN_MULT = 0.45           # floor multiplier on the base price
PRICE_MAX_MULT = 2.2            # ceiling multiplier
PRICE_DRIFT = 0.05              # random-walk step each market tick
PRICE_REVERT = 0.03            # pull back toward the base each tick
SELL_PRICE_IMPACT = 0.02       # price drop per unit you sell
BUY_PRICE_IMPACT = 0.03        # price rise per unit you buy
PRICE_HISTORY = 64             # samples kept per resource for the trend graph
