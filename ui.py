"""
ui.py — HUD: resource bar, speed/pause, tool + build + vehicle menus, tile info,
messages, help. Immediate-mode style: draw() rebuilds a button list each frame
and handle_click() hit-tests it. point_in_ui() lets input.py ignore world
clicks that land on a panel.
"""

import math

import pygame
import config
import assets
from tiles import ROCK, RUBBLE, EXCAVATED


TOP_H = 40
BOT_H = 46
PANEL_W = 214
TAB_H = 30               # height of the side-panel tab row

# The side panel is split into tabs so its button list can't overflow the screen.
PANEL_TABS = [("build", "Build"), ("fleet", "Fleet"), ("trade", "Trade")]


class UI:
    def __init__(self, screen_w, screen_h):
        self.real_w, self.real_h = screen_w, screen_h
        # The UI is drawn at a LOGICAL size = real / scale, then scaled to the
        # window, so the whole HUD grows/shrinks with the UI-scale setting while
        # the drawing code stays screen-relative. sw/sh are the logical size.
        self.scale = 1.0
        self.sw, self.sh = screen_w, screen_h
        self._surf = None       # logical-size surface used when scale != 1
        self.font = pygame.font.SysFont("consolas", 14)
        self.font_b = pygame.font.SysFont("consolas", 14, bold=True)
        self.font_s = pygame.font.SysFont("consolas", 11)
        self.font_alert = pygame.font.SysFont("consolas", 22, bold=True)  # big blinking warnings
        self.buttons = []
        self._panels = []
        self._icons = {}        # (key, size) -> scaled Surface (or None if missing)
        # Side-panel tabs + scroll: content is drawn under the tab row, clipped to
        # the panel, and scrollable so no button ever falls off-screen.
        self.panel_tab = "build"
        self.panel_scroll = 0.0
        self._side_panel_rect = None
        self._panel_content_rect = None
        self._panel_max_scroll = 0.0

    def resize(self, w, h):
        self.real_w, self.real_h = w, h
        self._relayout()

    def _relayout(self):
        """Recompute the logical HUD size from the window size and UI scale."""
        self.sw = max(640, int(self.real_w / self.scale))
        self.sh = max(400, int(self.real_h / self.scale))
        self._surf = None

    # ------------------------------------------------------------------ icons
    def _icon(self, surf, key, x, y, size=16):
        """Blit a HUD icon sprite scaled into a `size` box; returns its width."""
        ck = (key, size)
        if ck not in self._icons:
            sp = assets.get_sprite(key)
            if sp is not None:
                sc = size / float(max(sp.get_width(), sp.get_height()))
                sp = pygame.transform.smoothscale(
                    sp, (max(1, int(sp.get_width() * sc)), max(1, int(sp.get_height() * sc))))
            self._icons[ck] = sp
        ic = self._icons[ck]
        if ic is not None:
            surf.blit(ic, (x, y))
            return ic.get_width()
        return 0

    # ------------------------------------------------------------------ helpers
    def _button(self, surf, rect, label, mouse, on=False, enabled=True, sub=None):
        hover = rect.collidepoint(mouse) and enabled
        if on:
            col = config.COL_BUTTON_ON
        elif not enabled:
            col = config.COL_PANEL
        elif hover:
            col = config.COL_BUTTON_HOVER
        else:
            col = config.COL_BUTTON
        pygame.draw.rect(surf, col, rect, border_radius=4)
        pygame.draw.rect(surf, config.COL_PANEL_EDGE, rect, 1, border_radius=4)
        tc = config.COL_TEXT if enabled else config.COL_TEXT_DIM
        surf.blit(self.font.render(label, True, tc), (rect.x + 8, rect.y + 4))
        if sub:
            surf.blit(self.font_s.render(sub, True, config.COL_TEXT_DIM),
                      (rect.x + 8, rect.y + 22))
        return hover

    def _add(self, rect, action, arg=None):
        self.buttons.append({"rect": rect, "action": action, "arg": arg})

    # ------------------------------------------------------------------ draw
    def draw(self, surf, game):
        scale = getattr(game, "ui_scale", 1.0)
        if scale != self.scale:
            self.scale = scale
            self._relayout()

        self.buttons = []
        self._panels = []
        mx, my = pygame.mouse.get_pos()
        mouse = (mx / self.scale, my / self.scale)     # logical-space mouse

        if self.scale == 1.0:
            target = surf
        else:
            if self._surf is None:
                self._surf = pygame.Surface((self.sw, self.sh), pygame.SRCALPHA)
            self._surf.fill((0, 0, 0, 0))
            target = self._surf

        self._draw_topbar(target, game, mouse)
        self._draw_panel(target, game, mouse)
        self._draw_bottombar(target, game, mouse)
        self._draw_building_panel(target, game, mouse)
        self._draw_market_panel(target, game, mouse)
        self._draw_settings_menu(target, game, mouse)
        self._draw_load_menu(target, game, mouse)
        self._draw_tileinfo(target, game)
        self._draw_messages(target, game)
        self._draw_alerts(target, game)

        if self.scale != 1.0:
            surf.blit(pygame.transform.smoothscale(self._surf, (self.real_w, self.real_h)), (0, 0))

    # ------------------------------------------------------------------ load menu
    def _draw_load_menu(self, surf, game, mouse):
        if not game.show_load_menu:
            return
        import save as savemod
        rows = [("Latest save", config.SAVE_FILE, savemod.os.path.isfile(config.SAVE_FILE))]
        for (k, path, age) in savemod.list_backups():
            rows.append((f"Backup ~{age} min ago", path, True))
        pw, ph = 320, 56 + 26 * max(1, len(rows))
        box = pygame.Rect(self.sw // 2 - pw // 2, self.sh // 2 - ph // 2, pw, ph)
        self._panels.append(box)
        pygame.draw.rect(surf, config.COL_PANEL, box, border_radius=8)
        pygame.draw.rect(surf, config.COL_ACCENT, box, 1, border_radius=8)
        surf.blit(self.font_b.render("LOAD / ROLL BACK", True, config.COL_TEXT), (box.x + 14, box.y + 10))
        rc = pygame.Rect(box.right - 60, box.y + 8, 50, 22)
        self._button(surf, rc, "Close", mouse)
        self._add(rc, "close_load")
        y = box.y + 40
        for (label, path, exists) in rows:
            r = pygame.Rect(box.x + 12, y, pw - 24, 22)
            self._button(surf, r, label, mouse, enabled=exists)
            if exists:
                self._add(r, "load_slot", path)
            y += 26

    # ------------------------------------------------------------------ settings menu
    def _draw_settings_menu(self, surf, game, mouse):
        if not game.show_settings:
            return
        rows = [
            ("Clouds", "toggle_clouds", game.show_clouds),
            ("Condors (birds)", "toggle_birds", game.show_birds),
        ]
        pw, ph = 300, 52 + 30 * (len(rows) + 1) + 44   # +1 row for UI scale, save/quit
        box = pygame.Rect(self.sw // 2 - pw // 2, self.sh // 2 - ph // 2, pw, ph)
        self._panels.append(box)
        pygame.draw.rect(surf, config.COL_PANEL, box, border_radius=8)
        pygame.draw.rect(surf, config.COL_ACCENT, box, 1, border_radius=8)
        surf.blit(self.font_b.render("SETTINGS", True, config.COL_TEXT), (box.x + 14, box.y + 10))
        rc = pygame.Rect(box.right - 60, box.y + 8, 50, 22)
        self._button(surf, rc, "Close", mouse)
        self._add(rc, "close_settings")
        y = box.y + 42
        for (label, act, on) in rows:
            surf.blit(self.font.render(label, True, config.COL_TEXT), (box.x + 16, y + 3))
            rb = pygame.Rect(box.right - 84, y, 68, 24)
            self._button(surf, rb, "On" if on else "Off", mouse, on=on)
            self._add(rb, act)
            y += 30
        # UI scale: -  value  +
        surf.blit(self.font.render(f"UI scale: {game.ui_scale:.2f}x", True, config.COL_TEXT),
                  (box.x + 16, y + 3))
        for lbl, act, rx in [("-", "ui_scale_dn", box.right - 84), ("+", "ui_scale_up", box.right - 40)]:
            rb = pygame.Rect(rx, y, 30, 24)
            self._button(surf, rb, lbl, mouse)
            self._add(rb, act)
        y += 30
        # save / quit
        pygame.draw.line(surf, config.COL_PANEL_EDGE, (box.x + 12, y + 2), (box.right - 12, y + 2))
        y += 12
        rsave = pygame.Rect(box.x + 14, y, 128, 28)
        self._button(surf, rsave, "Save game", mouse)
        self._add(rsave, "save_game")
        rquit = pygame.Rect(box.right - 14 - 128, y, 128, 28)
        self._button(surf, rquit, "Save & Quit", mouse)
        self._add(rquit, "quit_game")

    # ------------------------------------------------------------------ market panel
    def _sparkline(self, surf, values, rect, col):
        if len(values) < 2:
            return
        lo, hi = min(values), max(values)
        rng = (hi - lo) or 1
        n = len(values)
        pts = [(rect.x + rect.w * i / (n - 1), rect.bottom - rect.h * (v - lo) / rng)
               for i, v in enumerate(values)]
        pygame.draw.lines(surf, col, False, pts, 1)

    def _draw_market_panel(self, surf, game, mouse):
        if not game.show_market:
            return
        from economy import TRADEABLE
        econ = game.economy
        pw, ph = 430, 44 + 18 * len(TRADEABLE) + 124
        box = pygame.Rect(self.sw // 2 - pw // 2, self.sh // 2 - ph // 2, pw, ph)
        self._panels.append(box)
        pygame.draw.rect(surf, config.COL_PANEL, box, border_radius=8)
        pygame.draw.rect(surf, config.COL_ACCENT, box, 1, border_radius=8)
        surf.blit(self.font_b.render("STOCK MARKET  (price + trend)", True, config.COL_TEXT),
                  (box.x + 14, box.y + 10))
        rc = pygame.Rect(box.right - 60, box.y + 8, 50, 22)
        self._button(surf, rc, "Close", mouse)
        self._add(rc, "close_market")
        y = box.y + 38
        for res in TRADEABLE:
            col = config.RESOURCE_COLOR.get(res, config.COL_TEXT)
            pygame.draw.circle(surf, col, (box.x + 22, y + 7), 5)
            surf.blit(self.font_s.render(config.RESOURCE_LABEL.get(res, res), True, config.COL_TEXT),
                      (box.x + 34, y))
            surf.blit(self.font_s.render(f"{econ.sell_price(res)}j", True, config.COL_ACCENT),
                      (box.x + 150, y))
            self._sparkline(surf, econ.price_hist.get(res, []),
                            pygame.Rect(box.x + 210, y - 1, 200, 15), col)
            y += 18
        # --- electricity price trend ------------------------------------------
        ecol = (150, 200, 230)
        pygame.draw.circle(surf, ecol, (box.x + 22, y + 7), 5)
        surf.blit(self.font_s.render("Electricity", True, config.COL_TEXT), (box.x + 34, y))
        surf.blit(self.font_s.render(f"{econ.elec_price():.3f}j/kWh", True, config.COL_ACCENT),
                  (box.x + 128, y))
        self._sparkline(surf, econ.elec_hist, pygame.Rect(box.x + 210, y - 1, 200, 15), ecol)
        y += 18
        # --- grid carbon intensity + emissions over time (item 27) ------------
        y += 6
        pygame.draw.line(surf, config.COL_PANEL_EDGE, (box.x + 12, y), (box.right - 12, y))
        y += 8
        frac = (econ.grid_carbon - config.CARBON_MIN) / max(1.0, config.GRID_CARBON_START - config.CARBON_MIN)
        frac = max(0.0, min(1.0, frac))
        ccol = (int(90 + 150 * frac), int(200 - 120 * frac), 90)
        surf.blit(self.font_s.render(f"Grid carbon: {econ.grid_carbon:.0f} kg/MWh", True, ccol),
                  (box.x + 14, y))
        bar = pygame.Rect(box.x + 210, y + 2, 200, 9)
        pygame.draw.rect(surf, (40, 44, 52), bar)
        pygame.draw.rect(surf, ccol, (bar.x, bar.y, int(bar.w * frac), bar.h))
        y += 18
        etot = (f"{econ.emissions_total / 1000:.2f} t" if econ.emissions_total >= 1000
                else f"{econ.emissions_total:.0f} kg")
        surf.blit(self.font_s.render(f"Emissions: {etot}  "
                                     f"(now {econ.emissions_rate:.2f} kg/s)", True, (210, 160, 140)),
                  (box.x + 14, y))
        self._sparkline(surf, econ.emissions_hist, pygame.Rect(box.x + 210, y - 1, 200, 15), (210, 150, 120))
        y += 18
        # --- power: solar production + consumption trend (kW) -----------------
        y += 6
        pygame.draw.line(surf, config.COL_PANEL_EDGE, (box.x + 12, y), (box.right - 12, y))
        y += 8
        # solar arrays' output right now, with its trend
        scol = (245, 205, 90)
        pygame.draw.circle(surf, scol, (box.x + 22, y + 7), 5)
        surf.blit(self.font_s.render("Solar output", True, config.COL_TEXT), (box.x + 34, y))
        surf.blit(self.font_s.render(f"{econ.solar_supply:.1f} kW", True, config.COL_ACCENT),
                  (box.x + 140, y))
        self._sparkline(surf, econ.solar_hist, pygame.Rect(box.x + 210, y - 1, 200, 15), scol)
        y += 18
        # total consumption of every running machine, trended over time
        dcol = (150, 200, 230)
        pygame.draw.circle(surf, dcol, (box.x + 22, y + 7), 5)
        surf.blit(self.font_s.render("Consumption", True, config.COL_TEXT), (box.x + 34, y))
        surf.blit(self.font_s.render(f"{econ.power_demand:.1f} kW", True, config.COL_ACCENT),
                  (box.x + 140, y))
        self._sparkline(surf, econ.demand_hist, pygame.Rect(box.x + 210, y - 1, 200, 15), dcol)
        y += 18

    # ------------------------------------------------------------------ top bar
    def _draw_topbar(self, surf, game, mouse):
        bar = pygame.Rect(0, 0, self.sw, TOP_H)
        self._panels.append(bar)
        pygame.draw.rect(surf, config.COL_PANEL, bar)
        pygame.draw.line(surf, config.COL_PANEL_EDGE, (0, TOP_H), (self.sw, TOP_H))

        x = 12
        # money + coffee: always visible, independent of the active side-panel tab
        econ = game.economy
        jw = self._icon(surf, "jammies", x, TOP_H // 2 - 9, 18)
        jtxt = f"{int(econ.jammies)}"
        surf.blit(self.font.render(jtxt, True, config.COL_ACCENT), (x + jw + 2, 11))
        x += jw + 2 + self.font.size(jtxt)[0] + 14
        cw = self._icon(surf, "iced_coffee", x, TOP_H // 2 - 9, 18)
        ctxt = f"{econ.coffee}"
        ccol = (240, 120, 110) if game.wages_due else config.COL_TEXT
        surf.blit(self.font.render(ctxt, True, ccol), (x + cw + 2, 11))
        x += cw + 2 + self.font.size(ctxt)[0] + 18

        for res in config.RESOURCES:
            if game.economy.amount(res) <= 0:      # only show what you hold
                continue
            col = config.RESOURCE_COLOR[res]
            pygame.draw.circle(surf, col, (x + 6, TOP_H // 2), 6)
            txt = f"{config.RESOURCE_LABEL[res]}:{game.economy.amount(res)}"
            surf.blit(self.font.render(txt, True, config.COL_TEXT), (x + 16, 11))
            x += 16 + self.font.size(txt)[0] + 18

        # worker count (strike/shortage/blackout are shown as big banners below)
        wtxt = f"Workers:{game.num_workers} (foot {len(game.foot_workers)}/veh {game.active_vehicle_count})"
        surf.blit(self.font.render(wtxt, True, config.COL_ACCENT), (x, 11))
        ox = x + self.font.size(wtxt)[0] + 24
        # overarching goal: villages linked by road
        vn = len(game.world.villages)
        vtxt = f"Villages linked: {game.villages_connected}/{vn}"
        vcol = (240, 200, 90) if game.villages_connected >= vn else (140, 210, 150)
        surf.blit(self.font.render(vtxt, True, vcol), (ox, 11))
        # sun/moon indicator (bright yellow by day, dim blue by night)
        ox += self.font.size(vtxt)[0] + 18
        s = game.sun
        scol = (int(150 + 105 * s), int(160 + 55 * s), int(205 - 90 * s))
        pygame.draw.circle(surf, scol, (ox + 9, TOP_H // 2), 8)
        pygame.draw.circle(surf, (20, 24, 34), (ox + 9, TOP_H // 2), 8, 1)

        # speed / pause on the right
        bx = self.sw - 4
        # speed buttons (labels derived from config.SPEED_STEPS; fastest on the right)
        for idx in range(len(config.SPEED_STEPS) - 1, -1, -1):
            label = f"{config.SPEED_STEPS[idx]:g}x"
            r = pygame.Rect(bx - 40, 6, 36, 28); bx -= 42
            self._button(surf, r, label, mouse, on=(not game.paused and game.speed_index == idx))
            self._add(r, "speed", idx)
        rp = pygame.Rect(bx - 74, 6, 70, 28); bx -= 78
        self._button(surf, rp, "Pause" if not game.paused else "Paused", mouse, on=game.paused)
        self._add(rp, "pause")

        # clock + calendar, just left of the speed controls (starts at today's date)
        dt = game.game_datetime()
        clk = dt.strftime("%H:%M")
        cal = dt.strftime("%a %d %b")
        calw = self.font_s.size(cal)[0]
        clkw = self.font.size(clk)[0]
        cx = bx - 10 - max(clkw, calw)
        surf.blit(self.font.render(clk, True, config.COL_ACCENT), (cx, 3))
        surf.blit(self.font_s.render(cal, True, config.COL_TEXT_DIM), (cx, 24))

    # ------------------------------------------------------------------ alerts
    def _draw_alerts(self, surf, game):
        """Banners stacked under the top bar, centred over the map. Critical
        conditions blink red (act now); softer guidance shows in calm amber. Each
        spells out the fix."""
        alerts = []      # (text, is_critical)
        if game.wages_due:
            alerts.append(("ON STRIKE  -  buy iced coffee to pay your workers!", True))
        if game.rubble_short:
            alerts.append(("RUBBLE SHORTAGE  -  roads cannot be built without rubble!", True))
        if game.power_blackout:
            alerts.append(("BLACKOUT  -  no cash for grid power; machines are stalled!", True))
        if game.mine_stuck:
            alerts.append(("NOTHING IN REACH TO MINE  -  build a Road to dig deeper!", False))
        if not alerts:
            return
        # Blink: a smooth pulse in [0.35, 1.0] (never fully off, so always readable).
        pulse = 0.35 + 0.65 * abs(math.sin(pygame.time.get_ticks() * 0.006))
        cx = (self.sw - PANEL_W) // 2                    # centre of the play area
        y = TOP_H + 10
        for text, critical in alerts:
            tw, th = self.font_alert.size(text)
            box = pygame.Rect(0, 0, tw + 30, th + 14)
            box.centerx, box.y = cx, y
            bg = pygame.Surface(box.size, pygame.SRCALPHA)
            if critical:
                bg.fill((120, 12, 12, int(70 + 150 * pulse)))        # pulsing red backdrop
                edge = (255, int(50 + 90 * pulse), int(50 + 90 * pulse))
            else:
                bg.fill((120, 82, 12, int(60 + 120 * pulse)))        # calm amber backdrop
                edge = (240, int(170 + 60 * pulse), int(70 + 60 * pulse))
            surf.blit(bg, box.topleft)
            pygame.draw.rect(surf, edge, box, 2, border_radius=6)
            txt = self.font_alert.render(text, True, (255, 255, 255))
            txt.set_alpha(int(150 + 105 * pulse))
            surf.blit(txt, (box.centerx - tw // 2, box.y + 7))
            y += box.height + 8

    # ------------------------------------------------------------------ side panel
    def _draw_panel(self, surf, game, mouse):
        panel = pygame.Rect(self.sw - PANEL_W, TOP_H, PANEL_W, self.sh - TOP_H - BOT_H)
        self._side_panel_rect = panel
        self._panels.append(panel)
        pygame.draw.rect(surf, config.COL_PANEL, panel)
        pygame.draw.line(surf, config.COL_PANEL_EDGE, (panel.x, panel.y), (panel.x, panel.bottom))

        # --- tab row: Build / Fleet / Trade -----------------------------------
        tw = PANEL_W // len(PANEL_TABS)
        for i, (key, label) in enumerate(PANEL_TABS):
            r = pygame.Rect(panel.x + i * tw, panel.y + 4, tw - 2, TAB_H - 8)
            self._button(surf, r, label, mouse, on=self.panel_tab == key)
            self._add(r, "panel_tab", key)

        # --- content area: clipped + scrollable so buttons never overflow ------
        content = pygame.Rect(panel.x, panel.y + TAB_H, PANEL_W, panel.bottom - (panel.y + TAB_H))
        self._panel_content_rect = content
        x = panel.x + 10
        w = PANEL_W - 20
        top = content.y + 8
        y = top - int(self.panel_scroll)

        prev_clip = surf.get_clip()
        surf.set_clip(content)
        if self.panel_tab == "build":
            y = self._draw_build_tab(surf, game, mouse, x, w, y, content)
        elif self.panel_tab == "fleet":
            y = self._draw_fleet_tab(surf, game, mouse, x, w, y, content)
        else:
            y = self._draw_trade_tab(surf, game, mouse, x, w, y, content)
        surf.set_clip(prev_clip)

        # clamp scroll to the measured content height (measured this frame)
        content_h = (y + int(self.panel_scroll)) - top
        self._panel_max_scroll = max(0.0, content_h - (content.h - 12))
        self.panel_scroll = max(0.0, min(self._panel_max_scroll, self.panel_scroll))

        # scrollbar hint when there's more below/above
        if self._panel_max_scroll > 0:
            track_h = content.h - 12
            bar_h = max(24, int(track_h * track_h / (track_h + self._panel_max_scroll)))
            bar_y = top + int((track_h - bar_h) * (self.panel_scroll / self._panel_max_scroll))
            pygame.draw.rect(surf, config.COL_PANEL_EDGE,
                             (content.right - 5, bar_y, 3, bar_h), border_radius=2)

    def _add_in(self, rect, clip, action, arg=None):
        """Register a button only if it's fully inside the clip region, so a
        scrolled-away button can't be clicked through the top/bottom bars."""
        if rect.top >= clip.top and rect.bottom <= clip.bottom:
            self._add(rect, action, arg)

    # ------------------------------------------------------------------ build tab
    def _draw_build_tab(self, surf, game, mouse, x, w, y, clip):
        surf.blit(self.font_b.render("BUILD", True, config.COL_TEXT), (x, y)); y += 22
        for bt, info in config.BUILDINGS.items():
            if not info.get("buildable", True):      # e.g. the pre-placed depot
                continue
            r = pygame.Rect(x, y, w, 38)
            on = game.tool == "build" and game.build_choice == bt
            aff = game.economy.can_afford(info["cost"])
            self._button(surf, r, info["name"], mouse, on=on, sub=self._cost_str(info["cost"]))
            if not aff:
                surf.blit(self.font_s.render("!", True, (230, 120, 120)), (r.right - 12, r.y + 4))
            self._add_in(r, clip, "build_select", bt)
            y += 40
        return y

    # ------------------------------------------------------------------ fleet tab
    def _draw_fleet_tab(self, surf, game, mouse, x, w, y, clip):
        surf.blit(self.font_b.render("VEHICLES", True, config.COL_TEXT), (x, y)); y += 22
        ws = game.has_workshop()
        if not ws:
            surf.blit(self.font_s.render("Build a Vehicle Workshop first.", True, config.COL_TEXT_DIM),
                      (x, y)); y += 18
        for vt, info in config.VEHICLES.items():
            r = pygame.Rect(x, y, w, 30)
            aff = ws and game.economy.can_afford(info["cost"])
            self._button(surf, r, info["name"], mouse, enabled=aff, sub=self._cost_str(info["cost"]))
            self._add_in(r, clip, "manufacture", vt)
            y += 32
        y += 8
        r = pygame.Rect(x, y, w, 28)
        aff = game.economy.can_afford(config.RECRUIT_COST)
        self._button(surf, r, "Recruit Worker", mouse, enabled=aff, sub=self._cost_str(config.RECRUIT_COST))
        self._add_in(r, clip, "recruit")
        y += 32
        return y

    # ------------------------------------------------------------------ trade tab
    def _draw_trade_tab(self, surf, game, mouse, x, w, y, clip):
        # Fully-populated, STATIC layout: every sell/buy button is always present
        # (greyed when unavailable) so nothing shifts as you trade. Prices sit to
        # the right of each button; the blue energy status goes below the buttons.
        econ = game.economy
        bw = w - 46                    # button width; the +/-price sits to its right
        surf.blit(self.font_b.render("TRADE", True, config.COL_TEXT), (x, y)); y += 22

        rC = pygame.Rect(x, y, w, 26)
        ccost = config.COFFEE_BATCH * config.COFFEE_PRICE
        self._button(surf, rC, f"Buy {config.COFFEE_BATCH} Iced Coffee", mouse,
                     enabled=econ.jammies >= ccost, sub=f"{ccost}j")
        self._add_in(rC, clip, "buy_coffee"); y += 30
        rM = pygame.Rect(x, y, w, 22)
        self._button(surf, rM, "Prices & Trends...", mouse, on=game.show_market)
        self._add_in(rM, clip, "toggle_market"); y += 28

        # SELL — every sellable resource, greyed when you hold none
        surf.blit(self.font_s.render("SELL", True, config.COL_TEXT_DIM), (x, y)); y += 15
        for res in config.RESOURCES:
            if res not in config.SELL_PRICES:
                continue
            r = pygame.Rect(x, y, bw, 22)
            self._button(surf, r, f"Sell {config.RESOURCE_LABEL[res]}", mouse,
                         enabled=econ.amount(res) > 0)
            gain = econ.sell_price(res) * config.SELL_BATCH
            surf.blit(self.font_s.render(f"+{gain}j", True, config.COL_TEXT_DIM),
                      (r.right + 6, r.y + 5))
            self._add_in(r, clip, "sell", res)
            y += 24

        # BUY — every buyable material, greyed when you can't afford it
        y += 4
        surf.blit(self.font_s.render("BUY", True, config.COL_TEXT_DIM), (x, y)); y += 15
        for res in config.BUYABLE:
            price = int(econ.buy_price(res) * config.BUY_BATCH)
            r = pygame.Rect(x, y, bw, 22)
            self._button(surf, r, f"Buy {config.RESOURCE_LABEL[res]}", mouse,
                         enabled=econ.jammies >= price)
            surf.blit(self.font_s.render(f"-{price}j", True, config.COL_TEXT_DIM),
                      (r.right + 6, r.y + 5))
            self._add_in(r, clip, "buy_material", res)
            y += 24

        # energy status — the blue text, now AFTER the buttons so it never shifts them
        y += 6
        pygame.draw.line(surf, config.COL_PANEL_EDGE, (x, y), (x + w, y)); y += 6
        ptxt = f"Load {econ.power_demand:.0f}  solar {econ.solar_supply:.0f}  grid {econ.grid_draw:.0f} kW"
        surf.blit(self.font_s.render(ptxt, True, (150, 200, 230)), (x, y)); y += 15
        bcol = (130, 205, 140) if econ.battery_capacity > 0 else config.COL_TEXT_DIM
        surf.blit(self.font_s.render(f"Battery {econ.battery_charge:.0f}/{econ.battery_capacity:.0f}",
                                     True, bcol), (x, y)); y += 15
        if econ.brownout:
            surf.blit(self.font_s.render("BLACKOUT - no cash for power", True, (240, 130, 110)),
                      (x, y)); y += 15
        return y

    # ------------------------------------------------------------------ bottom bar
    def _draw_bottombar(self, surf, game, mouse):
        bar = pygame.Rect(0, self.sh - BOT_H, self.sw, BOT_H)
        self._panels.append(bar)
        pygame.draw.rect(surf, config.COL_PANEL, bar)
        pygame.draw.line(surf, config.COL_PANEL_EDGE, (0, bar.y), (self.sw, bar.y))

        x = 10
        # The three action tools the player orders, then Pan. (Building is placed
        # from the Build tab in the side panel, so no Build button here.)
        for tool, label in [("excavate", "Excavate"), ("clean", "Clean"),
                            ("road", "Road"), ("select", "Pan")]:
            r = pygame.Rect(x, bar.y + 8, 88, 30)
            self._button(surf, r, label, mouse, on=game.tool == tool)
            self._add(r, "tool", tool)
            x += 92

        # Home: recenter on HQ (so panning can't lose you).
        rh = pygame.Rect(x, bar.y + 8, 64, 30)
        self._button(surf, rh, "Home", mouse)
        self._add(rh, "home")
        x += 70
        rm = pygame.Rect(x, bar.y + 8, 76, 30)
        self._button(surf, rm, "Market", mouse, on=game.show_market)
        self._add(rm, "toggle_market")
        x += 82
        rs = pygame.Rect(x, bar.y + 8, 80, 30)
        self._button(surf, rs, "Settings", mouse, on=game.show_settings)
        self._add(rs, "toggle_settings")
        x += 86

        help_txt = "LMB: mark  RMB: cancel  drag: box  wheel: zoom  M/C/R: tools  Space: pause  F5/F9: save/load"
        surf.blit(self.font_s.render(help_txt, True, config.COL_TEXT_DIM), (x + 6, bar.y + 16))

    # ------------------------------------------------------------------ tile info
    def _draw_tileinfo(self, surf, game):
        if game.hover_hex is None:
            return
        q, r = game.hover_hex
        if game.world.is_sky(q, r):          # above the summit ridge — open sky
            lines = [(f"Open sky  ({q},{r})", config.COL_TEXT),
                     ("Above the summit — nothing to mine here", config.COL_TEXT_DIM)]
            box = pygame.Rect(8, self.sh - BOT_H - 12 - 18 * len(lines) - 8, 250, 18 * len(lines) + 8)
            s = pygame.Surface(box.size, pygame.SRCALPHA); s.fill((*config.COL_PANEL, 230))
            surf.blit(s, box.topleft)
            pygame.draw.rect(surf, config.COL_PANEL_EDGE, box, 1)
            for i, (ln, col) in enumerate(lines):
                surf.blit(self.font_s.render(ln, True, col), (box.x + 8, box.y + 5 + i * 18))
            return
        t = game.world.get_tile(q, r)
        # A descriptive name from state + rock: "Rhyolite", "Diorite rubble",
        # "Excavated basalt", "Road". Only solid rock still holds ore to mine.
        rock = t.name
        if t.state == ROCK:
            title = rock
        elif t.state == RUBBLE:
            title = f"{rock} rubble"
        elif t.state == EXCAVATED:
            title = f"Excavated {rock.lower()}"
        else:
            title = "Road"
        lines = [(f"{title}  ({q},{r})", config.COL_TEXT)]
        if t.state == ROCK:
            lines.append((f"Hardness: {t.hardness_label}  ({t.mine_time:.1f}s)", config.COL_TEXT_DIM))
            if t.ore_type:
                oc = config.RESOURCE_COLOR.get(t.ore_type, config.COL_TEXT)
                label = config.RESOURCE_LABEL.get(t.ore_type, t.ore_type)
                lines.append((f"Drops {t.ore_amount} {label} when mined", oc))
            reach = game.max_mine_reach()
            in_range = game.world.mineable(t, reach)
            lines.append(("In mining range" if in_range else f"Needs road within {reach} tiles",
                          (120, 210, 130) if in_range else (220, 150, 90)))
        for res, amt in t.drops.items():
            oc = config.RESOURCE_COLOR.get(res, config.COL_TEXT)
            lines.append((f"On ground: {amt} {config.RESOURCE_LABEL.get(res, res)}", oc))
        if t.building:
            b = t.building
            if not b.built:
                st = f"building {int(b.progress*100)}%"
            elif b.obsolete:
                st = "obsolete"
            elif not b.enabled:
                st = "disabled"
            elif (blk := game.economy.reserve_block(b)) is not None:
                st = f"paused: low {config.RESOURCE_LABEL.get(blk[0], blk[0])}"
            else:
                st = "active"
            lines.append((f"{b.name} [{st}]", config.COL_ACCENT))
        w = 250
        box = pygame.Rect(8, self.sh - BOT_H - 12 - 18 * len(lines) - 8, w, 18 * len(lines) + 8)
        s = pygame.Surface(box.size, pygame.SRCALPHA)
        s.fill((*config.COL_PANEL, 230))
        surf.blit(s, box.topleft)
        pygame.draw.rect(surf, config.COL_PANEL_EDGE, box, 1)
        for i, (ln, col) in enumerate(lines):
            surf.blit(self.font_s.render(ln, True, col), (box.x + 8, box.y + 5 + i * 18))

    # ------------------------------------------------------------------ building panel
    def _draw_building_panel(self, surf, game, mouse):
        b = game.selected_building
        if b is None:
            return
        is_wh = b.built and b.btype == "warehouse"
        cost = config.BUILDINGS[b.btype].get("cost", {})
        can_demolish = config.BUILDINGS[b.btype].get("buildable", True)
        bw, bh = 250, (190 if is_wh else 96) + (28 if can_demolish else 0)
        box = pygame.Rect(self.sw // 2 - bw // 2, self.sh - BOT_H - bh - 12, bw, bh)
        self._panels.append(box)
        pygame.draw.rect(surf, config.COL_PANEL_LIGHT, box, border_radius=6)
        pygame.draw.rect(surf, config.COL_ACCENT, box, 1, border_radius=6)
        surf.blit(self.font_b.render(b.name, True, config.COL_TEXT), (box.x + 10, box.y + 8))

        if not b.built:
            st, sc = f"Under construction {int(b.progress*100)}%", config.COL_TEXT_DIM
        elif b.obsolete:
            st, sc = "Obsolete — superseded by a better building", (220, 150, 90)
        elif not b.enabled:
            st, sc = "Disabled (not processing)", (220, 150, 90)
        elif (blk := game.economy.reserve_block(b)) is not None:
            res, reserve = blk
            st, sc = (f"Paused — low {config.RESOURCE_LABEL.get(res, res)} (reserve {reserve})",
                      (230, 200, 120))
        else:
            st, sc = "Active", (120, 210, 130)
        surf.blit(self.font_s.render(st, True, sc), (box.x + 10, box.y + 30))
        note = config.BUILDINGS[b.btype].get("note", "")
        surf.blit(self.font_s.render(note[:40], True, config.COL_TEXT_DIM), (box.x + 10, box.y + 46))

        if is_wh:                                # auto-trade threshold controls
            wy = box.y + 66
            surf.blit(self.font_s.render(f"Auto-sell if cash < {game.auto_cash_min}", True, config.COL_TEXT),
                      (box.x + 10, wy + 3))
            for lbl, act, rx in [("-", "wh_cash_dn", box.right - 60), ("+", "wh_cash_up", box.right - 34)]:
                rb = pygame.Rect(rx, wy, 22, 20); self._button(surf, rb, lbl, mouse); self._add(rb, act)
            wy += 26
            surf.blit(self.font_s.render(f"Keep coffee > {game.auto_coffee_min}", True, config.COL_TEXT),
                      (box.x + 10, wy + 3))
            for lbl, act, rx in [("-", "wh_cof_dn", box.right - 60), ("+", "wh_cof_up", box.right - 34)]:
                rb = pygame.Rect(rx, wy, 22, 20); self._button(surf, rb, lbl, mouse); self._add(rb, act)
            wy += 26
            rm = pygame.Rect(box.x + 10, wy, 230, 20)
            self._button(surf, rm, f"Sell mode: {'Best value' if game.auto_smart_sell else 'Fixed order'}",
                         mouse, on=game.auto_smart_sell)
            self._add(rm, "wh_smart")

        # Demolish (red, dangerous): removes the building and refunds its build cost.
        if can_demolish:
            rDem = pygame.Rect(box.x + 10, box.bottom - 60, bw - 20, 24)
            hov = rDem.collidepoint(mouse)
            pygame.draw.rect(surf, (150, 62, 56) if hov else (120, 48, 44), rDem, border_radius=4)
            pygame.draw.rect(surf, (205, 95, 84), rDem, 1, border_radius=4)
            lbl = f"Demolish  (+{self._cost_str(cost)})" if cost else "Demolish"
            surf.blit(self.font.render(lbl, True, (245, 224, 220)), (rDem.x + 8, rDem.y + 4))
            self._add(rDem, "demolish_building")

        if b.built:
            rT = pygame.Rect(box.x + 10, box.bottom - 30, 150, 24)
            self._button(surf, rT, "Disable" if b.enabled else "Enable", mouse, on=not b.enabled)
            self._add(rT, "toggle_building")
        rClose = pygame.Rect(box.right - 66, box.bottom - 30, 56, 24)
        self._button(surf, rClose, "Close", mouse)
        self._add(rClose, "close_building")

    # ------------------------------------------------------------------ messages
    def _draw_messages(self, surf, game):
        y = self.sh - BOT_H - 16
        for m in reversed(game.messages):
            alpha = max(0, min(255, int(m["life"] / 4.0 * 255)))
            txt = self.font.render(m["text"], True, config.COL_ACCENT)
            txt.set_alpha(alpha)
            surf.blit(txt, (self.sw - PANEL_W - 10 - txt.get_width(), y))
            y -= 20

    # ------------------------------------------------------------------ interaction
    def _cost_str(self, cost):
        return " ".join(f"{v}{config.RESOURCE_ABBR.get(k, k[:2].title())}" for k, v in cost.items())

    def _logical(self, pos):
        """Map a real window position into logical (UI-space) coordinates."""
        return (pos[0] / self.scale, pos[1] / self.scale)

    def point_in_ui(self, pos):
        lp = self._logical(pos)
        return any(p.collidepoint(lp) for p in self._panels)

    def point_in_panel(self, pos):
        """True over the scrollable side panel (so the wheel scrolls, not zooms)."""
        return (self._side_panel_rect is not None
                and self._side_panel_rect.collidepoint(self._logical(pos)))

    def scroll_panel(self, dy):
        self.panel_scroll = max(0.0, min(self._panel_max_scroll, self.panel_scroll + dy))

    def handle_click(self, pos, game):
        lp = self._logical(pos)
        for b in self.buttons:
            if b["rect"].collidepoint(lp):
                self._do(b["action"], b["arg"], game)
                return True
        return self.point_in_ui(pos)

    def _do(self, action, arg, game):
        if action == "tool":
            game.tool = arg
            if arg == "build":            # jump straight to the building menu
                self.panel_tab = "build"
                self.panel_scroll = 0.0
        elif action == "panel_tab":
            self.panel_tab = arg
            self.panel_scroll = 0.0
        elif action == "speed":
            game.speed_index = arg
            game.paused = False
        elif action == "pause":
            game.paused = not game.paused
        elif action == "build_select":
            game.tool = "build"
            game.build_choice = arg
        elif action == "manufacture":
            game.manufacture(arg)
        elif action == "recruit":
            game.recruit_worker()
        elif action == "home":
            game.center_camera_home()
        elif action == "sell":
            game.sell(arg)
        elif action == "buy_coffee":
            game.buy_coffee()
        elif action == "buy_material":
            game.buy_material(arg)
        elif action == "toggle_market":
            game.show_market = not game.show_market
        elif action == "close_market":
            game.show_market = False
        elif action == "toggle_settings":
            game.show_settings = not game.show_settings
        elif action == "close_settings":
            game.show_settings = False
        elif action == "toggle_clouds":
            game.show_clouds = not game.show_clouds
        elif action == "toggle_birds":
            game.show_birds = not game.show_birds
        elif action == "ui_scale_up":
            game.ui_scale = round(min(2.0, game.ui_scale + 0.1), 2)
        elif action == "ui_scale_dn":
            game.ui_scale = round(max(0.7, game.ui_scale - 0.1), 2)
        elif action == "save_game":
            game.want_save = True
        elif action == "quit_game":
            game.want_save = True         # save before exiting so no progress is lost
            game.want_quit = True
        elif action == "toggle_building":
            game.toggle_selected_building()
        elif action == "demolish_building":
            game.demolish_selected_building()
        elif action == "close_building":
            game.selected_building = None
        elif action == "wh_cash_dn":
            game.auto_cash_min = max(0, game.auto_cash_min - 10)
        elif action == "wh_cash_up":
            game.auto_cash_min += 10
        elif action == "wh_cof_dn":
            game.auto_coffee_min = max(0, game.auto_coffee_min - 1)
        elif action == "wh_cof_up":
            game.auto_coffee_min += 1
        elif action == "wh_smart":
            game.auto_smart_sell = not game.auto_smart_sell
        elif action == "load_slot":
            game.want_load_path = arg
            game.show_load_menu = False
        elif action == "close_load":
            game.show_load_menu = False
