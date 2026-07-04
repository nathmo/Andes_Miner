"""
save.py — JSON save/load.

Only the diff from the procedural map is stored: the world seed plus every tile
the player has changed, the buildings, pending jobs, stockpile, agents, and
camera. On load we regenerate the map from the seed and re-apply the diff, so
saves stay tiny even on an effectively infinite map.

Note: under pygbag (web) this writes to the browser's virtual filesystem; it
persists for the session and, where the host enables it, across reloads.
"""

import json
import os

import config
from game import Game
from buildings import Building
from tiles import ROAD
from jobs import CONSTRUCT


def save_game(game, path=config.SAVE_FILE):
    tiles = []
    for (q, r) in game.world.modified:
        t = game.world.get_tile(q, r)
        tiles.append({"q": q, "r": r, "rock": t.rock, "state": t.state,
                      "marked": t.marked, "ore": t.ore})
    data = {
        "seed": game.world.seed,
        "hq": list(game.world.hq),
        "tiles": tiles,
        "buildings": [{"btype": b.btype, "q": b.q, "r": b.r,
                       "built": b.built, "progress": b.progress, "enabled": b.enabled}
                      for b in game.buildings],
        "jobs": [{"jtype": j.jtype, "q": j.q, "r": j.r}
                 for j in game.jobs.jobs],
        "inv": game.economy.inv,
        "jammies": game.economy.jammies,
        "coffee": game.economy.coffee,
        "salary_t": game._salary_t,
        "wages_due": game.wages_due,
        "num_workers": game.num_workers,
        "vehicles": [{"kind": v.kind, "q": v.hex[0], "r": v.hex[1]} for v in game.vehicles],
        "camera": ({"x": game.camera.x, "y": game.camera.y, "zoom": game.camera.zoom}
                   if game.camera is not None else {}),
        "speed_index": game.speed_index,
        "paused": game.paused,
    }
    with open(path, "w") as f:
        json.dump(data, f)
    return True


def load_game(path=config.SAVE_FILE, camera=None):
    if not os.path.isfile(path):
        return None
    with open(path) as f:
        data = json.load(f)

    game = Game(seed=data["seed"], camera=camera)
    game.world.hq = tuple(data.get("hq", [0, 0]))

    # re-apply tile diffs
    for td in data["tiles"]:
        t = game.world.get_tile(td["q"], td["r"])
        t.rock = td["rock"]
        t.state = td["state"]
        t.marked = td.get("marked", False)
        t.ore = td.get("ore")
        game.world.modified.add((td["q"], td["r"]))
    # rebuild road cache
    game.world.road_tiles = {(q, r) for (q, r) in game.world.modified
                             if game.world.get_tile(q, r).state == ROAD}

    # buildings
    game.buildings = []
    for bd in data["buildings"]:
        b = Building(bd["btype"], bd["q"], bd["r"], built=bd["built"])
        b.progress = bd.get("progress", 1.0 if bd["built"] else 0.0)
        b.enabled = bd.get("enabled", True)
        game.world.get_tile(bd["q"], bd["r"]).building = b
        game.buildings.append(b)

    # jobs (recreate pending designations)
    game.jobs.jobs = []
    game.jobs._by_tile = {}
    for jd in data["jobs"]:
        data_extra = None
        if jd["jtype"] == CONSTRUCT:
            t = game.world.get_tile(jd["q"], jd["r"])
            if t.building:
                data_extra = {"building": t.building}
        game.jobs.add(jd["jtype"], jd["q"], jd["r"], data_extra)

    # economy
    game.economy.inv = {res: data["inv"].get(res, 0) for res in config.RESOURCES}
    game.economy.jammies = data.get("jammies", config.JAMMIES_START)
    game.economy.coffee = data.get("coffee", config.COFFEE_START)
    game._salary_t = data.get("salary_t", 0.0)
    game.wages_due = data.get("wages_due", False)

    # agents
    game.num_workers = data["num_workers"]
    game.vehicles = []
    from entities import Agent
    for vd in data["vehicles"]:
        game.vehicles.append(Agent(vd["kind"], vd["q"], vd["r"]))
    game.foot_workers = []
    game._reconcile_agents()

    # camera / time
    if camera is not None:
        cam = data.get("camera", {})
        camera.x = cam.get("x", camera.x)
        camera.y = cam.get("y", camera.y)
        camera.zoom = cam.get("zoom", camera.zoom)
    game.speed_index = data.get("speed_index", 0)
    game.paused = data.get("paused", False)
    return game
