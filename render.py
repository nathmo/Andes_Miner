"""
render.py — draws the world as isometric-cube hexes plus overlays and entities.

Solid rock is drawn as a raised cube (top + two shaded side faces) so the map
reads as a mountain slope; dug tiles (rubble/excavated/road) are drawn as flat,
recessed floor. Overlays: mine marks, mineable hints, ore drops, buildings,
agents, selection rectangle, hover.
"""

import math

import pygame

import config
import hexgrid
import assets
from tiles import ROCK, RUBBLE, EXCAVATED, ROAD
from jobs import CLEAN, BUILD_ROAD


_SQRT3 = 3.0 ** 0.5


def _shade(color, mult):
    return (min(255, int(color[0] * mult)),
            min(255, int(color[1] * mult)),
            min(255, int(color[2] * mult)))


class Renderer:
    def __init__(self):
        self.font = pygame.font.SysFont("consolas", 14)
        self.font_small = pygame.font.SysFont("consolas", 11)
        self._sprite_cache = {}      # (key, target_w) -> scaled Surface

    def _blit_sprite(self, surface, key, sprite, cx, cy, target_w):
        tw = max(1, int(target_w))
        ck = (key, tw)
        sc = self._sprite_cache.get(ck)
        if sc is None:
            scale = tw / sprite.get_width()
            th = max(1, int(sprite.get_height() * scale))
            sc = pygame.transform.smoothscale(sprite, (tw, th))
            self._sprite_cache[ck] = sc
        surface.blit(sc, sc.get_rect(center=(int(cx), int(cy))))

    def _blit_tile(self, surface, key, sprite, cx, cy, hex_w):
        """Blit a tile sprite centred on the hex, scaled to the hex width plus a
        1px overscan so adjacent tiles leave no seam."""
        tw = max(2, int(hex_w) + 2)
        ck = ("T", key, tw)
        sc = self._sprite_cache.get(ck)
        if sc is None:
            scale = tw / sprite.get_width()
            th = max(2, int(round(sprite.get_height() * scale)))
            sc = pygame.transform.smoothscale(sprite, (tw, th))
            self._sprite_cache[ck] = sc
        surface.blit(sc, sc.get_rect(center=(int(cx), int(cy))))

    # ------------------------------------------------------------------ main
    def draw(self, surface, game):
        surface.fill(config.COL_BG)
        cam = game.camera
        size = cam.hex_pixel_size
        q_lo, q_hi, r_lo, r_hi = cam.visible_hex_box()

        show_mine_hint = game.tool == "mine"

        # Draw tiles back-to-front (increasing r = down the slope) for overlap.
        for r in range(r_lo, r_hi + 1):
            for q in range(q_lo, q_hi + 1):
                tile = game.world.get_tile(q, r)
                wx, wy = hexgrid.hex_to_pixel(q, r, config.HEX_SIZE)
                cx, cy = cam.world_to_screen(wx, wy)
                self._draw_tile(surface, tile, cx, cy, size, show_mine_hint, game)

        # Drops (ore / rubble piles), buildings, agents on top.
        self._draw_buildings(surface, game, cam, size)
        self._draw_drops(surface, game, cam, size, q_lo, q_hi, r_lo, r_hi)
        self._draw_agents(surface, game, cam, size)

        # Placement / selection previews.
        self._draw_hover(surface, game, cam, size)
        self._draw_selection(surface, game)

    # ------------------------------------------------------------------ tiles
    def _draw_tile(self, surface, tile, cx, cy, size, show_mine_hint, game):
        c = hexgrid.hex_corners(cx, cy, size)
        center = (cx, cy)
        hex_w = _SQRT3 * size

        if tile.state == ROCK:
            key = "tile_" + tile.rock
            sprite = assets.get_sprite(key)
            if sprite:
                self._blit_tile(surface, key, sprite, cx, cy, hex_w)
            else:
                base = tile.base_color
                top = [center, c[5], c[0], c[1]]
                left = [center, c[5], c[4], c[3]]
                right = [center, c[1], c[2], c[3]]
                pygame.draw.polygon(surface, _shade(base, config.SHADE_TOP), top)
                pygame.draw.polygon(surface, _shade(base, config.SHADE_LEFT), left)
                pygame.draw.polygon(surface, _shade(base, config.SHADE_RIGHT), right)
                pygame.draw.line(surface, (0, 0, 0), center, c[5], 1)
                pygame.draw.line(surface, (0, 0, 0), center, c[1], 1)
                pygame.draw.line(surface, (0, 0, 0), center, c[3], 1)
                pygame.draw.polygon(surface, (0, 0, 0), c, 1)

            if show_mine_hint and game.world.mineable(tile):
                pygame.draw.polygon(surface, config.COL_MINEABLE, [c[5], c[0], c[1]], 2)
        else:
            if tile.state == ROAD:
                key, fill = "tile_road", config.COL_ROAD
            elif tile.state == EXCAVATED:
                # tinted per original rock so excavated andesite != excavated basalt
                key, fill = "tile_excavated_" + tile.rock, tile.excavated_color
            else:
                key, fill = "tile_rubble", config.COL_RUBBLE
            sprite = assets.get_sprite(key)
            if sprite is None and tile.state == EXCAVATED:
                sprite = assets.get_sprite("tile_excavated")   # generic fallback
            if sprite:
                self._blit_tile(surface, key, sprite, cx, cy, hex_w)
            else:
                pygame.draw.polygon(surface, fill, c)
                pygame.draw.polygon(surface, _shade(fill, 0.6), c, 1)
                if tile.state == ROAD and size > 10:
                    pygame.draw.line(surface, _shade(fill, 1.4),
                                     (cx - size * 0.4, cy), (cx + size * 0.4, cy), max(1, int(size * 0.06)))

        if tile.marked:
            pygame.draw.polygon(surface, config.COL_MARK, c, max(2, int(size * 0.10)))
            r = size * 0.28
            pygame.draw.line(surface, config.COL_MARK, (cx - r, cy - r), (cx + r, cy + r), 2)
            pygame.draw.line(surface, config.COL_MARK, (cx + r, cy - r), (cx - r, cy + r), 2)
        # animated overlays for tiles queued to be cleaned / turned into road
        elif tile.state == RUBBLE and game.jobs.has_job(tile.q, tile.r, CLEAN):
            self._draw_scheduled(surface, c, cx, cy, size, config.COL_CLEAN_MARK, "clean")
        elif tile.state == EXCAVATED and game.jobs.has_job(tile.q, tile.r, BUILD_ROAD):
            self._draw_scheduled(surface, c, cx, cy, size, config.COL_ROAD_MARK, "road")

    def _draw_scheduled(self, surface, c, cx, cy, size, col, kind):
        """Pulsing overlay marking a tile queued for cleaning or road building."""
        pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.006)
        pygame.draw.polygon(surface, col, c, max(2, int(size * (0.07 + 0.05 * pulse))))
        if kind == "clean":
            r = size * 0.30                        # a little sweep arc
            rect = pygame.Rect(int(cx - r), int(cy - r), int(2 * r), int(2 * r))
            pygame.draw.arc(surface, col, rect, 0.5, 2.7, max(2, int(size * 0.09)))
        else:                                      # road preview centre line
            pygame.draw.line(surface, col, (cx - size * 0.4, cy), (cx + size * 0.4, cy),
                             max(2, int(size * 0.10)))

    # ------------------------------------------------------------------ drops
    def _draw_drops(self, surface, game, cam, size, q_lo, q_hi, r_lo, r_hi):
        for r in range(r_lo, r_hi + 1):
            for q in range(q_lo, q_hi + 1):
                tile = game.world.get_tile(q, r)
                if not tile.drops:
                    continue
                wx, wy = hexgrid.hex_to_pixel(q, r, config.HEX_SIZE)
                cx, cy = cam.world_to_screen(wx, wy)
                # up to 3 markers total, one colour per resource on the pile
                cols = []
                for res, amt in tile.drops.items():
                    cols += [config.RESOURCE_COLOR.get(res, (200, 200, 200))] * amt
                cols = cols[:3]
                rad = max(3, int(size * 0.20))
                n = len(cols)
                for i, col in enumerate(cols):
                    ox = cx + (i - (n - 1) / 2.0) * rad * 0.95
                    pygame.draw.circle(surface, col, (int(ox), int(cy)), rad)
                    pygame.draw.circle(surface, _shade(col, 0.6), (int(ox), int(cy)), rad, 1)

    # ------------------------------------------------------------------ buildings
    def _draw_buildings(self, surface, game, cam, size):
        for b in game.buildings:
            wx, wy = hexgrid.hex_to_pixel(b.q, b.r, config.HEX_SIZE)
            cx, cy = cam.world_to_screen(wx, wy)
            info = config.BUILDINGS[b.btype]
            col = info["color"]
            s = size * 0.7
            rect = pygame.Rect(0, 0, s * 1.4, s * 1.4)
            rect.center = (cx, cy - s * 0.3)
            if not b.built:
                # ghost + progress
                ghost = pygame.Surface(rect.size, pygame.SRCALPHA)
                ghost.fill((*col, 110))
                surface.blit(ghost, rect.topleft)
                pygame.draw.rect(surface, config.COL_ACCENT, rect, 2)
                frac = b.progress
                pygame.draw.rect(surface, config.COL_ACCENT,
                                 (rect.left, rect.bottom - 4, rect.width * frac, 4))
            else:
                sprite = assets.get_sprite(b.btype)
                if sprite:
                    self._blit_sprite(surface, b.btype, sprite, rect.centerx, rect.centery, size * 1.5)
                else:
                    pygame.draw.rect(surface, col, rect, border_radius=int(s * 0.15))
                    pygame.draw.rect(surface, _shade(col, 0.55), rect, 2, border_radius=int(s * 0.15))
                    letter = info["name"][0]
                    if size > 12:
                        label = self.font.render(letter, True, (12, 12, 16))
                        surface.blit(label, label.get_rect(center=rect.center))

    # ------------------------------------------------------------------ agents
    def _draw_agents(self, surface, game, cam, size):
        for a in game.iter_agents():
            cx, cy = cam.world_to_screen(a.px, a.py)
            rad = max(4, int(size * 0.24))
            sprite = assets.get_sprite(a.kind)
            if sprite:
                tw = size * (0.7 if a.kind == "worker" else 1.3)
                self._blit_sprite(surface, a.kind, sprite, cx, cy, tw)
            elif a.kind == "worker":
                pygame.draw.circle(surface, (70, 200, 120), (int(cx), int(cy)), rad)
                pygame.draw.circle(surface, (20, 90, 50), (int(cx), int(cy)), rad, 2)
            else:
                col = config.VEHICLES[a.kind]["color"]
                rect = pygame.Rect(0, 0, rad * 2.2, rad * 1.7)
                rect.center = (cx, cy)
                pygame.draw.rect(surface, col, rect, border_radius=3)
                pygame.draw.rect(surface, _shade(col, 0.5), rect, 2, border_radius=3)
            # carrying indicator (coloured by the first resource on board)
            if getattr(a, "carrying", None):
                res = next(iter(a.carrying))
                oc = config.RESOURCE_COLOR.get(res, (200, 200, 200))
                pygame.draw.circle(surface, oc, (int(cx), int(cy - rad - 3)), max(2, int(rad * 0.4)))
            # working flash
            if a.state == "WORKING" and (int(a.work_timer * 6) % 2 == 0):
                pygame.draw.circle(surface, config.COL_ACCENT, (int(cx), int(cy)), rad + 3, 1)

    # ------------------------------------------------------------------ hover / preview
    def _draw_hover(self, surface, game, cam, size):
        if game.hover_hex is None:
            return
        q, r = game.hover_hex
        wx, wy = hexgrid.hex_to_pixel(q, r, config.HEX_SIZE)
        cx, cy = cam.world_to_screen(wx, wy)
        c = hexgrid.hex_corners(cx, cy, size)
        col = config.COL_SELECT_RECT
        if game.tool in ("road", "build"):
            ok = game.can_place_here(q, r)
            col = (110, 220, 130) if ok else (220, 90, 90)
        pygame.draw.polygon(surface, col, c, 2)

    def _draw_selection(self, surface, game):
        if game.selection_rect:
            x0, y0, x1, y1 = game.selection_rect
            rect = pygame.Rect(min(x0, x1), min(y0, y1), abs(x1 - x0), abs(y1 - y0))
            s = pygame.Surface(rect.size, pygame.SRCALPHA)
            s.fill((*config.COL_SELECT_RECT, 40))
            surface.blit(s, rect.topleft)
            pygame.draw.rect(surface, config.COL_SELECT_RECT, rect, 1)
