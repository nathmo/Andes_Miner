"""
tools/screenshot.py — render one frame of the game to a PNG, headlessly.

Used to produce docs/screenshot.png for the README (and by CI, if ever wanted).
Loads andes_save.json when present so the shot shows an actual operation —
roads, buildings, excavation — instead of an empty starting slope. Falls back to
a fresh world otherwise.

    python tools/screenshot.py [out_path]

Runs under SDL's dummy video driver, so it needs no real display.
"""

import os
import sys

# Headless: pick the dummy driver before pygame touches the display.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

# Allow running as `python tools/screenshot.py` from the repo root.
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import pygame

import config
from camera import Camera
from game import Game
from render import Renderer
from ui import UI
import save as savemod

WIDTH = int(os.environ.get("SHOT_W", 1440))
HEIGHT = int(os.environ.get("SHOT_H", 900))
SIM_SECONDS = float(os.environ.get("SHOT_SIM", 2.5))   # let agents spread out
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(_ROOT, "docs", "screenshot.png")


def build_game(camera):
    save_path = os.path.join(_ROOT, config.SAVE_FILE)
    if os.path.isfile(save_path):
        try:
            g = savemod.load_game(path=save_path, camera=camera)
            if g is not None:
                return g, True
        except Exception as ex:  # corrupt/incompatible save -> fresh world
            print(f"screenshot: could not load save ({ex}); using fresh world")
    return Game(seed=config.WORLD_SEED, camera=camera), False


def main():
    pygame.init()
    pygame.display.set_caption(config.TITLE)
    screen = pygame.display.set_mode((WIDTH, HEIGHT))

    camera = Camera(WIDTH, HEIGHT)
    game, from_save = build_game(camera)
    camera.resize(WIDTH, HEIGHT)

    # Optional framing overrides: recenter on HQ and/or force a zoom level.
    if os.environ.get("SHOT_HOME"):
        game.center_camera_home()
    if os.environ.get("SHOT_ZOOM"):
        camera.zoom = max(config.MIN_ZOOM, min(config.MAX_ZOOM, float(os.environ["SHOT_ZOOM"])))

    renderer = Renderer()
    ui = UI(WIDTH, HEIGHT)

    # Clean marketing frame: no tool overlays, no leftover strike banner spam.
    game.tool = "select"
    game.hover_hex = None
    game.selection_rect = None
    game.selected_building = None
    game.paused = False

    # Advance the simulation a little so crews path out of HQ and look busy.
    step = 1.0 / 60.0
    steps = int(SIM_SECONDS / step)
    for _ in range(steps):
        try:
            game.update(step, step)
        except Exception as ex:
            print(f"screenshot: sim step failed ({ex}); rendering current state")
            break

    game.messages = []  # drop transient toasts for a clean shot

    renderer.draw(screen, game)
    ui.draw(screen, game)
    pygame.display.flip()

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    pygame.image.save(screen, OUT)
    print(f"screenshot: wrote {OUT} ({WIDTH}x{HEIGHT}, from_save={from_save})")
    pygame.quit()


if __name__ == "__main__":
    main()
