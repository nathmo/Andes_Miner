"""
main.py — entry point and the async game loop (pygbag / web compatible).

The loop is written `async` with an `await asyncio.sleep(0)` each frame so the
exact same code runs natively (desktop) and compiled to WASM in the browser via
pygbag. Real-time simulation is scaled by the player's speed multiplier; pause
freezes the sim but keeps camera/UI responsive.
"""

import sys
import asyncio
import pygame

import config
from camera import Camera
from game import Game
from render import Renderer
from ui import UI
from input import InputHandler
from splash import Splash
import save as savemod


def _enable_dpi_awareness():
    """On Windows, opt into real (physical) pixels. Without this, display scaling
    (125%/150%) makes Windows silently upscale the window, so an 800px window can
    become ~1200 physical px and its bottom (the action bar) falls off-screen."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)   # per-monitor aware (Win 8.1+)
        except Exception:
            ctypes.windll.user32.SetProcessDPIAware()        # system aware (older)
    except Exception:
        pass


async def main():
    _enable_dpi_awareness()
    pygame.init()
    pygame.display.set_caption(config.TITLE)

    # Fit the initial window to the desktop so the bottom action bar is never
    # pushed off-screen (too-tall window, or display-scaling overflow).
    win_w, win_h = config.WINDOW_WIDTH, config.WINDOW_HEIGHT
    try:
        dw, dh = pygame.display.get_desktop_sizes()[0]
        win_w = min(win_w, dw - 20)
        win_h = max(480, min(win_h, dh - 120))   # leave room for title bar + taskbar
    except Exception:
        pass
    screen = pygame.display.set_mode((win_w, win_h), pygame.RESIZABLE)
    clock = pygame.time.Clock()

    camera = Camera(win_w, win_h)
    game = Game(seed=config.WORLD_SEED, camera=camera)
    renderer = Renderer()
    ui = UI(win_w, win_h)
    inp = InputHandler()
    splash = Splash(camera)

    running = True
    while running:
        dt = clock.tick(config.FPS) / 1000.0
        dt = min(dt, 0.1)  # clamp after stalls

        events = pygame.event.get()
        for e in events:
            if e.type == pygame.QUIT:
                running = False
            elif e.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode((e.w, e.h), pygame.RESIZABLE)
                camera.resize(e.w, e.h)
                ui.resize(e.w, e.h)

        # Splash intro: far summit view + title, then zoom in to HQ on SPACE.
        if splash.active():
            splash.handle(events)
            splash.update(dt)
            renderer.draw(screen, game)
            splash.draw_overlay(screen)
            pygame.display.flip()
            if not splash.active():
                game.log("Mark rock near the road to start mining (Mine tool).")
            await asyncio.sleep(0)
            continue

        if inp.handle(events, game, ui, camera) == "quit":
            running = False

        camera.pan_keys(pygame.key.get_pressed(), dt)

        sim_dt = dt * game.sim_multiplier()
        game.update(sim_dt, dt)

        # save / load requests
        if game.want_save:
            game.want_save = False
            try:
                savemod.save_game(game)
                game.log("Game saved")
            except Exception as ex:
                game.log(f"Save failed: {ex}")
        if game.want_quit:                 # settings -> Save & Quit (save ran above)
            running = False
        if game.want_load:
            game.want_load = False
            try:
                loaded = savemod.load_game(camera=camera)
                if loaded:
                    game = loaded
                    game.log("Game loaded")
                else:
                    game.log("No save file found")
            except Exception as ex:
                game.log(f"Load failed: {ex}")
        if game.want_load_path:
            path = game.want_load_path
            game.want_load_path = None
            try:
                loaded = savemod.load_game(path=path, camera=camera)
                if loaded:
                    game = loaded
                    game.log("Restored backup")
                else:
                    game.log("Backup not found")
            except Exception as ex:
                game.log(f"Load failed: {ex}")

        # autosave
        if game._autosave_t >= config.AUTOSAVE_INTERVAL:
            game._autosave_t = 0.0
            try:
                savemod.save_game(game)
                game.log("Auto-saved")
            except Exception:
                pass

        # rolling exponential backups
        if game._backup_t >= config.BACKUP_INTERVAL:
            game._backup_t = 0.0
            try:
                savemod.rolling_backup(game)
                game.log("Backup saved")
            except Exception:
                pass

        renderer.draw(screen, game)
        ui.draw(screen, game)
        pygame.display.flip()

        await asyncio.sleep(0)

    pygame.quit()


if __name__ == "__main__":
    asyncio.run(main())
