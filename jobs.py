"""
jobs.py — the work queue and assignment.

A Job designates work on one tile: MINE a rock, CLEAN rubble, BUILD_ROAD on an
excavated tile, HAUL an ore drop to HQ, or CONSTRUCT a building. Idle agents
claim the nearest job they are competent to perform. Jobs are reserved so two
agents never grab the same one, and briefly cooled-down if an agent can't reach
them (e.g. no path yet).
"""

import config
import hexgrid

MINE = "MINE"
CLEAN = "CLEAN"
BUILD_ROAD = "BUILD_ROAD"
HAUL = "HAUL"
CONSTRUCT = "CONSTRUCT"

# Which agent kinds may perform which jobs.
WORKER_JOBS = {MINE, CLEAN, BUILD_ROAD, HAUL, CONSTRUCT}


class Job:
    __slots__ = ("jtype", "q", "r", "agent", "cooldown", "data")

    def __init__(self, jtype, q, r, data=None):
        self.jtype = jtype
        self.q = q
        self.r = r
        self.agent = None
        self.cooldown = 0.0
        self.data = data or {}

    @property
    def pos(self):
        return (self.q, self.r)


class JobManager:
    def __init__(self, world):
        self.world = world
        self.jobs = []
        self._by_tile = {}      # (q,r,jtype) -> Job to dedupe designations

    # ------------------------------------------------------------------ edit
    def add(self, jtype, q, r, data=None):
        key = (q, r, jtype)
        if key in self._by_tile:
            return self._by_tile[key]
        job = Job(jtype, q, r, data)
        self.jobs.append(job)
        self._by_tile[key] = job
        return job

    def remove(self, job):
        try:
            self.jobs.remove(job)
        except ValueError:
            pass
        self._by_tile.pop((job.q, job.r, job.jtype), None)

    def cancel_at(self, q, r):
        """Remove any pending (unclaimed) job designations on a tile."""
        for job in list(self.jobs):
            if job.q == q and job.r == r and job.agent is None:
                self.remove(job)

    def has_job(self, q, r, jtype):
        return (q, r, jtype) in self._by_tile

    def count(self, jtype):
        return sum(1 for j in self.jobs if j.jtype == jtype)

    # ------------------------------------------------------------------ tick
    def update(self, dt):
        for job in self.jobs:
            if job.cooldown > 0:
                job.cooldown = max(0.0, job.cooldown - dt)

    # ------------------------------------------------------------------ assign
    def claim(self, agent, game):
        """Reserve and return a job for the agent. Job types are considered in the
        agent's priority order; within the highest-priority type that has any
        available work, the nearest job wins. So a bulldozer always heads for the
        nearest rubble, and workers only fall back to hauling/cleaning when no
        vehicle is automating it."""
        allowed = agent.claimable_kinds(game)
        astart = agent.hex
        for jtype in agent.job_priority():
            if jtype not in allowed:
                continue
            best = None
            best_d = None
            for job in self.jobs:
                if job.agent is not None or job.cooldown > 0 or job.jtype != jtype:
                    continue
                if not self._still_valid(job):
                    continue
                # only a machine whose reach covers this rock may take the mine job
                if jtype == MINE and not self.world.mineable(
                        self.world.get_tile(job.q, job.r), agent.mine_reach):
                    continue
                d = hexgrid.axial_distance(astart, job.pos)
                if best_d is None or d < best_d:
                    best, best_d = job, d
            if best:
                best.agent = agent
                return best
        return None

    def claim_nearest(self, agent, game, jtype):
        """Reserve and return the nearest unclaimed valid job of one type (used to
        chain haul pickups), or None."""
        astart = agent.hex
        best = None
        best_d = None
        for job in self.jobs:
            if job.agent is not None or job.cooldown > 0 or job.jtype != jtype:
                continue
            if not self._still_valid(job):
                continue
            d = hexgrid.axial_distance(astart, job.pos)
            if best_d is None or d < best_d:
                best, best_d = job, d
        if best:
            best.agent = agent
            return best
        return None

    def release(self, job, cooldown=0.0, done=False):
        job.agent = None
        job.cooldown = cooldown
        if done:
            self.remove(job)

    def _still_valid(self, job):
        t = self.world.get_tile(job.q, job.r)
        if job.jtype == MINE:
            # valid if any tier could reach it; per-agent reach is checked in claim()
            return self.world.mineable(t, config.MAX_MINE_REACH)
        if job.jtype == CLEAN:
            return t.state == 1  # RUBBLE
        if job.jtype == BUILD_ROAD:
            return t.state == 2  # EXCAVATED
        if job.jtype == HAUL:
            return bool(t.drops)
        if job.jtype == CONSTRUCT:
            return t.building is not None and not t.building.built
        return False
