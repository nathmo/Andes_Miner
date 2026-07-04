"""
ui.py — HUD: resource bar, speed/pause, tool + build + vehicle menus, tile info,
messages, help. Immediate-mode style: draw() rebuilds a button list each frame
and handle_click() hit-tests it. point_in_ui() lets input.py ignore world
clicks that land on a panel.
"""

import pygame
import config
import assets
from tiles import ROCK, RUBBLE, EXCAVATED


TOP_H = 40
BOT_H = 46
PANEL_W = 214


class UI:
    def __init__(self, screen_w, screen_h):
        self.sw, self.sh = screen_w, screen_h
        self.font = pygame.font.SysFont("consolas", 14)
        self.font_b = pygame.font.SysFont("consolas", 14, bold=True)
        self.font_s = pygame.font.SysFont("consolas", 11)
        self.buttons = []
        self._panels = []
        self._icons = {}        # (key, size) -> scaled Surface (or None if missing)

    def resize(self, w, h):
        self.sw, self.sh = w, h

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
        self.buttons = []
        self._panels = []
        mouse = pygame.mouse.get_pos()
        self._draw_topbar(surf, game, mouse)
        self._draw_panel(surf, game, mouse)
        self._draw_bottombar(surf, game, mouse)
        self._draw_building_panel(surf, game, mouse)
        self._draw_market_panel(surf, game, mouse)
        self._draw_load_menu(surf, game, mouse)
        self._draw_tileinfo(surf, game)
        self._draw_messages(surf, game)

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
        pw, ph = 430, 44 + 18 * len(TRADEABLE) + 56
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
        surf.blit(self.font_s.render(f"Emissions: {econ.emissions_total:.0f} kg  "
                                     f"(now {econ.emissions_rate:.1f}/s)", True, (210, 160, 140)),
                  (box.x + 14, y))
        self._sparkline(surf, econ.emissions_hist, pygame.Rect(box.x + 210, y - 1, 200, 15), (210, 150, 120))
        y += 18

    # ------------------------------------------------------------------ top bar
    def _draw_topbar(self, surf, game, mouse):
        bar = pygame.Rect(0, 0, self.sw, TOP_H)
        self._panels.append(bar)
        pygame.draw.rect(surf, config.COL_PANEL, bar)
        pygame.draw.line(surf, config.COL_PANEL_EDGE, (0, TOP_H), (self.sw, TOP_H))

        x = 12
        for res in config.RESOURCES:
            if game.economy.amount(res) <= 0:      # only show what you hold
                continue
            col = config.RESOURCE_COLOR[res]
            pygame.draw.circle(surf, col, (x + 6, TOP_H // 2), 6)
            txt = f"{config.RESOURCE_LABEL[res]}:{game.economy.amount(res)}"
            surf.blit(self.font.render(txt, True, config.COL_TEXT), (x + 16, 11))
            x += 16 + self.font.size(txt)[0] + 18

        # worker count (+ strike warning)
        wtxt = f"Workers:{game.num_workers} (foot {len(game.foot_workers)}/veh {game.active_vehicle_count})"
        surf.blit(self.font.render(wtxt, True, config.COL_ACCENT), (x, 11))
        ox = x + self.font.size(wtxt)[0] + 24
        if game.wages_due:
            surf.blit(self.font_b.render("ON STRIKE", True, (240, 110, 100)), (ox, 11))
            ox += self.font.size("ON STRIKE")[0] + 16
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
        # speed buttons
        labels = [("3x", 2), ("2x", 1), ("1x", 0)]
        for label, idx in labels:
            r = pygame.Rect(bx - 40, 6, 36, 28); bx -= 42
            self._button(surf, r, label, mouse, on=(not game.paused and game.speed_index == idx))
            self._add(r, "speed", idx)
        rp = pygame.Rect(bx - 74, 6, 70, 28); bx -= 78
        self._button(surf, rp, "Pause" if not game.paused else "Paused", mouse, on=game.paused)
        self._add(rp, "pause")

    # ------------------------------------------------------------------ side panel
    def _draw_panel(self, surf, game, mouse):
        panel = pygame.Rect(self.sw - PANEL_W, TOP_H, PANEL_W, self.sh - TOP_H - BOT_H)
        self._panels.append(panel)
        pygame.draw.rect(surf, config.COL_PANEL, panel)
        pygame.draw.line(surf, config.COL_PANEL_EDGE, (panel.x, panel.y), (panel.x, panel.bottom))

        x = panel.x + 10
        w = PANEL_W - 20
        y = TOP_H + 8
        econ = game.economy

        # --- MARKET: money, salary coffee, sell held resources -----------------
        surf.blit(self.font_b.render("MARKET", True, config.COL_TEXT), (x, y)); y += 20
        mcol = (240, 120, 110) if game.wages_due else config.COL_ACCENT
        jw = self._icon(surf, "jammies", x, y - 2, 18)
        surf.blit(self.font.render(f"{int(econ.jammies)}", True, config.COL_ACCENT), (x + jw + 3, y))
        cw = self._icon(surf, "iced_coffee", x + 112, y - 2, 18)
        surf.blit(self.font.render(f"{econ.coffee}", True, mcol), (x + 112 + cw + 2, y)); y += 20
        if econ.power_demand > 0 or econ.solar_supply > 0 or econ.battery_capacity > 0:
            ptxt = f"Power {econ.power_demand:.0f}  solar {econ.solar_supply:.0f}  grid {econ.grid_draw:.0f}"
            surf.blit(self.font_s.render(ptxt, True, (150, 200, 230)), (x, y)); y += 15
            if econ.battery_capacity > 0:
                btxt = f"Battery {econ.battery_charge:.0f}/{econ.battery_capacity:.0f}"
                surf.blit(self.font_s.render(btxt, True, (130, 205, 140)), (x, y)); y += 15
        if econ.brownout:
            surf.blit(self.font_s.render("MACHINES STOPPED (no power/cash)", True, (240, 130, 110)),
                      (x, y)); y += 15
        rC = pygame.Rect(x, y, w, 26)
        ccost = config.COFFEE_BATCH * config.COFFEE_PRICE
        self._button(surf, rC, f"Buy {config.COFFEE_BATCH} Iced Coffee", mouse,
                     enabled=econ.jammies >= ccost, sub=f"{ccost}j")
        self._add(rC, "buy_coffee"); y += 30
        for res in config.RESOURCES:
            if econ.amount(res) <= 0:
                continue
            r = pygame.Rect(x, y, w, 22)
            self._button(surf, r, f"Sell {config.RESOURCE_LABEL[res]}", mouse)
            gain = econ.sell_price(res) * config.SELL_BATCH
            surf.blit(self.font_s.render(f"+{gain}j", True, config.COL_TEXT_DIM),
                      (r.right - 42, r.y + 5))
            self._add(r, "sell", res)
            y += 24
        # buy materials you can't make yet (silicon, lithium)
        for res in config.BUYABLE:
            price = int(econ.buy_price(res) * config.BUY_BATCH)
            r = pygame.Rect(x, y, w, 22)
            self._button(surf, r, f"Buy {config.RESOURCE_LABEL[res]}", mouse,
                         enabled=econ.jammies >= price)
            surf.blit(self.font_s.render(f"-{price}j", True, config.COL_TEXT_DIM),
                      (r.right - 46, r.y + 5))
            self._add(r, "buy_material", res)
            y += 24
        y += 6

        # --- BUILD -------------------------------------------------------------
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
            self._add(r, "build_select", bt)
            y += 40

        # --- VEHICLES ----------------------------------------------------------
        y += 4
        surf.blit(self.font_b.render("VEHICLES", True, config.COL_TEXT), (x, y)); y += 22
        ws = game.has_workshop()
        for vt, info in config.VEHICLES.items():
            r = pygame.Rect(x, y, w, 30)
            aff = ws and game.economy.can_afford(info["cost"])
            self._button(surf, r, info["name"], mouse, enabled=aff, sub=self._cost_str(info["cost"]))
            self._add(r, "manufacture", vt)
            y += 32

        y += 4
        r = pygame.Rect(x, y, w, 28)
        aff = game.economy.can_afford(config.RECRUIT_COST)
        self._button(surf, r, "Recruit Worker", mouse, enabled=aff, sub=self._cost_str(config.RECRUIT_COST))
        self._add(r, "recruit")

    # ------------------------------------------------------------------ bottom bar
    def _draw_bottombar(self, surf, game, mouse):
        bar = pygame.Rect(0, self.sh - BOT_H, self.sw, BOT_H)
        self._panels.append(bar)
        pygame.draw.rect(surf, config.COL_PANEL, bar)
        pygame.draw.line(surf, config.COL_PANEL_EDGE, (0, bar.y), (self.sw, bar.y))

        x = 10
        for tool, label in [("mine", "Mine/Clean"), ("road", "Road"), ("build", "Build"), ("select", "Pan")]:
            r = pygame.Rect(x, bar.y + 8, 108, 30)
            self._button(surf, r, label, mouse, on=game.tool == tool)
            self._add(r, "tool", tool)
            x += 114

        # Home: recenter on HQ (so panning can't lose you).
        rh = pygame.Rect(x, bar.y + 8, 72, 30)
        self._button(surf, rh, "Home", mouse)
        self._add(rh, "home")
        x += 78
        rm = pygame.Rect(x, bar.y + 8, 84, 30)
        self._button(surf, rm, "Market", mouse, on=game.show_market)
        self._add(rm, "toggle_market")
        x += 90

        help_txt = "LMB: act/mark  RMB: cancel  drag: box-mark  wheel: zoom  Space: pause  H: home  F5/F9: save/load"
        surf.blit(self.font_s.render(help_txt, True, config.COL_TEXT_DIM), (x + 6, bar.y + 16))

    # ------------------------------------------------------------------ tile info
    def _draw_tileinfo(self, surf, game):
        if game.hover_hex is None:
            return
        q, r = game.hover_hex
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
        bw, bh = 250, (190 if is_wh else 96)
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
        return " ".join(f"{v}{k[:2].title()}" for k, v in cost.items())

    def point_in_ui(self, pos):
        return any(p.collidepoint(pos) for p in self._panels)

    def handle_click(self, pos, game):
        for b in self.buttons:
            if b["rect"].collidepoint(pos):
                self._do(b["action"], b["arg"], game)
                return True
        return self.point_in_ui(pos)

    def _do(self, action, arg, game):
        if action == "tool":
            game.tool = arg
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
        elif action == "toggle_building":
            game.toggle_selected_building()
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
