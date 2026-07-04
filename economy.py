"""
economy.py — the global stockpile, the stock market, and building processing.

One shared inventory (like early-game Factorio). Buildings pull inputs from it
and push outputs back on a timer. Inputs are consumed when a recipe starts and
outputs delivered when it finishes, so nothing is double-spent. Prices drift on a
small stock market (random walk + your production trend, floored) — see item 23.
"""

import random

import config

# Everything with a sell price is tradeable and gets a drifting market price.
TRADEABLE = list(config.SELL_PRICES.keys())


class Economy:
    def __init__(self):
        self.inv = {res: 0 for res in config.RESOURCES}
        for k, v in config.START_INVENTORY.items():
            self.inv[k] = self.inv.get(k, 0) + v
        self.jammies = float(config.JAMMIES_START)   # money (float: energy micro-costs)
        self.coffee = config.COFFEE_START            # iced coffee (worker salary)
        # energy telemetry (updated each tick in update())
        self.energy_bought = 0.0        # cumulative grid power drawn
        self.power_demand = 0.0         # power used this tick
        self.solar_supply = 0.0         # solar power available this tick
        self.grid_draw = 0.0            # power actually bought from the grid this tick
        self.battery_charge = 0.0       # energy stored in Grid Batteries
        self.battery_capacity = 0.0     # total storage from built batteries
        self.export_power = 0.0         # clean power reinjected to the grid this tick
        self.brownout = False           # a machine couldn't be powered (e.g. no cash)

        # carbon: grid intensity + cumulative emissions from bought grid power
        self.grid_carbon = config.GRID_CARBON_START
        self.emissions_total = 0.0
        self.emissions_rate = 0.0
        self.emissions_hist = [0.0]

        # power trends (kW), sampled each market tick for the trend graphs
        self.demand_hist = [0.0]         # electricity consumed (all running machines)
        self.solar_hist = [0.0]          # electricity produced by Solar Arrays

        # stock market: per-resource price multiplier + recent price history
        self.price_mult = {res: 1.0 for res in TRADEABLE}
        self.price_hist = {res: [config.SELL_PRICES[res]] for res in TRADEABLE}
        # electricity price drifts too, and is charted in the market trend panel
        self.elec_mult = 1.0
        self.elec_hist = [config.KWH_PRICE]
        self._market_t = 0.0

    # ------------------------------------------------------------------ stockpile
    def amount(self, res):
        return self.inv.get(res, 0)

    def add(self, res, n):
        self.inv[res] = self.inv.get(res, 0) + n

    # ------------------------------------------------------------------ market
    def sell_price(self, res):
        """Current per-unit sell price (base * market multiplier, floored at 1)."""
        return max(1, round(config.SELL_PRICES.get(res, 0) * self.price_mult.get(res, 1.0)))

    def buy_price(self, res):
        """Current per-unit buy price (base * market multiplier, floored at 1)."""
        return max(1, round(config.BUY_PRICES.get(res, 0) * self.price_mult.get(res, 1.0)))

    def elec_price(self):
        """Current grid electricity price (jammies per kWh), drifting on the market."""
        return config.KWH_PRICE * self.elec_mult

    def sell(self, res, batch=None):
        """Sell up to `batch` units of a resource for jammies. Returns jammies earned."""
        batch = config.SELL_BATCH if batch is None else batch
        amt = min(batch, self.inv.get(res, 0))
        if amt <= 0:
            return 0
        self.inv[res] -= amt
        gain = amt * self.sell_price(res)
        self.jammies += gain
        # flooding the market with a resource depresses its price
        if res in self.price_mult:
            self.price_mult[res] = max(config.PRICE_MIN_MULT,
                                       self.price_mult[res] - amt * config.SELL_PRICE_IMPACT)
        return gain

    def tick_market(self, dt):
        """Random-walk each price toward/away from its base and log the trend."""
        self._market_t += dt
        if self._market_t < config.MARKET_TICK:
            return
        self._market_t = 0.0
        for res in TRADEABLE:
            m = self.price_mult[res]
            m += random.uniform(-1.0, 1.0) * config.PRICE_DRIFT
            m += (1.0 - m) * config.PRICE_REVERT          # mean-revert to base
            self.price_mult[res] = max(config.PRICE_MIN_MULT, min(config.PRICE_MAX_MULT, m))
            hist = self.price_hist[res]
            hist.append(self.sell_price(res))
            if len(hist) > config.PRICE_HISTORY:
                hist.pop(0)
        # electricity price drifts on the same random-walk + mean-revert model
        m = self.elec_mult
        m += random.uniform(-1.0, 1.0) * config.PRICE_DRIFT
        m += (1.0 - m) * config.PRICE_REVERT
        self.elec_mult = max(config.PRICE_MIN_MULT, min(config.PRICE_MAX_MULT, m))
        self.elec_hist.append(self.elec_price())
        if len(self.elec_hist) > config.PRICE_HISTORY:
            self.elec_hist.pop(0)
        self.emissions_hist.append(self.emissions_total)
        if len(self.emissions_hist) > config.EMISS_HISTORY:
            self.emissions_hist.pop(0)
        # power production/consumption trends (values set by _allocate_power)
        self.demand_hist.append(self.power_demand)
        if len(self.demand_hist) > config.POWER_HISTORY:
            self.demand_hist.pop(0)
        self.solar_hist.append(self.solar_supply)
        if len(self.solar_hist) > config.POWER_HISTORY:
            self.solar_hist.pop(0)

    def buy(self, res, batch=None):
        """Buy `batch` units of a material with jammies. Returns units bought."""
        batch = config.BUY_BATCH if batch is None else batch
        if res not in config.BUY_PRICES:
            return 0
        cost = batch * self.buy_price(res)
        if self.jammies < cost:
            return 0
        self.jammies -= cost
        self.add(res, batch)
        # buying pressure lifts the price
        if res in self.price_mult:
            self.price_mult[res] = min(config.PRICE_MAX_MULT,
                                       self.price_mult[res] + batch * config.BUY_PRICE_IMPACT)
        return batch

    def buy_coffee(self, batch=None):
        """Buy iced coffee with jammies. Returns coffees bought (0 if too poor)."""
        batch = config.COFFEE_BATCH if batch is None else batch
        cost = batch * config.COFFEE_PRICE
        if self.jammies < cost:
            return 0
        self.jammies -= cost
        self.coffee += batch
        return batch

    def can_afford(self, cost):
        return all(self.inv.get(k, 0) >= v for k, v in cost.items())

    def spend(self, cost):
        if not self.can_afford(cost):
            return False
        for k, v in cost.items():
            self.inv[k] -= v
        return True

    # ------------------------------------------------------------------ processing
    def update(self, dt, buildings, sun=1.0):
        # Mark obsolete buildings (poor-yield ones superseded by a better type).
        enabled_types = {b.btype for b in buildings if b.built and b.enabled}
        for b in buildings:
            b.obsolete = any(t in enabled_types
                             for t in config.OBSOLETED_BY.get(b.btype, []))

        self.tick_market(dt)
        self._allocate_power(dt, buildings, sun)

        # Only powered buildings advance their recipe (no power -> paused).
        for b in buildings:
            if not b.active or not b.recipes or not b.powered:
                continue
            if b.current is None:
                b.current = self._pick_recipe(b)
                b.timer = 0.0
                if b.current is not None:
                    self._consume(b.recipes[b.current]["inp"])
            if b.current is None:
                continue
            b.timer += dt
            recipe = b.recipes[b.current]
            if b.timer >= recipe["time"]:
                for res, n in recipe["out"].items():
                    self.add(res, n)
                b.current = None
                b.timer = 0.0

    def _allocate_power(self, dt, buildings, sun):
        """Power a machine from solar first, then a Grid Battery, then bought grid.
        Surplus solar charges the battery. Machines that no source can cover this
        tick brown out (b.powered=False)."""
        solar = sun * sum(config.SOLAR_ARRAY_OUTPUT for b in buildings
                          if b.built and b.enabled and b.power_gen)
        self.battery_capacity = sum(config.BATTERY_CAPACITY for b in buildings
                                    if b.built and b.enabled and b.is_battery)
        self.battery_charge = min(self.battery_charge, self.battery_capacity)

        price = self.elec_price()
        battery_avail = (self.battery_charge / dt) if dt > 0 else 0.0
        buyable = (self.jammies / (dt * price)
                   if dt > 0 and price > 0 else 0.0)
        budget = solar + battery_avail + max(0.0, buyable)

        used = 0.0
        for b in buildings:
            if not b.active or not b.recipes:
                b.powered = False
                continue
            idx = b.current if b.current is not None else self._pick_recipe(b)
            if idx is None:
                b.powered = False
                continue
            p = b.power_for(idx)
            if used + p <= budget + 1e-9:
                used += p
                b.powered = True
            else:
                b.powered = False          # brownout

        self.brownout = any(
            (not b.powered) and b.active and b.recipes
            and (b.current is not None or self._pick_recipe(b) is not None)
            for b in buildings)

        # source the used power: solar -> battery -> grid
        from_solar = min(used, solar)
        from_battery = min(used - from_solar, battery_avail)
        from_grid = used - from_solar - from_battery
        self.battery_charge -= from_battery * dt

        # surplus solar charges the battery; overflow is exported (greens the grid)
        surplus = max(0.0, solar - used) * dt
        room = self.battery_capacity - self.battery_charge
        stored = min(room, surplus * config.BATTERY_CHARGE_EFF)
        self.battery_charge += stored
        exported = max(0.0, surplus - stored / config.BATTERY_CHARGE_EFF)
        self.export_power = exported / dt if dt > 0 else 0.0

        self.jammies -= from_grid * dt * price
        self.energy_bought += from_grid * dt
        self.emissions_rate = from_grid * self.grid_carbon * config.CO2_SCALE   # kg/s
        self.emissions_total += self.emissions_rate * dt
        if self.export_power > 0:
            self.grid_carbon = max(config.CARBON_MIN,
                                   self.grid_carbon - self.export_power * dt * config.CARBON_EXPORT_DECAY)
        else:
            self.grid_carbon = min(config.GRID_CARBON_START,
                                   self.grid_carbon + dt * config.CARBON_REVERT)
        self.power_demand = used
        self.solar_supply = solar
        self.grid_draw = from_grid

    def _inputs_available(self, inp):
        """True if every input is in stock AND consuming it keeps each resource at
        or above its configured reserve floor (config.INPUT_RESERVE). This is what
        stops the Silica Kiln from draining rubble the roads/buildings still need."""
        for res, n in inp.items():
            reserve = config.INPUT_RESERVE.get(res, 0)
            if self.inv.get(res, 0) - n < reserve:
                return False
        return True

    def _pick_recipe(self, b):
        """First recipe (in config order) that's runnable — inputs in stock and
        above their reserve floor."""
        for i, recipe in enumerate(b.recipes):
            if self._inputs_available(recipe["inp"]):
                return i
        return None

    def reserve_block(self, b):
        """For UI status: if a built, enabled, non-obsolete processing building is
        idle *specifically* because a reserved input (e.g. rubble) is at its floor,
        return (res, reserve); else None. None also when it's actively running or
        idle for some other reason (out of ore, no power)."""
        if not b.recipes or b.current is not None:
            return None
        if self._pick_recipe(b) is not None:     # a recipe could run -> not reserve-blocked
            return None
        for recipe in b.recipes:
            for res, n in recipe["inp"].items():
                reserve = config.INPUT_RESERVE.get(res, 0)
                if reserve and self.inv.get(res, 0) - n < reserve:
                    return (res, reserve)
        return None

    def _consume(self, inp):
        for res, n in inp.items():
            self.inv[res] -= n
