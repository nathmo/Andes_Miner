"""
economy.py — the global stockpile and building processing.

One shared inventory (like early-game Factorio). Buildings pull inputs from it
and push outputs back on a timer. Inputs are consumed when a recipe starts and
outputs delivered when it finishes, so nothing is double-spent.
"""

import config


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

    # ------------------------------------------------------------------ stockpile
    def amount(self, res):
        return self.inv.get(res, 0)

    def add(self, res, n):
        self.inv[res] = self.inv.get(res, 0) + n

    # ------------------------------------------------------------------ market
    def sell(self, res, batch=None):
        """Sell up to `batch` units of a resource for jammies. Returns jammies earned."""
        batch = config.SELL_BATCH if batch is None else batch
        amt = min(batch, self.inv.get(res, 0))
        if amt <= 0:
            return 0
        self.inv[res] -= amt
        gain = amt * config.SELL_PRICES.get(res, 0)
        self.jammies += gain
        return gain

    def buy(self, res, batch=None):
        """Buy `batch` units of a material with jammies. Returns units bought."""
        batch = config.BUY_BATCH if batch is None else batch
        price = config.BUY_PRICES.get(res)
        if price is None:
            return 0
        cost = batch * self.buy_price(res)
        if self.jammies < cost:
            return 0
        self.jammies -= cost
        self.add(res, batch)
        return batch

    def buy_price(self, res):
        """Per-unit buy price (item 23 will make this drift)."""
        return config.BUY_PRICES.get(res, 0)

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
        """Solar first, then buy the grid shortfall with jammies. Buildings that
        can't be powered this tick brown out (b.powered=False)."""
        solar = sun * sum(config.SOLAR_ARRAY_OUTPUT for b in buildings
                          if b.built and b.enabled and b.power_gen)
        buyable = (self.jammies / (dt * config.KWH_PRICE)
                   if dt > 0 and config.KWH_PRICE > 0 else 0.0)
        budget = solar + max(0.0, buyable)
        used = 0.0
        for b in buildings:
            if not b.active or not b.recipes:
                b.powered = False
                continue
            will_run = b.current is not None or self._pick_recipe(b) is not None
            if not will_run:
                b.powered = False
                continue
            p = b.power_draw
            if used + p <= budget + 1e-9:
                used += p
                b.powered = True
            else:
                b.powered = False          # brownout
        grid = max(0.0, used - solar)
        self.jammies -= grid * dt * config.KWH_PRICE
        self.energy_bought += grid * dt
        self.power_demand = used
        self.solar_supply = solar

    def _pick_recipe(self, b):
        """First recipe (in config order) whose inputs are all in stock."""
        for i, recipe in enumerate(b.recipes):
            if self.can_afford(recipe["inp"]):
                return i
        return None

    def _consume(self, inp):
        for res, n in inp.items():
            self.inv[res] -= n
