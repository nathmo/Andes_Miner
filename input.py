"""
input.py — turns pygame events into game actions.

Mouse: LMB acts with the current tool (single click or drag-box to mark, paint
roads), RMB cancels a designation, MMB (or LMB with the Pan tool) drags the
camera, wheel zooms at the cursor. Keyboard: tool shortcuts, speed/pause,
save/load. WASD/arrow panning is polled per-frame in main via camera.pan_keys.
"""

import pygame
import config
import hexgrid


class InputHandler:
    def __init__(self):
        self.pan_active = False
        self.box_start = None       # screen pos where a mine drag began
        self.painting = False       # holding LMB to paint roads
        self.paint_last = None

    def handle(self, events, game, ui, camera):
        for e in events:
            if e.type == pygame.QUIT:
                return "quit"

            elif e.type == pygame.MOUSEBUTTONDOWN:
                self._mouse_down(e, game, ui, camera)
            elif e.type == pygame.MOUSEBUTTONUP:
                self._mouse_up(e, game, ui, camera)
            elif e.type == pygame.MOUSEMOTION:
                self._mouse_move(e, game, ui, camera)
            elif e.type == pygame.MOUSEWHEEL:
                mx, my = pygame.mouse.get_pos()
                factor = config.ZOOM_STEP if e.y > 0 else 1.0 / config.ZOOM_STEP
                camera.zoom_at(mx, my, factor)
            elif e.type == pygame.KEYDOWN:
                self._key(e, game)
        return None

    # ------------------------------------------------------------------ mouse
    def _mouse_down(self, e, game, ui, camera):
        pos = e.pos
        if e.button == 2:  # middle -> pan
            self.pan_active = True
            return
        if e.button == 1:  # left
            if ui.point_in_ui(pos):
                ui.handle_click(pos, game)
                return
            # clicking a building selects it (for the enable/disable panel)
            if game.tool in ("mine", "select"):
                q, r = camera.screen_to_hex(*pos)
                if game.world.get_tile(q, r).building is not None:
                    game.select_building_at(q, r)
                    return
                game.selected_building = None
            if game.tool == "select":
                self.pan_active = True
            elif game.tool == "mine":
                self.box_start = pos
            elif game.tool in ("road", "build"):
                q, r = camera.screen_to_hex(*pos)
                game.place(q, r)
                if game.tool == "road":
                    self.painting = True
                    self.paint_last = (q, r)
        elif e.button == 3:  # right -> cancel
            if ui.point_in_ui(pos):
                return
            q, r = camera.screen_to_hex(*pos)
            game.undesignate(q, r)
            self.box_start = None
            game.selection_rect = None

    def _mouse_up(self, e, game, ui, camera):
        if e.button == 2:
            self.pan_active = False
        elif e.button == 1:
            if game.tool == "select":
                self.pan_active = False
            if self.box_start is not None:
                x0, y0 = self.box_start
                x1, y1 = e.pos
                if abs(x1 - x0) < 5 and abs(y1 - y0) < 5:
                    if not ui.point_in_ui(e.pos):
                        q, r = camera.screen_to_hex(x1, y1)
                        game.box_designate([(q, r)])
                else:
                    self._box_designate(game, camera, (x0, y0), (x1, y1))
                self.box_start = None
                game.selection_rect = None
            self.painting = False
            self.paint_last = None

    def _mouse_move(self, e, game, ui, camera):
        pos = e.pos
        game.hover_hex = None if ui.point_in_ui(pos) else camera.screen_to_hex(*pos)
        if self.pan_active:
            camera.pan_screen(e.rel[0], e.rel[1])
        if self.box_start is not None:
            game.selection_rect = (self.box_start[0], self.box_start[1], pos[0], pos[1])
        if self.painting:
            q, r = camera.screen_to_hex(*pos)
            if (q, r) != self.paint_last:
                game.place(q, r)
                self.paint_last = (q, r)

    def _box_designate(self, game, camera, p0, p1):
        rect = pygame.Rect(min(p0[0], p1[0]), min(p0[1], p1[1]),
                           abs(p1[0] - p0[0]), abs(p1[1] - p0[1]))
        corners = [(rect.left, rect.top), (rect.right, rect.top),
                   (rect.left, rect.bottom), (rect.right, rect.bottom)]
        qs, rs = [], []
        for (sx, sy) in corners:
            q, r = camera.screen_to_hex(sx, sy)
            qs.append(q); rs.append(r)
        cells = []
        for r in range(min(rs) - 1, max(rs) + 2):
            for q in range(min(qs) - 1, max(qs) + 2):
                wx, wy = hexgrid.hex_to_pixel(q, r, config.HEX_SIZE)
                sx, sy = camera.world_to_screen(wx, wy)
                if rect.collidepoint(sx, sy):
                    cells.append((q, r))
        game.box_designate(cells)

    # ------------------------------------------------------------------ keyboard
    def _key(self, e, game):
        k = e.key
        if k == pygame.K_SPACE:
            game.paused = not game.paused
        elif k in (pygame.K_1, pygame.K_KP1):
            game.speed_index = 0; game.paused = False
        elif k in (pygame.K_2, pygame.K_KP2):
            game.speed_index = 1; game.paused = False
        elif k in (pygame.K_3, pygame.K_KP3):
            game.speed_index = 2; game.paused = False
        elif k == pygame.K_m:
            game.tool = "mine"
        elif k == pygame.K_r:
            game.tool = "road"
        elif k == pygame.K_b:
            game.tool = "build"
        elif k == pygame.K_ESCAPE:
            game.tool = "select"
        elif k == pygame.K_h:
            game.center_camera_home()
        elif k == pygame.K_F5:
            game.want_save = True
        elif k == pygame.K_F9:
            game.want_load = True
