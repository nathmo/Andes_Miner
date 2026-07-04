"""
buildings.py — placed structures (workshop, oven, crusher, arc furnace).

A Building sits on one tile. It starts unbuilt (a CONSTRUCT job raises it), then
becomes active. Processing buildings convert stockpile inputs to outputs over
time; that logic lives in economy.py so all inventory access is in one place.
"""

import config


class Building:
    __slots__ = ("btype", "q", "r", "built", "progress", "timer", "current",
                 "enabled", "obsolete", "powered")

    def __init__(self, btype, q, r, built=False):
        self.btype = btype
        self.q = q
        self.r = r
        self.built = built
        self.progress = 1.0 if built else 0.0
        self.timer = 0.0            # elapsed time on the current recipe
        self.current = None         # index of recipe being processed, or None
        self.enabled = True         # player toggle (building panel)
        self.obsolete = False       # auto-set when a better building exists
        self.powered = True         # had enough power to run this tick (energy sim)

    @property
    def active(self):
        """Whether this building actually processes right now."""
        return self.built and self.enabled and not self.obsolete

    @property
    def info(self):
        return config.BUILDINGS[self.btype]

    @property
    def name(self):
        return self.info["name"]

    @property
    def recipes(self):
        return self.info["process"]

    @property
    def power_gen(self):
        return self.info.get("power_gen", False)

    @property
    def is_battery(self):
        return self.info.get("storage", False)

    @property
    def power_draw(self):
        """Instantaneous power while running the current recipe."""
        return self.power_for(self.current)

    def power_for(self, idx):
        """Power drawn if running recipe `idx`: energy-per-op / recipe time, so the
        total energy per operation equals MACHINE_KWH_PER_OP regardless of duration."""
        if idx is None or not self.recipes:
            return 0.0
        t = self.recipes[idx]["time"]
        kwh = config.MACHINE_KWH_PER_OP.get(self.btype, 0)
        return kwh / t if t > 0 else 0.0
