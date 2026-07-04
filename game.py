"""
game.py — the central Game object that wires every system together.

Owns the world, camera, economy, job queue, buildings, and agents, and exposes
the high-level actions the UI/input layers call (mark, place road/building,
manufacture vehicle, recruit worker). Labour model: the player has a worker
count; each vehicle needs one worker to crew it, and any spare workers do jobs
on foot. So building vehicles trades hand-labour for faster specialised units.
"""

import config
import hexgrid
from world import World
from economy import Economy
from jobs import JobManager, MINE, CLEAN, BUILD_ROAD, CONSTRUCT
from entities import Agent
from buildings import Building
from tiles import ROCK, RUBBLE, EXCAVATED, ROAD


class Game:
    def __init__(self, seed=config.WORLD_SEED, camera=None):
        self.world = World(seed)
        self.economy = Economy()
        self.jobs = JobManager(self.world)
        self.buildings = []
        self.camera = camera

        self.num_workers = config.START_WORKERS
        self.vehicles = []            # Agent objects (vehicles)
        self.foot_workers = []        # Agent objects (on-foot workers)
        self.active_vehicle_count = 0
        self._reconcile_agents()

        # interaction state (driven by input.py)
        self.tool = "mine"            # mine | road | build | select
        self.build_choice = "workshop"
        self.hover_hex = None
        self.selection_rect = None

        # time / speed
        self.speed_index = 0
        self.paused = False

        # upkeep (salary paid in iced coffee, per completed job — register_action)
        self.wages_due = False        # True while any worker is paused unpaid
        self.selected_building = None

        # transient on-screen messages
        self.messages = []
        self._autosave_t = 0.0

        # save/load requests raised by input, handled by main
        self.want_save = False
        self.want_load = False

    # ------------------------------------------------------------------ agents
    def _reconcile_agents(self):
        active_v = min(len(self.vehicles), self.num_workers)
        self.active_vehicle_count = active_v
        foot_needed = self.num_workers - active_v
        hq = self.world.hq
        while len(self.foot_workers) < foot_needed:
            self.foot_workers.append(Agent("worker", *hq))
        while len(self.foot_workers) > foot_needed:
            # drop an idle worker if possible, else the last one
            idle = next((w for w in self.foot_workers if w.state == "IDLE"), None)
            self.foot_workers.remove(idle or self.foot_workers[-1])

    def iter_active_agents(self):
        for w in self.foot_workers:
            yield w
        for v in self.vehicles[:self.active_vehicle_count]:
            yield v

    def iter_agents(self):
        """All agents to draw (includes parked, uncrewed vehicles)."""
        for w in self.foot_workers:
            yield w
        for v in self.vehicles:
            yield v

    def has_active_vehicle_for(self, jtype):
        """Is a crewed vehicle available that performs this job type?"""
        for v in self.vehicles[:self.active_vehicle_count]:
            if jtype in config.VEHICLES[v.kind]["jobs"]:
                return True
        return False

    # ------------------------------------------------------------------ update
    def update(self, sim_dt, real_dt):
        if not self.paused and sim_dt > 0:
            self.jobs.update(sim_dt)
            was_striking = self.wages_due
            for a in self.iter_active_agents():
                if a.striking:                  # owed coffee — try to back-pay
                    if self.economy.coffee >= 1:
                        self.economy.coffee -= 1
                        a.striking = False
                    else:
                        continue                # this worker waits, unpaid
                a.update(sim_dt, self)
            self.wages_due = any(a.striking for a in self.iter_active_agents())
            if self.wages_due and not was_striking:
                self.log("Out of iced coffee — a worker paused. Buy more to keep going.")
            elif was_striking and not self.wages_due:
                self.log("Wages paid — crew back to work")
            self.economy.update(sim_dt, self.buildings)
        self._update_messages(real_dt)
        self._autosave_t += real_dt

    # ------------------------------------------------------------------ salary
    def register_action(self, agent):
        """A worker just finished a job. Every WAGE_ACTIONS_PER_COFFEE jobs it
        drinks one iced coffee as its wage; if the stockpile is empty it pauses
        (strikes) until coffee is available again."""
        agent.actions += 1
        if agent.actions >= config.WAGE_ACTIONS_PER_COFFEE:
            agent.actions -= config.WAGE_ACTIONS_PER_COFFEE
            if self.economy.coffee >= 1:
                self.economy.coffee -= 1
            else:
                agent.striking = True

    def sim_multiplier(self):
        return 0.0 if self.paused else config.SPEED_STEPS[self.speed_index]

    # ------------------------------------------------------------------ actions
    def designate(self, q, r):
        """Context-sensitive work order on a tile (the 'mine' tool)."""
        t = self.world.get_tile(q, r)
        if t.state == ROCK:
            if self.world.mineable(t) and not t.marked:
                t.marked = True
                self.jobs.add(MINE, q, r)
        elif t.state == RUBBLE:
            if not self.jobs.has_job(q, r, CLEAN):
                self.jobs.add(CLEAN, q, r)

    def undesignate(self, q, r):
        t = self.world.get_tile(q, r)
        t.marked = False
        self.jobs.cancel_at(q, r)

    def can_place_here(self, q, r):
        t = self.world.get_tile(q, r)
        if self.tool == "road":
            return (t.state == EXCAVATED and not self.jobs.has_job(q, r, BUILD_ROAD)
                    and self.economy.can_afford(config.ROAD_COST))
        if self.tool == "build":
            if t.building is not None:
                return False
            if t.state not in (EXCAVATED, ROAD):
                return False
            return self.economy.can_afford(config.BUILDINGS[self.build_choice]["cost"])
        return False

    def place(self, q, r):
        if not self.can_place_here(q, r):
            return
        if self.tool == "road":
            if self.economy.spend(config.ROAD_COST):
                self.jobs.add(BUILD_ROAD, q, r)
        elif self.tool == "build":
            cost = config.BUILDINGS[self.build_choice]["cost"]
            if self.economy.spend(cost):
                b = Building(self.build_choice, q, r, built=False)
                self.world.get_tile(q, r).building = b
                self.buildings.append(b)
                self.jobs.add(CONSTRUCT, q, r, data={"building": b})
                self.log(f"{b.name} queued")

    # ------------------------------------------------------------------ economy actions
    def has_workshop(self):
        return any(b.built and b.btype == "workshop" for b in self.buildings)

    def manufacture(self, vtype):
        if not self.has_workshop():
            self.log("Need a built Vehicle Workshop")
            return False
        cost = config.VEHICLES[vtype]["cost"]
        if not self.economy.can_afford(cost):
            self.log("Not enough metal")
            return False
        self.economy.spend(cost)
        self.vehicles.append(Agent(vtype, *self.world.hq))
        self._reconcile_agents()
        self.log(f"{config.VEHICLES[vtype]['name']} built")
        return True

    def recruit_worker(self):
        if not self.economy.can_afford(config.RECRUIT_COST):
            self.log("Not enough metal to recruit")
            return False
        self.economy.spend(config.RECRUIT_COST)
        self.num_workers += 1
        self._reconcile_agents()
        self.log("Recruited a worker")
        return True

    # ------------------------------------------------------------------ market / upkeep
    def sell(self, res):
        gain = self.economy.sell(res)
        if gain:
            self.log(f"Sold {config.RESOURCE_LABEL.get(res, res)} for {gain} jammies")

    def buy_coffee(self):
        n = self.economy.buy_coffee()
        if n:
            self.log(f"Bought {n} iced coffee")
        else:
            self.log("Not enough jammies for coffee")

    # ------------------------------------------------------------------ building selection
    def select_building_at(self, q, r):
        t = self.world.get_tile(q, r)
        self.selected_building = t.building if t.building else None
        return self.selected_building is not None

    def toggle_selected_building(self):
        b = self.selected_building
        if b is None:
            return
        b.enabled = not b.enabled
        self.log(f"{b.name} {'enabled' if b.enabled else 'disabled'}")

    # ------------------------------------------------------------------ camera
    def center_camera_home(self):
        """Recenter the view on the HQ so you can't get lost while panning."""
        if self.camera is not None:
            hx, hy = hexgrid.hex_to_pixel(*self.world.hq, config.HEX_SIZE)
            self.camera.x, self.camera.y = hx, hy

    # ------------------------------------------------------------------ messages
    def log(self, text):
        self.messages.append({"text": text, "life": 4.0})
        if len(self.messages) > 6:
            self.messages.pop(0)

    def _update_messages(self, dt):
        for m in self.messages:
            m["life"] -= dt
        self.messages = [m for m in self.messages if m["life"] > 0]
