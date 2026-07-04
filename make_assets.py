"""
make_assets.py — export the built-in placeholder shapes as editable PNGs.

Run this once (or any time you want to reset the art) to drop a starter sprite
for every worker, vehicle, and building into ./assets. Edit or replace those
PNGs freely — the game loads them automatically (see assets.py). Delete a PNG to
fall back to the code-drawn shape.

    python make_assets.py
"""

import os
import math
import pygame

import config
import hexgrid

ASSET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

# Tile sprites are authored at this hex radius (centre-to-vertex). The canvas is
# sized to the pointy-top hex bounding box so the art fills the cell exactly with
# no padding — keep that ratio (W = sqrt(3)*R, H = 2*R) in any replacement art or
# tiles won't line up on the grid.
TILE_R = 64
_SQRT3 = math.sqrt(3.0)


def _shade(c, m):
    return (min(255, int(c[0] * m)), min(255, int(c[1] * m)), min(255, int(c[2] * m)))


def _save(surf, name):
    pygame.image.save(surf, os.path.join(ASSET_DIR, name + ".png"))
    print("wrote", name + ".png")


def worker_sprite():
    s = pygame.Surface((48, 48), pygame.SRCALPHA)
    pygame.draw.circle(s, (70, 200, 120), (24, 26), 18)          # body
    pygame.draw.circle(s, (20, 90, 50), (24, 26), 18, 3)
    pygame.draw.circle(s, (235, 215, 180), (24, 14), 8)          # head
    pygame.draw.circle(s, (20, 90, 50), (24, 14), 8, 2)
    return s


def vehicle_sprite(col):
    w, h = 72, 54
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    body = pygame.Rect(6, 12, w - 12, h - 24)
    pygame.draw.rect(s, col, body, border_radius=8)
    pygame.draw.rect(s, _shade(col, 0.5), body, 3, border_radius=8)
    pygame.draw.rect(s, _shade(col, 1.35), (w - 28, 18, 15, 11), border_radius=3)  # cabin
    pygame.draw.circle(s, (28, 28, 32), (20, h - 12), 9)         # wheels
    pygame.draw.circle(s, (28, 28, 32), (w - 20, h - 12), 9)
    pygame.draw.circle(s, (70, 70, 76), (20, h - 12), 4)
    pygame.draw.circle(s, (70, 70, 76), (w - 20, h - 12), 4)
    return s


def _tile_canvas():
    """Transparent surface sized to the hex bounding box, with the hex centre."""
    w = int(round(_SQRT3 * TILE_R))
    h = 2 * TILE_R
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    return s, (w / 2.0, h / 2.0)


def rock_tile_sprite(color):
    """A solid rock, drawn as a raised isometric cube (top + two shaded sides)."""
    s, (cx, cy) = _tile_canvas()
    c = hexgrid.hex_corners(cx, cy, TILE_R)
    center = (cx, cy)
    top = [center, c[5], c[0], c[1]]
    left = [center, c[5], c[4], c[3]]
    right = [center, c[1], c[2], c[3]]
    pygame.draw.polygon(s, _shade(color, config.SHADE_TOP), top)
    pygame.draw.polygon(s, _shade(color, config.SHADE_LEFT), left)
    pygame.draw.polygon(s, _shade(color, config.SHADE_RIGHT), right)
    for corner in (c[5], c[1], c[3]):            # the three cube edges from centre
        pygame.draw.line(s, (0, 0, 0), center, corner, 2)
    pygame.draw.polygon(s, (0, 0, 0), c, 2)      # outer silhouette
    return s


def floor_tile_sprite(fill, road=False):
    """A dug/flat tile (rubble / excavated / road), drawn as recessed floor."""
    s, (cx, cy) = _tile_canvas()
    c = hexgrid.hex_corners(cx, cy, TILE_R)
    pygame.draw.polygon(s, fill, c)
    pygame.draw.polygon(s, _shade(fill, 0.6), c, 2)
    if road:
        pygame.draw.line(s, _shade(fill, 1.4),
                         (cx - TILE_R * 0.4, cy), (cx + TILE_R * 0.4, cy), 5)
    return s


def building_sprite(col, letter):
    n = 84
    s = pygame.Surface((n, n), pygame.SRCALPHA)
    rect = pygame.Rect(8, 8, n - 16, n - 16)
    pygame.draw.rect(s, col, rect, border_radius=12)
    pygame.draw.rect(s, _shade(col, 0.55), rect, 4, border_radius=12)
    pygame.draw.rect(s, _shade(col, 1.2), (rect.x + 6, rect.y + 6, rect.w - 12, 10), border_radius=4)
    font = pygame.font.SysFont("consolas", 44, bold=True)
    lab = font.render(letter, True, (14, 14, 18))
    s.blit(lab, lab.get_rect(center=(rect.centerx, rect.centery + 6)))
    return s


