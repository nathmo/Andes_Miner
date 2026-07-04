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

Press **SPACE** at the summit splash to zoom in and start.

## Controls
- **Excavate tool** (`M`) — LMB marks rock for mining (within your machines'
  reach of a road); drag to box-mark many. With a **Mining Planner** built,
  box-selecting ore beyond reach auto-plans the dig + road corridor out to it.
  RMB cancels.
- **Clean tool** (`C`) — LMB (or drag) marks rubble for clearing; a worker or
  bulldozer hauls it off, leaving excavated floor. RMB cancels.
- **Road tool** (`R`) — LMB (or drag) plans road on excavated tiles; a builder
  carries rubble to the site and lays it.
- **Right panel tabs** — the side panel is split into **Build** (place buildings),
  **Fleet** (manufacture vehicles, recruit workers), and **Trade** (buy coffee,
  sell/buy materials). Picking the Build tool jumps to the Build tab; the wheel
  scrolls a tab if its list is taller than the panel. Your jammies and coffee
  always show in the top bar.
- **Build** — pick a building on the Build tab and LMB to place it (no separate
  Build button in the bottom bar; the Build tab drives it).
- **Market button** — live prices, trend sparklines, grid carbon + emissions graph.
- **Settings button** — toggle sky ambiance (clouds, condors) on or off.
- **Pan tool / MMB / drag** — pan. **WASD / arrows** also pan. **Wheel** zooms.
- **Home button / H** — recenter the view on HQ so panning can't lose you.
- **Hover any tile** — the info box names it (e.g. "Diorite rubble", "Excavated
  basalt"), shows hardness and what solid rock drops, mining range, and any piles
  sitting on it.
- **Click a building** — opens its panel; toggle it, or set a Warehouse's auto-sell.
- **Space** pause · **1 / 2 / 3** speed · **F5** save · **F9** load/roll-back menu · **Esc** pan tool.

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

## The bigger game — goal, market, energy
- **Goal.** Villages are scattered across the slope; the objective is to reach and
  link each one to your road network (top bar tracks progress), rewarding lateral
  exploration.
- **Market.** Sell any resource for jammies and buy materials from the **Trade**
  tab — the metals **iron** and **copper** to unblock building when you're
  mining-starved, plus **silicon** and **lithium** you can't make early (needed
  for the better machines). Prices drift on a small stock market: your own trading
  and a random walk move them, floored so you can always raise coffee money.
- **Energy.** Machines draw power. Buy it from the grid (auto, with jammies) or
  build **Solar Arrays** — a full material chain runs rubble → SiO2 → solar panels,
  and lithium (from spodumene via an Electrolysis Plant) feeds **Battery Factories**
  and **Grid Batteries** that store daytime solar for the night. Reinjecting clean
  surplus greens the grid's carbon intensity for everyone; run out of cash and the
  machines stop (workers keep going). A **day/night cycle** dims the world and sets
  solar yield. A **Warehouse** auto-sells to hold cash and coffee above thresholds.

## Money & upkeep — jammies & iced coffee
Sell any stockpiled resource for **jammies** (the game's money) from the **Trade**
tab. Spend jammies on **iced coffee** — your workers' wages. Wages are
**action-based, not timed**: a worker drinks one iced coffee for roughly every ten
jobs it finishes, so idle workers cost nothing and there's no clock pressure. Run
out of coffee and that worker pauses until you can pay it. Prices and rates all
live in [`config.py`](config.py).

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
`main` loop · `splash` intro · `game` wiring · `world`/`worldgen`/`tiles` map ·
`hexgrid` math · `camera` · `render` · `environment` (sky) · `pathfinding` ·
`jobs` · `entities` · `buildings` · `economy` (stockpile/market/energy) · `ui` ·
`input` · `assets` · `save` (+ rolling backups).
