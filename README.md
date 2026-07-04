# Andes — a chill hex mining game

[![Build desktop apps](https://github.com/nathmo/Andes_Miner/actions/workflows/build.yml/badge.svg)](https://github.com/nathmo/Andes_Miner/actions/workflows/build.yml)

You are the **Overseer**: a camera over an endless Andean slope. Mark rock for
mining, and your workers dig it out, haul the ore home, clear rubble, and lay
roads. Refine ore into metal, build a vehicle workshop, and grow from three
workers with hand tools into a fleet of mining machines. No win, no lose — build
at your own pace.

![Andes gameplay: roads radiating from HQ across an Andean slope of shaded hex cubes](docs/screenshot.png)

Blend of **Lego Rock Raiders** (dig, haul, vehicles) and **Factorio** (roads,
processing chains). Built in plain, readable Python with **pygame-ce**.

## The slope / movement rule
Tiles are pointy-top hexes shaded as isometric cubes. The two **vertical** edges
(straight east/west) are **blocked** — you move only across the four slanted
edges (NE/NW/SE/SW), so every step reads as climbing stairs up or down the
slope. The map still connects: going "east" is a NE→SE zig-zag.

## Controls
- **Mine/Clean tool** — LMB marks rock for mining (must be within 2 tiles of a
  road); drag to box-mark many. On rubble it orders a clean-up. RMB cancels.
- **Road tool** — LMB (or drag) lays road on excavated tiles.
- **Build tool** — pick a building in the right panel, LMB to place it.
- **Pan tool / MMB / drag** — pan. **WASD / arrows** also pan. **Wheel** zooms.
- **Home button / H** — recenter the view on HQ so panning can't lose you.
- **Hover any tile** — the info box shows rock hardness (Soft/Medium/Hard), what
  ore it holds (iron/copper/none), and whether it's in mining range.
- **Click a building** — opens its panel; toggle it on/off there.
- **Space** pause · **1 / 2 / 3** speed · **F5** save · **F9** load · **Esc** pan tool.

## Loop
Cleaning rubble yields **rubble** — the bootstrap material. Your first **Simple
Oven** and every **Road** are paid for in rubble, so you're never stuck needing
metal before you can make metal. From there:

Mine → clean rubble (→ rubble) → ore drops hauled to HQ → build an **Oven**
(ore→metal) → get iron & copper → build a **Vehicle Workshop** → manufacture
mining machines, bulldozers, transporters, up to the **Mega Machine** → add a
**Crusher** + **Arc Furnace** to double your metal yield → recruit more workers.
Every vehicle needs one worker to crew it; spare workers labour on foot.

**Automation & roads.** You only ever *order* two things: **mining** (mark the
rock) and **road building**. Everything else self-organises — transporters
auto-haul ore, bulldozers auto-clear rubble, and workers only step in on those
jobs when you haven't built a vehicle for them yet (so you don't waste hands on
work a machine could do). Lay **roads** to move faster; loose **rubble** slows
everyone down. And once you build the **Arc Furnace**, the poor-yield **Oven**
auto-stops so ore isn't wasted (you can force it back on from its panel).

## Money & upkeep — jammies & iced coffee
Sell any stockpiled resource for **jammies** (the game's money) from the MARKET
panel, at any time. Spend jammies on **iced coffee**. Every payday your workers
drink coffee as their salary — run out and the crew goes **on strike** until you
can pay them again, so keep selling to keep the coffee flowing. Prices, payday
interval, and coffee cost are all in [`config.py`](config.py).

## Download & play
CI builds a Windows `.exe`, a Debian/Ubuntu `.deb`, and a macOS `.app` on every
push (see the badge above).
- **Tagged releases** — download a build from the
  [Releases page](https://github.com/nathmo/Andes_Miner/releases). Push a
  `v*` tag (e.g. `v1.0.0`) and the workflow attaches all three there.
- **Latest commit** — the same three artifacts hang off each successful run on
  the [Actions tab](https://github.com/nathmo/Andes_Miner/actions) (open a run →
  *Artifacts*; you must be signed in to GitHub to download them).

Install notes: on Linux `sudo dpkg -i andes_*.deb` then run `andes`. macOS builds
are unsigned, so the first launch needs a right-click → *Open* to clear
Gatekeeper.

## Run (desktop)
```
python -m pip install -r requirements.txt
python main.py
```

## Build for the web (itch.io)
Uses [pygbag](https://pypi.org/project/pygbag/) to compile to WASM. The code is
pure Python with no C extensions, so it ports cleanly.
```
python -m pip install pygbag
python -m pygbag main.py         # serves a local test build at http://localhost:8000
python -m pygbag --build main.py # produces build/web -> zip its contents for itch.io
```

## Build a desktop executable
The [build workflow](.github/workflows/build.yml) does this for all three OSes;
to build locally:
```
python -m pip install pyinstaller
pyinstaller --onefile --windowed --name Andes --add-data "assets;assets" main.py
```
(On macOS/Linux use `--add-data "assets:assets"`; on macOS drop `--onefile` to
get a `.app` bundle.)

## Art
Starter sprites live in `assets/` — one per worker, vehicle, and building, plus
one per **tile** (each rock type as an isometric cube, and road / rubble /
excavated floor). Edit or replace any of them and the game picks up the change
on next launch. Delete a PNG to fall back to the code-drawn shape. To regenerate
the whole set from scratch:
```
python make_assets.py
```
Filenames are the entity/tile key (e.g. `miner_s.png`, `oven.png`,
`tile_granite.png`, `tile_road.png`).

**Tile dimensions matter:** tiles are pointy-top hexes and must keep the ratio
`W : H = sqrt(3) : 2` (e.g. 111×128) with the hexagon filling the canvas
edge-to-edge — otherwise they won't line up on the grid. The generated PNGs are
exact templates to trace; full details in [`assets/.keep`](assets/.keep).

## Tuning
Every number (mining times, ore yields, costs, speeds, colours) lives in
[`config.py`](config.py). Change balance there without touching game logic.

## Layout
`main` loop · `game` wiring · `world`/`worldgen`/`tiles` map · `hexgrid` math ·
`camera` · `render` · `pathfinding` · `jobs` · `entities` · `buildings` ·
`economy` · `ui` · `input` · `assets` · `save`.
