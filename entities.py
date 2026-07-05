"""
entities.py — workers and vehicles that carry out jobs.

An Agent is a small state machine: IDLE -> (claim job) -> MOVING -> WORKING ->
back to IDLE. Workers do everything slowly by hand; vehicles are faster but
specialised (see config.VEHICLES). Movement is along a path of walkable tiles;
to work a solid tile the agent stands on an adjacent passable tile.
"""

import config
import hexgrid
import pathfinding
from jobs import MINE, CLEAN, BUILD_ROAD, HAUL, CONSTRUCT, WORKER_JOBS
from tiles import RUBBLE, EXCAVATED, ROAD

# Workers prefer order-driven / human-only tasks; hauling and cleaning come last
# and are dropped entirely once a vehicle automates them (see claimable_kinds).
WORKER_PRIORITY = [CONSTRUCT, MINE, BUILD_ROAD, HAUL, CLEAN]


class Agent:
    def __init__(self, kind, q, r):
        self.kind = kind                # "worker" or a config.VEHICLES key
        self.hex = (q, r)
        self.px, self.py = hexgrid.hex_to_pixel(q, r, config.HEX_SIZE)

        if kind == "worker":
            self.speed = config.WORKER_MOVE_SPEED
            self.carry = config.WORKER_CARRY
            self.mine_mult = config.HAND_MINE_MULT
            self.clean_mult = 1.0
            self.mine_reach = config.MINE_ROAD_RANGE
            self._jobs = set(WORKER_JOBS)
        else:
            v = config.VEHICLES[kind]
            self.speed = v["speed"]
            self.carry = v["carry"]
            self.mine_mult = v["mine_mult"] or 1.0
            self.clean_mult = v["clean_mult"] or 1.0
            self.mine_reach = v.get("mine_reach", config.MINE_ROAD_RANGE)
            self._jobs = set(v["jobs"])

        self.state = "IDLE"
        self.job = None
        self.path = []
        self.phase = None               # for HAUL: "pickup" / "deliver"
        self.carrying = None            # dict of resource-key -> amount being hauled
        self.work_timer = 0.0
        self.work_needed = 0.0
        self._target_px = None
        self.actions = 0                # jobs finished toward the next iced coffee
        self.striking = False           # paused: owed coffee the stockpile can't cover

    # ------------------------------------------------------------------ helpers
    def job_kinds(self):
        return self._jobs

    def job_priority(self):
        if self.kind == "worker":
            return WORKER_PRIORITY
        return list(config.VEHICLES[self.kind]["jobs"])

    def claimable_kinds(self, game):
        """Job types this agent will take right now. Workers hand off hauling and
        cleaning to vehicles once such a vehicle is on the job."""
        if self.kind != "worker":
            return self._jobs
        kinds = set(self._jobs)
        if game.has_active_vehicle_for(HAUL):
            kinds.discard(HAUL)
        if game.has_active_vehicle_for(CLEAN):
            kinds.discard(CLEAN)
        if game.has_active_vehicle_for(BUILD_ROAD):
            kinds.discard(BUILD_ROAD)     # a road paver frees workers from paving
        return kinds

    def _begin_path(self, path):
        self.path = list(path)
        self.state = "MOVING"
        self._advance_target()

    def _advance_target(self):
        if self.path:
            q, r = self.path[0]
            self._target_px = hexgrid.hex_to_pixel(q, r, config.HEX_SIZE)
        else:
            self._target_px = None

    # ------------------------------------------------------------------ update
    def update(self, dt, game):
        if self.state == "IDLE":
            self._try_claim(game)
        elif self.state == "MOVING":
            self._move(dt, game)
        elif self.state == "WORKING":
            self._work(dt, game)

    # ------------------------------------------------------------------ claim
    def _try_claim(self, game):
        job = game.jobs.claim(self, game)
        if not job:
            return
        world = game.world
        target = job.pos

        if job.jtype == BUILD_ROAD:
            # A road costs rubble that must be carried from storage to the site.
            if not game.economy.can_afford(config.ROAD_COST):
                game.jobs.release(job, cooldown=2.0)     # no rubble to supply yet
                return
            path = pathfinding.find_path(world, self.hex, world.hq)
            if path is None:
                path, _ = pathfinding.find_path_adjacent(world, self.hex, world.hq)
                if path is None:
                    game.jobs.release(job, cooldown=1.5)
                    return
            self.job = job
            self.phase = "fetch"                         # go to storage, grab rubble
            self._begin_path(path)
            return

        if job.jtype in (MINE, CONSTRUCT):
            path, stand = pathfinding.find_path_adjacent(world, self.hex, target)
            if stand is None:
                game.jobs.release(job, cooldown=1.5)
                return
        else:
            # CLEAN / HAUL: the tile itself is passable.
            path = pathfinding.find_path(world, self.hex, target)
            if path is None:
                path, stand = pathfinding.find_path_adjacent(world, self.hex, target)
                if stand is None:
                    game.jobs.release(job, cooldown=1.5)
                    return

        self.job = job
        if job.jtype == HAUL:
            self.phase = "collect"
        self._begin_path(path)

    # ------------------------------------------------------------------ move
    def _move(self, dt, game):
        if self._target_px is None:
            self._arrive(game)
            return
        tx, ty = self._target_px
        dx, dy = tx - self.px, ty - self.py
        dist = (dx * dx + dy * dy) ** 0.5
        # roads speed you up, loose rubble slows you down (terrain of tile entered)
        terrain = config.TERRAIN_SPEED.get(game.world.get_tile(*self.path[0]).state, 1.0)
        step = self.speed * terrain * dt
        if dist <= step or dist == 0:
            self.px, self.py = tx, ty
            self.hex = self.path.pop(0)
            if self.path:
                self._advance_target()
            else:
                self._arrive(game)
        else:
            self.px += dx / dist * step
            self.py += dy / dist * step

    def _arrive(self, game):
        # Delivering accumulated cargo (the pile jobs were released during collect,
        # so this must not depend on self.job).
        if self.phase == "deliver":
            self._deliver(game)
            return
        job = self.job
        if job is None:
            self.state = "IDLE"
            return
        world = game.world

        if job.jtype == HAUL:      # phase == "collect"
            tile = world.get_tile(job.q, job.r)
            if self.carrying is None:
                self.carrying = {}
            cap_left = self.carry - sum(self.carrying.values())
            for res, amt in world.take_drop_capped(tile, cap_left).items():
                self.carrying[res] = self.carrying.get(res, 0) + amt
            had_leftover = bool(tile.drops)
            game.jobs.release(self.job, done=True)   # remove this pile's job first
            self.job = None
            if had_leftover:
                game.jobs.add(HAUL, job.q, job.r)    # remainder -> another trip
            # keep collecting from nearby piles until full, then deliver
            if self.carry - sum(self.carrying.values()) > 0:
                nxt = game.jobs.claim_nearest(self, game, HAUL)
                if nxt is not None:
                    p = pathfinding.find_path(world, self.hex, nxt.pos)
                    if p is None:
                        p, _ = pathfinding.find_path_adjacent(world, self.hex, nxt.pos)
                    if p is not None:
                        self.job = nxt
                        self.phase = "collect"
                        self._begin_path(p)
                        return
                    game.jobs.release(nxt, cooldown=1.0)   # unreachable, give back
            if self.carrying:
                self.phase = "deliver"
                dest = game.nearest_dropoff(self.hex)   # HQ or a nearer cable station
                p = pathfinding.find_path(world, self.hex, dest)
                if p is None:
                    p, _ = pathfinding.find_path_adjacent(world, self.hex, dest)
                self._begin_path(p or [])
                return
            self.state = "IDLE"
            self.phase = None
            return

        if job.jtype == BUILD_ROAD and self.phase == "fetch":
            # At storage: take the rubble the road needs, then carry it to the site.
            if not game.economy.spend(config.ROAD_COST):
                game.jobs.release(job, cooldown=2.0)     # rubble ran out — retry later
                self.job = None
                self.phase = None
                self.path = []
                self._target_px = None
                self.state = "IDLE"
                return
            self.carrying = dict(config.ROAD_COST)
            self.phase = "build"
            path = pathfinding.find_path(world, self.hex, job.pos)
            if path is None:
                path, _ = pathfinding.find_path_adjacent(world, self.hex, job.pos)
            self._begin_path(path or [])
            return

        # MINE / CLEAN / BUILD_ROAD (build phase) / CONSTRUCT -> spend work time
        self.work_timer = 0.0
        self.work_needed = self._work_time(game, job)
        self.state = "WORKING"

    # ------------------------------------------------------------------ work
    def _work_time(self, game, job):
        t = game.world.get_tile(job.q, job.r)
        if job.jtype == MINE:
            return t.mine_time / self.mine_mult
        if job.jtype == CLEAN:
            return config.HAND_CLEAN_TIME / self.clean_mult
        if job.jtype == BUILD_ROAD:
            return config.BUILD_ROAD_TIME
        if job.jtype == CONSTRUCT:
            return config.CONSTRUCT_TIME
        return 1.0

    def _work(self, dt, game):
        self.work_timer += dt
        job = self.job
        if job and job.jtype == CONSTRUCT and job.data.get("building"):
            job.data["building"].progress = min(1.0, self.work_timer / self.work_needed)
        if self.work_timer < self.work_needed:
            return
        world = game.world
        t = world.get_tile(job.q, job.r)
        if job.jtype == MINE:
            world.mine(t)                             # rock -> rubble
            game.hint_rubble()                        # first-rubble "use Clean tool" nudge
            if t.drops:
                game.jobs.add(HAUL, t.q, t.r)         # transporters auto-haul the ore
            game.jobs.add(CLEAN, t.q, t.r)            # bulldozers auto-clean
        elif job.jtype == CLEAN:
            world.clean(t)                            # -> excavated + a rubble pile
            if t.drops:
                game.jobs.add(HAUL, t.q, t.r)         # the rubble pile must be hauled
        elif job.jtype == BUILD_ROAD:
            world.build_road(t)                          # consumes the carried rubble
            self.carrying = None
        elif job.jtype == CONSTRUCT:
            if t.building:
                t.building.built = True
                t.building.progress = 1.0
                game.log(f"{config.BUILDINGS[t.building.btype]['name']} built")
        game.register_action(self)
        self._finish(game, done=True)

    def _deliver(self, game):
        """Drop accumulated cargo into the stockpile (one haul action per trip)."""
        if self.carrying:
            for res, amt in self.carrying.items():
                game.economy.add(res, amt)
            game.log(", ".join(f"+{a} {config.RESOURCE_LABEL.get(res, res)}"
                               for res, a in self.carrying.items()))
            self.carrying = None
            game.register_action(self)
        self.job = None
        self.phase = None
        self.path = []
        self._target_px = None
        self.state = "IDLE"

    def _finish(self, game, done):
        game.jobs.release(self.job, done=done)
        self.job = None
        self.phase = None
        self.path = []
        self._target_px = None
        self.state = "IDLE"
