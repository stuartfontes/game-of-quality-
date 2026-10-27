import random

import pygame

from src.core import settings
from src.core.screen import Screen
from src.core.ui import MessageBox, draw_lives, draw_score, draw_text_centered


class Ring:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.state = "pending"


class FlightScreen(Screen):
    def __init__(self, manager):
        super().__init__(manager)
        self.font = manager.assets.font(settings.FONT_FILE, settings.FONT_SIZE_SMALL)
        self.box = MessageBox((16, 96, 352, 108), self.font)
        self.box_lock = 0.0
        self.box_action = None
        self.rings = []
        self.x = 0.0
        self.y = 0.0
        self.vel_y = 0.0
        self.flap_time = 0.0
        self.invuln = 0.0
        self.elapsed = 0.0
        self.end_x = 0.0

    def on_enter(self):
        self.build_rings()
        self.place(0.0, settings.FLIGHT_START_Y)
        self.invuln = 0.0
        self.elapsed = 0.0
        self.box_action = None
        self.box.hide()

    def build_rings(self):
        self.rings = []
        y = settings.FLIGHT_START_Y
        for i in range(settings.FLIGHT_RINGS):
            y += random.randint(-settings.FLIGHT_RING_STEP, settings.FLIGHT_RING_STEP)
            y = max(settings.FLIGHT_RING_MIN_Y, min(settings.FLIGHT_RING_MAX_Y, y))
            x = settings.FLIGHT_FIRST_RING_X + i * settings.FLIGHT_RING_SPACING
            self.rings.append(Ring(x, y))
        self.end_x = self.rings[-1].x + settings.FLIGHT_RING_SPACING

    def place(self, x, y):
        self.x = x
        self.y = y
        self.vel_y = 0.0
        self.flap_time = 0.0

    def respawn(self):
        passed = [ring for ring in self.rings if ring.state == "passed"]
        if passed:
            last = passed[-1]
            self.place(last.x + 24, last.y)
        else:
            self.place(0.0, settings.FLIGHT_START_Y)
        for ring in self.rings:
            if ring.state == "missed" and ring.x > self.x:
                ring.state = "pending"
        self.invuln = settings.FLIGHT_RESPAWN_INVULN

    def show_box(self, text, title, action):
        self.box.show(text, title=title)
        self.box_action = action
        self.box_lock = settings.MESSAGE_LOCK

    def close_box(self):
        action = self.box_action
        self.box_action = None
        if action == "hub":
            self.manager.go_to("hub")
            return
        self.box.hide()
        if action == "respawn":
            self.respawn()

    def lose_life(self, extra=""):
        state = self.manager.state
        parts = [state.lose_life()]
        if extra:
            parts.append(extra)
        if state.game_over:
            parts.append(state.score_text())
        action = "hub" if state.game_over else "respawn"
        self.show_box("\n".join(parts), "Atenção", action)

    def check_rings(self):
        state = self.manager.state
        for ring in self.rings:
            if ring.state != "pending" or self.x < ring.x:
                continue
            if abs(self.y - ring.y) <= settings.FLIGHT_RING_GAP / 2:
                ring.state = "passed"
                state.add_ring()
            else:
                ring.state = "missed"
                if settings.FLIGHT_MISS_COSTS_LIFE:
                    self.lose_life()
                    return

    def update(self, dt):
        self.box.update(dt)
        self.box_lock = max(0.0, self.box_lock - dt)
        inputs = self.manager.input
        state = self.manager.state

        if self.box.visible:
            if inputs.pressed("confirm") and self.box_lock <= 0:
                self.close_box()
            return

        step = min(dt, 1 / 30)
        self.elapsed += dt
        self.invuln = max(0.0, self.invuln - dt)
        self.flap_time = max(0.0, self.flap_time - dt)
        state.add_time(dt)

        if inputs.pressed("jump"):
            self.vel_y = -settings.FLIGHT_FLAP
            self.flap_time = settings.FLIGHT_FLAP_ANIM

        self.vel_y = min(
            self.vel_y + settings.FLIGHT_GRAVITY * step, settings.FLIGHT_MAX_FALL
        )
        self.x += settings.FLIGHT_SPEED * step
        self.y += self.vel_y * step
        if self.y < settings.FLIGHT_CEILING:
            self.y = settings.FLIGHT_CEILING
            self.vel_y = max(self.vel_y, 0.0)

        self.check_rings()
        if self.box.visible:
            return

        floor = settings.FLIGHT_GROUND_Y - settings.FLIGHT_BODY_H / 2
        if self.y >= floor:
            if self.invuln > 0:
                self.y = floor
                self.vel_y = 0.0
            else:
                self.lose_life()
                return

        if self.x >= self.end_x:
            state.win()
            text = (
                state.messages["victory"] + "\n"
                + state.messages["voucher"] + "\n"
                + state.score_text()
            )
            self.show_box(text, "Parabéns", "hub")

    def draw_bird(self, surface):
        if self.invuln > 0 and int(self.elapsed * 12) % 2 == 0:
            return
        cx = settings.FLIGHT_CAMERA_X
        cy = round(self.y)
        body = pygame.Rect(0, 0, settings.FLIGHT_BODY_W, settings.FLIGHT_BODY_H)
        body.center = (cx, cy)
        tip_y = cy - 12 if self.flap_time > 0 else cy + 10
        wing = [(cx - 2, cy), (cx - 14, tip_y), (cx + 4, cy + 2)]
        pygame.draw.polygon(surface, settings.COLOR_TEXT, wing)
        pygame.draw.rect(surface, settings.COLOR_HIGHLIGHT, body)

    def draw(self, surface):
        surface.fill(settings.COLOR_BG)
        width = settings.INTERNAL_WIDTH
        camera = self.x - settings.FLIGHT_CAMERA_X

        ground = pygame.Rect(
            0, settings.FLIGHT_GROUND_Y, width,
            settings.INTERNAL_HEIGHT - settings.FLIGHT_GROUND_Y,
        )
        pygame.draw.rect(surface, settings.COLOR_PANEL, ground)
        pygame.draw.line(
            surface, settings.COLOR_DIM,
            (0, settings.FLIGHT_GROUND_Y), (width, settings.FLIGHT_GROUND_Y),
        )

        colors = {
            "pending": settings.COLOR_HIGHLIGHT,
            "passed": settings.COLOR_SUCCESS,
            "missed": settings.COLOR_DIM,
        }
        for ring in self.rings:
            sx = ring.x - camera
            if sx < -16 or sx > width + 16:
                continue
            rect = pygame.Rect(0, 0, 14, settings.FLIGHT_RING_GAP + 12)
            rect.center = (round(sx), round(ring.y))
            pygame.draw.ellipse(surface, colors[ring.state], rect, 3)

        self.draw_bird(surface)

        state = self.manager.state
        passed = sum(1 for ring in self.rings if ring.state == "passed")
        progress = f"argolas {passed}/{len(self.rings)}"
        surface.blit(self.font.render(progress, False, settings.COLOR_TEXT), (4, 2))
        draw_lives(surface, state.lives, settings.MAX_ATTEMPTS)
        draw_score(surface, self.font, state)

        if self.elapsed < 4.0:
            draw_text_centered(
                surface, state.messages["flight_hint"], self.font,
                settings.COLOR_HIGHLIGHT, width // 2, 176,
            )

        self.box.draw(surface)