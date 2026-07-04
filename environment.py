"""
environment.py — sky ambiance: drifting clouds and animated condors.

World-anchored: clouds and birds live in world coordinates, so they pan and zoom
with the map (zoom in and a cloud gets bigger; pan and it slides past like the
terrain). Deterministic (seeded value-noise hashing, no RNG so it stays
pygbag/WASM-safe). Clouds are an *infinite lattice* of cells, each cell holding a
cloud with probability CLOUD_FILL, so coverage is consistent and controllable by
spacing/fill. Birds are a few wandering instances wrapped in a world band around
the camera. Sprites are placeholders from assets/ (cloud_0/1, bird_0..2) with a
code-drawn fallback, meant to be replaced with real art.
"""

import math

import pygame

import config
import assets
import worldgen

_SPRITE_H = config.HEX_SIZE * 1.5   # world px per row (for altitude from cam.y)


class Environment:
    def __init__(self, seed, n_birds=None):
        self.seed = seed
        self.t = 0.0
        nb = config.SKY_BIRDS if n_birds is None else n_birds
        self.birds = [self._make_bird(i) for i in range(nb)]

    def _h(self, a, b):
        return worldgen._hash01(a, b, self.seed + 4242)

    def _make_bird(self, i):
        # A straight-line heading; horizontal only for now (varied in a later pass).
        sign = 1.0 if self._h(i, 10) > 0.5 else -1.0
        return {
            "fx": self._h(i, 7),
            "fy": self._h(i, 8),
            "vx": (0.5 + 0.7 * self._h(i, 9)) * sign * config.BIRD_DRIFT,
            "vy": 0.0,
            "scale": config.BIRD_SCALE * (0.8 + 0.5 * self._h(i, 12)),
        }

    # ------------------------------------------------------------------ update
    def update(self, dt, cam):
        dt = min(dt, 0.1)
        self.t += dt
        for b in self.birds:
            b["fx"] = (b["fx"] + b["vx"] * dt) % 1.0
            b["fy"] = (b["fy"] + b["vy"] * dt) % 1.0

    # ------------------------------------------------------------------ draw
    def draw(self, surface, cam, show_clouds=True, show_birds=True):
        if show_clouds:
            self._draw_clouds(surface, cam)
        if show_birds:
            self._draw_birds(surface, cam)

    def _visible_world_rect(self, cam):
        wx0, wy0 = cam.screen_to_world(0, 0)
        wx1, wy1 = cam.screen_to_world(cam.screen_w, cam.screen_h)
        return wx0, wy0, wx1, wy1

    def _draw_clouds(self, surface, cam):
        # cloud type shifts wispy as you climb; fluffy low down
        high = _clamp(1.0 - (cam.y / _SPRITE_H + 12) / 48.0)
        sprite = assets.get_sprite("cloud_1" if high > 0.55 else "cloud_0")

        S = config.CLOUD_SPACING
        ox = self.t * config.CLOUD_DRIFT_PX          # the whole field drifts sideways
        wx0, wy0, wx1, wy1 = self._visible_world_rect(cam)
        i0 = int(math.floor((wx0 - ox) / S)) - 1
        i1 = int(math.ceil((wx1 - ox) / S)) + 1
        j0 = int(math.floor(wy0 / S)) - 1
        j1 = int(math.ceil(wy1 / S)) + 1
        for i in range(i0, i1 + 1):
            for j in range(j0, j1 + 1):
                if worldgen._hash01(i, j, self.seed + 4242) > config.CLOUD_FILL:
                    continue                          # this cell has no cloud
                hx = worldgen._hash01(i, j, self.seed + 11)
                hy = worldgen._hash01(i, j, self.seed + 22)
                hs = worldgen._hash01(i, j, self.seed + 33)
                wx = i * S + (hx - 0.5) * S * 0.7 + ox
                wy = j * S + (hy - 0.5) * S * 0.7
                sx, sy = cam.world_to_screen(wx, wy)
                self._blit(surface, sprite, sx, sy,
                           config.CLOUD_SCALE * (0.7 + 0.7 * hs) * cam.zoom,
                           alpha=150 + int(70 * hx), fallback="cloud")

    def _draw_birds(self, surface, cam):
        frame = int(self.t * 5) % 3
        sprite = assets.get_sprite(f"bird_{frame}")
        for b in self.birds:
            wx = cam.x + (b["fx"] - 0.5) * config.SKY_SPAN_W
            wy = cam.y + (b["fy"] - 0.5) * config.SKY_SPAN_H
            sx, sy = cam.world_to_screen(wx, wy)
            self._blit(surface, sprite, sx, sy, b["scale"] * cam.zoom,
                       alpha=255, flip=b["vx"] < 0, fallback="bird")

    def _blit(self, surface, sprite, sx, sy, sc, alpha=255, flip=False, fallback="cloud"):
        # cull off-screen (with generous margin for big zoomed sprites)
        m = 400
        if sx < -m or sx > surface.get_width() + m or sy < -m or sy > surface.get_height() + m:
            return
        if sprite is not None:
            img = pygame.transform.smoothscale(
                sprite, (max(1, int(sprite.get_width() * sc)),
                         max(1, int(sprite.get_height() * sc))))
            if flip:
                img = pygame.transform.flip(img, True, False)
            if alpha < 255:
                img.set_alpha(alpha)
            surface.blit(img, img.get_rect(center=(sx, sy)))
        elif fallback == "cloud":
            r = max(6, int(60 * sc))
            s = pygame.Surface((r * 2, r), pygame.SRCALPHA)
            pygame.draw.ellipse(s, (240, 244, 252, min(255, alpha)), s.get_rect())
            surface.blit(s, s.get_rect(center=(sx, sy)))
        else:
            r = max(3, int(8 * sc))
            pygame.draw.line(surface, (44, 44, 54), (sx - r, sy), (sx, sy - r * 0.6), 2)
            pygame.draw.line(surface, (44, 44, 54), (sx + r, sy), (sx, sy - r * 0.6), 2)


def _clamp(v):
    return max(0.0, min(1.0, v))
