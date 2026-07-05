"""
game.py — the central Game object that wires every system together.

Owns the world, camera, economy, job queue, buildings, and agents, and exposes
the high-level actions the UI/input layers call (mark, place road/building,
manufacture vehicle, recruit worker). Labour model: the player has a worker
count; each vehicle needs one worker to crew it, and any spare workers do jobs
on foot. So building vehicles trades hand-labour for faster specialised units.
"""

import heapq
import math
import datetime

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
        self._ensure_depot()          # central storage on the HQ tile

        self.num_workers = config.START_WORKERS
        self.vehicles = []            # Agent objects (vehicles)
        self.foot_workers = []        # Agent objects (on-foot workers)
        self.active_vehicle_count = 0
        self._reconcile_agents()

        # interaction state (driven by input.py)
        self.tool = "excavate"        # excavate | clean | road | build | select
        self.build_choice = "workshop"
        self.hover_hex = None
        self.selection_rect = None
        self.show_market = False      # stock-market panel toggle
        self.show_settings = False    # settings menu toggle

        # display preferences (settings menu)
        self.show_clouds = True       # drifting clouds in the sky
        self.show_birds = False       # circling condors (off by default)
        self.ui_scale = 1.0           # HUD scale factor (settings menu)

        # time / speed
        self.speed_index = 0
        self.paused = False

        # environment: day/night. time_of_day in [0,1); sun 0 at night, 1 at noon.
        # The calendar starts at today's real date; game_day counts days elapsed.
        self.time_of_day = config.DAY_START_HOUR / 24.0   # start at 08:00
        self.sun = 1.0
        self.start_date = datetime.date.today().isoformat()
        self.game_day = 0

        # upkeep (salary paid in iced coffee, per completed job — register_action)
        self.wages_due = False        # True while any worker is paused unpaid
        self.rubble_short = False      # True while road jobs are stalled with no rubble
        self.power_blackout = False    # True while machines are stopped for lack of cash
        self.selected_building = None

        # overarching goal: link villages to the road network
        self.villages_connected = 0
        self._last_road_count = -1

        # warehouse auto-trade settings (item 28)
        self.auto_cash_min = config.AUTO_CASH_MIN
        self.auto_coffee_min = config.AUTO_COFFEE_MIN
        self.auto_smart_sell = False     # upgrade: sell the most valuable stock
        self._auto_t = 0.0

        # transient on-screen messages
        self.messages = []
        self._autosave_t = 0.0

        # save/load requests raised by input, handled by main
        self.want_save = False
        self.want_load = False
        self.want_load_path = None    # load a specific backup slot
        self.want_quit = False        # settings menu -> save & exit
        self.show_load_menu = False
        self._backup_t = 0.0
        self._backup_step = 0

    # ------------------------------------------------------------------ depot
    def _ensure_depot(self):
        """Guarantee a Storage Depot sits on the HQ tile (the haul drop-off), so
        deliveries land in a visible building rather than on bare road. Keeps the
        tile and the buildings list consistent (load resets the list but not the
        tile reference)."""
        t = self.world.get_tile(*self.world.hq)
        if t.building is not None:
            if t.building not in self.buildings:
                self.buildings.append(t.building)
            return
        depot = Building("depot", *self.world.hq, built=True)
        t.building = depot
        self.buildings.append(depot)

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
    def _advance_time(self, sim_dt):
        """Advance the day/night clock and recompute the sun factor (raised cosine
        peaking at noon, zero through the night). Rolls the calendar over midnight."""
        raw = self.time_of_day + sim_dt / config.DAY_LENGTH
        self.game_day += int(raw)                   # whole days crossed (robust to big steps)
        self.time_of_day = raw % 1.0
        self.sun = max(0.0, math.cos((self.time_of_day - 0.5) * 2.0 * math.pi))

    def game_datetime(self):
        """Current in-game date & time as a datetime (calendar starts at today)."""
        try:
            base = datetime.date.fromisoformat(self.start_date)
        except (ValueError, TypeError):
            base = datetime.date.today()
        secs = int(self.time_of_day * 86400)
        return (datetime.datetime(base.year, base.month, base.day)
                + datetime.timedelta(days=self.game_day, seconds=secs))

    def update(self, sim_dt, real_dt):
        if not self.paused and sim_dt > 0:
            self._advance_time(sim_dt)
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
            self.economy.update(sim_dt, self.buildings, self.sun)

            # rubble shortage: road jobs queued but no rubble in stock to supply them
            was_short = self.rubble_short
            self.rubble_short = (self.jobs.count(BUILD_ROAD) > 0
                                 and not self.economy.can_afford(config.ROAD_COST))
            if self.rubble_short and not was_short:
                self.log("Rubble shortage — roads need rubble. Clean rubble or buy some.")
            elif was_short and not self.rubble_short:
                self.log("Rubble restored — road building resuming")

            # electric blackout: machines stopped because there's no cash for grid power
            was_black = self.power_blackout
            self.power_blackout = self.economy.brownout
            if self.power_blackout and not was_black:
                self.log("Electric blackout — no cash for grid power. Sell goods or build solar.")
            elif was_black and not self.power_blackout:
                self.log("Power restored — machines running again")

            self._update_goal()
            self._auto_trade(sim_dt)
        self._update_messages(real_dt)
        self._autosave_t += real_dt
        self._backup_t += real_dt

    # ------------------------------------------------------------------ goal
    def _update_goal(self):
        """Recount linked villages, but only when the road network changed."""
        rc = len(self.world.road_tiles)
        if rc == self._last_road_count:
            return
        self._last_road_count = rc
        connected = sum(1 for (vq, vr) in self.world.villages
                        if self.world.road_within(vq, vr, config.VILLAGE_CONNECT_RANGE))
        if connected > self.villages_connected:
            self.log(f"Village linked by road!  ({connected}/{len(self.world.villages)})")
        self.villages_connected = connected

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
    def max_mine_reach(self):
        """Largest mining reach available: hand workers plus any owned mining
        machine (higher tiers reach farther from a road). Used to decide what the
        player may mark; a job is then claimed only by a unit that can reach it."""
        reach = config.MINE_ROAD_RANGE
        for v in self.vehicles:
            if MINE in config.VEHICLES[v.kind]["jobs"]:
                reach = max(reach, config.VEHICLES[v.kind].get("mine_reach", config.MINE_ROAD_RANGE))
        return reach

    def designate(self, q, r):
        """Work order on a tile, filtered by the active tool: the Excavate tool
        marks solid rock for mining; the Clean tool marks rubble for clearing."""
        t = self.world.get_tile(q, r)
        if t.state == ROCK and self.tool != "clean":
            if self.world.mineable(t, self.max_mine_reach()) and not t.marked:
                t.marked = True
                self.jobs.add(MINE, q, r)
        elif t.state == RUBBLE and self.tool != "excavate":
            if not self.jobs.has_job(q, r, CLEAN):
                self.jobs.add(CLEAN, q, r)

    def undesignate(self, q, r):
        t = self.world.get_tile(q, r)
        t.marked = False
        self.jobs.cancel_at(q, r)

    # ------------------------------------------------------------------ auto-planner
    def has_planner(self):
        return any(b.built and b.btype == "planner" for b in self.buildings)

    def box_designate(self, cells):
        """Designate a batch of tiles (single click or drag-box). With a built
        Mining Planner, rock out of road range is reached automatically: a
        dig+road corridor is planned from the road network to each such tile.
        Without one, only in-range rock is marked (rubble queued for cleaning)."""
        planner = self.has_planner()
        reach = self.max_mine_reach()
        far = []
        for (q, r) in cells:
            if self.world.is_sky(q, r):          # open sky above the summit: nothing to do
                continue
            t = self.world.get_tile(q, r)
            if t.state == ROCK and self.tool != "clean":
                if self.world.mineable(t, reach):
                    self.designate(q, r)
                elif planner:
                    far.append((q, r))
            elif t.state == RUBBLE and self.tool != "excavate":
                self.designate(q, r)
        if not planner or not far:
            return
        far.sort(key=lambda c: hexgrid.axial_distance(c, self.world.hq))
        cap = config.PLAN_MAX_ROUTES
        planned = sum(1 for tgt in far[:cap] if self._plan_route(tgt))
        if planned:
            msg = f"Planner: routing to {planned} ore tile(s)"
            if len(far) > cap:
                msg += f" (+{len(far) - cap} not planned this pass)"
            self.log(msg)

    def _plan_route(self, target):
        """Dijkstra from `target` back to the nearest road — cheap across passable
        tiles, costly through rock — then queue the dig+road corridor and mark the
        target for mining. Job validity gates the order, so the road creeps out and
        each newly-reachable rock is mined in turn. Returns True if a route queued."""
        road = self.world.road_tiles
        dist = {target: 0.0}
        came = {target: None}
        heap = [(0.0, target)]
        goal = None
        expanded = 0
        while heap:
            d, cur = heapq.heappop(heap)
            if d > dist.get(cur, 1e18):
                continue
            if cur in road and cur != target:
                goal = cur
                break
            expanded += 1
            if expanded > config.PLAN_MAX_EXPAND:
                break
            for n in hexgrid.walkable_neighbors(*cur):
                t = self.world.get_tile(*n)
                step = 0.2 if t.passable() else 1.0
                nd = d + step
                if nd < dist.get(n, 1e18):
                    dist[n] = nd
                    came[n] = cur
                    heapq.heappush(heap, (nd, n))
        if goal is None:
            return False
        node, route = goal, []
        while node is not None:
            route.append(node)
            node = came[node]
        # route = [road tile, ..., target]; road the in-between, mine the target
        for (q, r) in route[1:-1]:
            self._queue_path_tile(q, r)
        tt = self.world.get_tile(*target)
        if tt.state == ROCK and not tt.marked:
            tt.marked = True
            self.jobs.add(MINE, *target)
        return True

    def _queue_path_tile(self, q, r):
        """Queue whatever turns tile (q, r) into road: mine/clean as needed, then
        the road itself (each job waits on the tile's state via job validity)."""
        t = self.world.get_tile(q, r)
        if t.state == ROAD:
            return
        if t.state == ROCK:
            t.marked = True
            self.jobs.add(MINE, q, r)      # -> rubble, auto-clean -> excavated
        elif t.state == RUBBLE:
            self.jobs.add(CLEAN, q, r)
        self.jobs.add(BUILD_ROAD, q, r)    # valid once the tile is excavated

    def can_place_here(self, q, r):
        t = self.world.get_tile(q, r)
        if self.tool == "road":
            # Roads can be planned freely; a builder fetches the rubble to the site.
            return t.state == EXCAVATED and not self.jobs.has_job(q, r, BUILD_ROAD)
        if self.tool == "build":
            if t.building is not None:
                return False
            info = config.BUILDINGS[self.build_choice]
            if info.get("on") == "road":
                if t.state != ROAD:            # cable stations sit on the road
                    return False
            elif t.state not in (EXCAVATED, ROAD):
                return False
            return self.economy.can_afford(info["cost"])
        return False

    def nearest_dropoff(self, hexpos):
        """Where a hauler unloads: HQ, or a nearer built Cable Car Station (which
        cables the load straight to HQ). Shorter trips = more throughput far out."""
        best = self.world.hq
        bd = hexgrid.axial_distance(hexpos, self.world.hq)
        for b in self.buildings:
            if b.built and b.btype == "cable_station":
                d = hexgrid.axial_distance(hexpos, (b.q, b.r))
                if d < bd:
                    bd, best = d, (b.q, b.r)
        return best

    def place(self, q, r):
        if not self.can_place_here(q, r):
            return
        if self.tool == "road":
            self.jobs.add(BUILD_ROAD, q, r)   # rubble is fetched to the site by the builder
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

    def has_warehouse(self):
        return any(b.built and b.btype == "warehouse" for b in self.buildings)

    # ------------------------------------------------------------------ auto-trade
    def _auto_trade(self, dt):
        """With a Warehouse, keep coffee and cash above their thresholds: buy coffee
        when low, and sell stock (fixed order, or the most valuable with the upgrade)
        when cash is low, never dipping resources below their keep-reserve."""
        if not self.has_warehouse():
            return
        self._auto_t += dt
        if self._auto_t < config.AUTO_TRADE_INTERVAL:
            return
        self._auto_t = 0.0
        econ = self.economy
        if econ.coffee < self.auto_coffee_min and econ.jammies >= config.COFFEE_PRICE:
            econ.buy_coffee(config.COFFEE_BATCH)
        if econ.jammies < self.auto_cash_min:
            res = self._auto_sell_pick()
            if res:
                econ.sell(res, config.SELL_BATCH)

    def _auto_sell_pick(self):
        econ = self.economy
        if self.auto_smart_sell:                 # sell whatever is worth the most now
            best, best_val = None, 0
            for res in config.SELL_PRICES:
                amt = econ.amount(res) - config.AUTO_SELL_KEEP.get(res, 0)
                if amt <= 0:
                    continue
                val = amt * econ.sell_price(res)
                if val > best_val:
                    best, best_val = res, val
            return best
        for res in config.AUTO_SELL_FIXED:       # default: dump low-value surplus first
            if econ.amount(res) - config.AUTO_SELL_KEEP.get(res, 0) > 0:
                return res
        return None

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

    def buy_material(self, res):
        n = self.economy.buy(res, config.BUY_BATCH)
        if n:
            self.log(f"Bought {n} {config.RESOURCE_LABEL.get(res, res)}")
        else:
            self.log("Not enough jammies")

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
