"""
splash.py — the opening splash screen (item 30).

Starts zoomed far out on the mountain summit with the slow-drifting clouds, shows
the title and a "press SPACE" prompt, then on SPACE eases a zoom-in down to the HQ
at (0,0) and hands control to the game at 1x. The world itself is drawn by the
normal renderer (so the summit terrain + clouds show through); this only positions
the camera, animates the zoom, and paints the title overlay.
"""

import math

import pygame

import config
import hexgrid


class Splash:
    def __init__(self, camera):
        self.camera = camera
        self.state = "splash"        # splash -> zooming -> done
        self.t = 0.0
        self._start = None
        # far-out view of the summit (up the slope = negative r), fully zoomed out
        sx, sy = hexgrid.hex_to_pixel(0, -config.SPLASH_SUMMIT_R, config.HEX_SIZE)
        camera.x, camera.y = sx, sy
        camera.zoom = config.MIN_ZOOM
        self._title = pygame.font.SysFont("consolas", 60, bold=True)
        self._sub = pygame.font.SysFont("consolas", 22)

    def active(self):
        return self.state != "done"

    def handle(self, events):
        for e in events:
            if (e.type == pygame.KEYDOWN and e.key == pygame.K_SPACE
                    and self.state == "splash"):
                self.state = "zooming"
                self.t = 0.0
                self._start = (self.camera.x, self.camera.y, self.camera.zoom)

    def update(self, dt):
        if self.state != "zooming":
            return
        self.t += dt
        f = min(1.0, self.t / config.SPLASH_ZOOM_DUR)
        ease = f * f * (3.0 - 2.0 * f)                 # smoothstep
        hqx, hqy = hexgrid.hex_to_pixel(0, 0, config.HEX_SIZE)
        sx, sy, sz = self._start
        self.camera.x = sx + (hqx - sx) * ease
        self.camera.y = sy + (hqy - sy) * ease
        self.camera.zoom = sz + (1.0 - sz) * ease
        if f >= 1.0:
            self.state = "done"

    def draw_overlay(self, screen):
        if self.state != "splash":
            return
        w, h = screen.get_size()
        band = pygame.Surface((w, 170), pygame.SRCALPHA)
        band.fill((10, 14, 26, 150))
        screen.blit(band, (0, h // 2 - 100))
        title = self._title.render("ANDES MINING CORP", True, (240, 224, 180))
        screen.blit(title, title.get_rect(center=(w // 2, h // 2 - 38)))
        pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.004)
        sub = self._sub.render("Press SPACE to start", True, (230, 235, 245))
        sub.set_alpha(int(120 + 135 * pulse))
        screen.blit(sub, sub.get_rect(center=(w // 2, h // 2 + 34)))
