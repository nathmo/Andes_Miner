"""
camera.py — pan, zoom, and world<->screen transforms.

Holds a world-space focus point (the pixel the screen centre looks at) and a
zoom factor. Also computes the visible axial-coordinate box so the renderer
only touches on-screen tiles (essential for an infinite map).
"""

import config
import hexgrid


class Camera:
    def __init__(self, screen_w, screen_h):
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.x = 0.0                    # world-space focus (px at zoom 1.0)
        self.y = 0.0
        self.zoom = 1.0
        # centre on the HQ at (0, 0)
        hx, hy = hexgrid.hex_to_pixel(0, 0, config.HEX_SIZE)
        self.x, self.y = hx, hy

    # ------------------------------------------------------------------ resize
    def resize(self, w, h):
        self.screen_w, self.screen_h = w, h

    # ------------------------------------------------------------------ transforms
    def world_to_screen(self, wx, wy):
        sx = (wx - self.x) * self.zoom + self.screen_w / 2
        sy = (wy - self.y) * self.zoom + self.screen_h / 2
        return sx, sy

    def screen_to_world(self, sx, sy):
        wx = (sx - self.screen_w / 2) / self.zoom + self.x
        wy = (sy - self.screen_h / 2) / self.zoom + self.y
        return wx, wy

    def screen_to_hex(self, sx, sy):
        wx, wy = self.screen_to_world(sx, sy)
        return hexgrid.pixel_to_hex(wx, wy, config.HEX_SIZE)

    @property
    def hex_pixel_size(self):
        return config.HEX_SIZE * self.zoom

    # ------------------------------------------------------------------ movement
    def pan_screen(self, dx_screen, dy_screen):
        """Pan by a screen-space delta (used by drag)."""
        self.x -= dx_screen / self.zoom
        self.y -= dy_screen / self.zoom

    def pan_keys(self, keys, dt):
        import pygame
        vx = vy = 0.0
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            vx -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            vx += 1
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            vy -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            vy += 1
        if vx or vy:
            speed = config.CAM_PAN_SPEED / self.zoom * dt
            self.x += vx * speed
            self.y += vy * speed

    def zoom_at(self, sx, sy, factor):
        """Zoom keeping the world point under the cursor fixed."""
        wx, wy = self.screen_to_world(sx, sy)
        self.zoom = max(config.MIN_ZOOM, min(config.MAX_ZOOM, self.zoom * factor))
        # re-anchor so (wx, wy) stays under the cursor
        nsx, nsy = self.world_to_screen(wx, wy)
        self.x += (nsx - sx) / self.zoom
        self.y += (nsy - sy) / self.zoom

    # ------------------------------------------------------------------ culling
    def visible_hex_box(self):
        """Inclusive (q_lo, q_hi, r_lo, r_hi) covering the screen, with margin."""
        corners = [
            self.screen_to_world(0, 0),
            self.screen_to_world(self.screen_w, 0),
            self.screen_to_world(0, self.screen_h),
            self.screen_to_world(self.screen_w, self.screen_h),
        ]
        qs, rs = [], []
        for (wx, wy) in corners:
            q, r = hexgrid.pixel_to_hex(wx, wy, config.HEX_SIZE)
            qs.append(q)
            rs.append(r)
        margin = 2
        return (min(qs) - margin, max(qs) + margin,
                min(rs) - margin, max(rs) + margin)