# Emoji fonts to try, in order, across the three desktop platforms.
_EMOJI_FONTS = "segoe ui emoji,apple color emoji,noto color emoji"


def _has_pixels(surf):
    """True if the surface has a meaningful (non-empty, non-tofu) glyph."""
    w, h = surf.get_size()
    if w < 4 or h < 4:
        return False
    hits = 0
    for y in range(0, h, 4):
        for x in range(0, w, 4):
            if surf.get_at((x, y))[3] > 24:
                hits += 1
    return hits > 6


def emoji_sprite(chars, px=128):
    """Render a color-emoji glyph to a square-ish PNG, or None if unavailable.

    Uses the platform emoji font; foreground colour is ignored for colour
    glyphs. The result is scaled to fit a `px` box, aspect preserved.
    """
    try:
        font = pygame.font.SysFont(_EMOJI_FONTS, 96)
        surf = font.render(chars, True, (255, 255, 255)).convert_alpha()
    except Exception:
        return None
    if not _has_pixels(surf):
        return None
    w, h = surf.get_size()
    scale = px / float(max(w, h))
    return pygame.transform.smoothscale(surf, (max(1, int(w * scale)), max(1, int(h * scale))))


def iced_coffee_fallback(px=128):
    """Hand-drawn iced-coffee cup, used when no emoji font is available."""
    s = pygame.Surface((px, px), pygame.SRCALPHA)
    cup = pygame.Rect(int(px * 0.28), int(px * 0.24), int(px * 0.44), int(px * 0.62))
    pygame.draw.rect(s, (225, 232, 240), cup, border_radius=6)           # clear cup
    coffee = pygame.Rect(cup.x, int(px * 0.44), cup.w, int(px * 0.42))
    pygame.draw.rect(s, (120, 78, 52), coffee, border_bottom_left_radius=6, border_bottom_right_radius=6)
    for (ix, iy) in [(0.36, 0.5), (0.52, 0.58), (0.42, 0.66)]:           # ice cubes
        r = pygame.Rect(int(px * ix), int(px * iy), int(px * 0.1), int(px * 0.1))
        pygame.draw.rect(s, (205, 228, 240), r, border_radius=2)
    pygame.draw.line(s, (230, 90, 110), (int(px * 0.6), int(px * 0.14)),
                     (int(px * 0.5), int(px * 0.5)), max(2, px // 24))    # straw
    pygame.draw.rect(s, (90, 60, 40), cup, 2, border_radius=6)
    return s


def coin_sprite(col=(66, 132, 232), px=96):
    """A blue circular coin (jammies — the game's money)."""
    s = pygame.Surface((px, px), pygame.SRCALPHA)
    c = px // 2
    r = int(px * 0.44)
    pygame.draw.circle(s, _shade(col, 0.55), (c, c), r)                 # dark rim
    pygame.draw.circle(s, col, (c, c), r - max(2, px // 28))            # face
    pygame.draw.circle(s, _shade(col, 1.28), (c, c), int(r * 0.66))     # inner disk
    d = int(r * 0.42)                                                   # centre gem
    pts = [(c, c - d), (c + d, c), (c, c + d), (c - d, c)]
    pygame.draw.polygon(s, _shade(col, 1.55), pts)
    pygame.draw.polygon(s, _shade(col, 0.70), pts, 2)
    pygame.draw.circle(s, (235, 242, 255), (int(c - r * 0.34), int(c - r * 0.34)),
                       max(2, px // 16))                                # specular
    return s


def main():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    pygame.init()
    os.makedirs(ASSET_DIR, exist_ok=True)

    # tiles: one cube per rock type, plus the three floor states
    for key, info in config.ROCK_TYPES.items():
        _save(rock_tile_sprite(info[1]), "tile_" + key)
    _save(floor_tile_sprite(config.COL_RUBBLE), "tile_rubble")
    _save(floor_tile_sprite(config.COL_EXCAVATED), "tile_excavated")
    _save(floor_tile_sprite(config.COL_ROAD, road=True), "tile_road")

    _save(worker_sprite(), "worker")
    for key, info in config.VEHICLES.items():
        _save(vehicle_sprite(info["color"]), key)
    for key, info in config.BUILDINGS.items():
        _save(building_sprite(info["color"], info["name"][0]), key)

    # HUD icons: iced coffee (worker wages) — emoji where available, else drawn.
    _save(emoji_sprite("\U0001F9CB") or iced_coffee_fallback(), "iced_coffee")
    _save(coin_sprite(), "jammies")                     # money

    pygame.quit()
    print("Done. Edit the PNGs in ./assets and re-run the game to see changes.")


if __name__ == "__main__":
    main()
