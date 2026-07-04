"""
environment.py — sky ambiance: drifting clouds and animated condors (item 25).

Purely decorative and deterministic (seeded value-noise hashing, no RNG so it
stays pygbag/WASM-safe). Clouds slide slowly left/right across the display; the
cloud *type* and the number of visible birds depend on the altitude currently in
view (low on the slope → fluffy clouds + many birds; high up → thin wispy clouds
+ few birds). Sprites are placeholders loaded from assets/ (cloud_0, cloud_1,
bird_0..2) with a code-drawn fallback, meant to be replaced with real art.
"""

import pygame

import config
import assets
import worldgen

_SPRITE_H = config.HEX_SIZE * 1.5   # world px per row (for altitude from cam.y)


class Environment:
    def __init__(self, seed, n_clouds=11, n_birds=16):
        self.seed = seed
        self.t = 0.0
        self.clouds = [self._make_cloud(i) for i in range(n_clouds)]
        self.birds = [self._make_bird(i) for i in range(n_birds)]

    def _h(self, a, b):
        return worldgen._hash01(a, b, self.seed + 4242)

    def _make_cloud(self, i):
        return {
            "x": self._h(i, 1),                       # fraction of width [0,1)
            "y": 0.04 + 0.46 * self._h(i, 2),         # upper-screen band
            "scale": 0.6 + 1.5 * self._h(i, 3),
            "vx": (self._h(i, 4) - 0.5) * 0.03,       # slow drift (frac/sec)
            "alpha": 150 + int(80 * self._h(i, 6)),
        }

    def _make_bird(self, i):
        return {
            "x": self._h(i, 7),
            "y": 0.42 + 0.5 * self._h(i, 8),
            "vx": (0.02 + 0.05 * self._h(i, 9)) * (1 if self._h(i, 10) > 0.5 else -1),
            "phase": self._h(i, 11),
            "scale": 0.7 + 0.7 * self._h(i, 12),
        }

    # ------------------------------------------------------------------ update
    def update(self, dt, cam):
        dt = min(dt, 0.1)
        self.t += dt
        for c in self.clouds:
            c["x"] = (c["x"] + c["vx"] * dt) % 1.0
        for b in self.birds:
            b["x"] = (b["x"] + b["vx"] * dt) % 1.0

    # ------------------------------------------------------------------ draw
    def draw(self, surface, cam):
        w, h = cam.screen_w, cam.screen_h
        # altitude in view: row at screen centre (higher row = lower on the slope)
        row = cam.y / _SPRITE_H
        ground = _clamp((row + 12) / 48.0)      # 0 high up, 1 down near the base
        high = 1.0 - ground

        # cloud type shifts wispy as you climb; fluffy low down
        ckey = "cloud_1" if high > 0.55 else "cloud_0"
        cloud = assets.get_sprite(ckey)
        for c in self.clouds:
            self._blit_cloud(surface, cloud, c, w, h, high)

        # more birds toward the ground, fewer up high
        nb = int(len(self.birds) * (0.12 + 0.88 * ground))
        frame = int(self.t * 5) % 3
        bird = assets.get_sprite(f"bird_{frame}")
        for b in self.birds[:nb]:
            self._blit_bird(surface, bird, b, w, h)

    def _blit_cloud(self, surface, sprite, c, w, h, high):
        px, py = int(c["x"] * w), int(c["y"] * h)
        if sprite is not None:
            sc = c["scale"] * (0.8 if high > 0.55 else 1.0)
            img = pygame.transform.smoothscale(
                sprite, (max(1, int(sprite.get_width() * sc)),
                         max(1, int(sprite.get_height() * sc))))
            img.set_alpha(c["alpha"])
            surface.blit(img, img.get_rect(center=(px, py)))
        else:
            s = pygame.Surface((120, 60), pygame.SRCALPHA)
            pygame.draw.ellipse(s, (240, 244, 252, 90), s.get_rect())
            surface.blit(s, s.get_rect(center=(px, py)))

    def _blit_bird(self, surface, sprite, b, w, h):
        px, py = int(b["x"] * w), int(b["y"] * h)
        if sprite is not None:
            sc = b["scale"]
            img = pygame.transform.smoothscale(
                sprite, (max(1, int(sprite.get_width() * sc)),
                         max(1, int(sprite.get_height() * sc))))
            if b["vx"] < 0:
                img = pygame.transform.flip(img, True, False)
            surface.blit(img, img.get_rect(center=(px, py)))
        else:
            pygame.draw.line(surface, (44, 44, 54), (px - 6, py), (px, py - 4), 2)
            pygame.draw.line(surface, (44, 44, 54), (px + 6, py), (px, py - 4), 2)


def _clamp(v):
    return max(0.0, min(1.0, v))
