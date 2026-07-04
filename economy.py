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
        self.jammies = config.JAMMIES_START     # money
        self.coffee = config.COFFEE_START       # iced coffee (worker salary)

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
    def update(self, dt, buildings):
        # Mark obsolete buildings (poor-yield ones superseded by a better type).
        enabled_types = {b.btype for b in buildings if b.built and b.enabled}
        for b in buildings:
            b.obsolete = any(t in enabled_types
                             for t in config.OBSOLETED_BY.get(b.btype, []))

        for b in buildings:
            if not b.active or not b.recipes:
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

    def _pick_recipe(self, b):
        """First recipe (in config order) whose inputs are all in stock."""
        for i, recipe in enumerate(b.recipes):
            if self.can_afford(recipe["inp"]):
                return i
        return None

    def _consume(self, inp):
        for res, n in inp.items():
            self.inv[res] -= n
