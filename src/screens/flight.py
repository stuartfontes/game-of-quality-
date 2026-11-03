import math
import random

import pygame

from src.core import progress, settings
from src.core.chests import Chest
from src.core.level import Level
from src.core.phases import load_phases
from src.core.screen import Screen
from src.core.ui import (
    MessageBox,
    draw_alert,
    draw_lives,
    draw_score,
    draw_text_centered,
)


class Ring:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.state = "pending"


class Pipe:
    def __init__(self, x, gap_y):
        self.x = x
        self.gap_y = gap_y

    def rects(self):
        half = settings.FLIGHT_PIPE_WIDTH // 2
        gap = settings.FLIGHT_PIPE_GAP
        top_h = round(self.gap_y - gap / 2) + 40
        top = pygame.Rect(round(self.x) - half, -40, settings.FLIGHT_PIPE_WIDTH, top_h)
        bottom_y = round(self.gap_y + gap / 2)
        bottom = pygame.Rect(
            round(self.x) - half, bottom_y,
            settings.FLIGHT_PIPE_WIDTH, settings.INTERNAL_HEIGHT - bottom_y,
        )
        return top, bottom


class Orb:
    def __init__(self, x, center_y):
        self.x = x
        self.center_y = center_y
        self.phase = random.uniform(0, math.tau)

    def y(self, t):
        wave = math.sin(t * settings.FLIGHT_ORB_SPEED + self.phase)
        return self.center_y + wave * settings.FLIGHT_ORB_AMPLITUDE

    def hits(self, rect, t):
        cy = self.y(t)
        nearest_x = max(rect.left, min(self.x, rect.right))
        nearest_y = max(rect.top, min(cy, rect.bottom))
        dx = self.x - nearest_x
        dy = cy - nearest_y
        return dx * dx + dy * dy <= settings.FLIGHT_ORB_RADIUS ** 2


class FlightScreen(Screen):
    def __init__(self, manager):
        super().__init__(manager)
        self.level = Level()
        self.phases = load_phases()
        assets = manager.assets
        self.font = assets.font(settings.FONT_FILE, settings.FONT_SIZE_SMALL)
        self.prompt_font = assets.font(settings.FONT_FILE, settings.FONT_SIZE_PROMPT)
        self.alert_font = assets.font(settings.FONT_FILE, settings.FONT_SIZE_ALERT)
        self.box = MessageBox((16, 96, 352, 108), self.font)
        self.box_lock = 0.0
        self.box_action = None
        self.rings = []
        self.pipes = []
        self.orbs = []
        self.doors = []
        self.x = 0.0
        self.y = 0.0
        self.vel_y = 0.0
        self.flap_time = 0.0
        self.invuln = 0.0
        self.elapsed = 0.0
        self.door_x = 0.0

    @property
    def phase(self):
        return self.phases[self.manager.state.phase_index]

    def on_enter(self):
        self.manager.state.resume = False
        self.build_course()
        self.place(0.0, settings.FLIGHT_START_Y)
        self.invuln = 0.0
        self.elapsed = 0.0
        self.box_action = None
        self.box.hide()

    def build_course(self):
        count = self.phase.rings
        self.rings = []
        self.pipes = []
        self.orbs = []
        y = settings.FLIGHT_START_Y
        for i in range(count):
            y += random.randint(-settings.FLIGHT_RING_STEP, settings.FLIGHT_RING_STEP)
            y = max(settings.FLIGHT_RING_MIN_Y, min(settings.FLIGHT_RING_MAX_Y, y))
            x = settings.FLIGHT_FIRST_RING_X + i * settings.FLIGHT_RING_SPACING
            self.rings.append(Ring(x, y))

        for a, b in zip(self.rings, self.rings[1:]):
            mid_x = (a.x + b.x) / 2
            mid_y = (a.y + b.y) / 2
            if random.random() < 0.5:
                self.pipes.append(Pipe(mid_x, mid_y))
            else:
                self.orbs.append(Orb(mid_x, mid_y))

        last = self.rings[-1]
        self.door_x = last.x + settings.FLIGHT_DOOR_DISTANCE
        top = settings.FLIGHT_CEILING
        height = (settings.FLIGHT_GROUND_Y - top) // 3
        self.doors = []
        for i, choice in enumerate(("up", "straight", "down")):
            zone = pygame.Rect(0, 0, settings.FLIGHT_DOOR_WIDTH, height)
            zone.midtop = (round(self.door_x), top + i * height)
            bottom = zone.centery + settings.CHEST_HEIGHT // 2
            chest = Chest(choice, zone.centerx, bottom, 0)
            self.doors.append((chest, zone))

    def place(self, x, y):
        self.x = x
        self.y = y
        self.vel_y = 0.0
        self.flap_time = 0.0

    def bird_rect(self):
        rect = pygame.Rect(0, 0, settings.FLIGHT_BODY_W, settings.FLIGHT_BODY_H)
        rect.center = (round(self.x), round(self.y))
        return rect

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
        if action and action.startswith("go:"):
            self.manager.state.resume = True
            self.manager.go_to(action[3:])
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

    def door_touched(self):
        rect = self.bird_rect()
        for chest, zone in self.doors:
            if chest.opened:
                continue
            if rect.colliderect(zone):
                return chest
        return None

    def open_door(self, chest):
        state = self.manager.state
        chest.opened = True
        chest.item = self.level.item_for(state.phase_index, chest.choice)
        result = progress.resolve_choice(state, self.level, self.phases, chest.choice)
        if result["correct"]:
            self.show_box(result["text"], result["title"], result["action"])
        else:
            self.lose_life(state.messages["chest_wrong"] + " " + result["item"])

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

    def check_obstacles(self):
        if self.invuln > 0:
            return False
        rect = self.bird_rect()
        for pipe in self.pipes:
            if abs(pipe.x - self.x) > 40:
                continue
            if any(rect.colliderect(part) for part in pipe.rects()):
                self.lose_life()
                return True
        for orb in self.orbs:
            if abs(orb.x - self.x) > 40:
                continue
            if orb.hits(rect, self.elapsed):
                self.lose_life()
                return True
        return False

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

        if self.check_obstacles():
            return

        touched = self.door_touched()
        if touched is not None:
            self.open_door(touched)
            return

        if self.x > self.door_x + 60:
            self.respawn()

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
        height = settings.INTERNAL_HEIGHT
        camera = round(self.x - settings.FLIGHT_CAMERA_X)
        state = self.manager.state

        ground = pygame.Rect(
            0, settings.FLIGHT_GROUND_Y, width, height - settings.FLIGHT_GROUND_Y
        )
        pygame.draw.rect(surface, settings.COLOR_PANEL, ground)
        pygame.draw.line(
            surface, settings.COLOR_DIM,
            (0, settings.FLIGHT_GROUND_Y), (width, settings.FLIGHT_GROUND_Y),
        )

        for pipe in self.pipes:
            for part in pipe.rects():
                shown = part.move(-camera, 0)
                if shown.right < 0 or shown.left > width:
                    continue
                pygame.draw.rect(surface, settings.COLOR_PIPE, shown)
                pygame.draw.rect(surface, settings.COLOR_TEXT, shown, 1)

        for orb in self.orbs:
            sx = orb.x - camera
            if sx < -16 or sx > width + 16:
                continue
            center = (round(sx), round(orb.y(self.elapsed)))
            pygame.draw.circle(surface, settings.COLOR_ORB, center, settings.FLIGHT_ORB_RADIUS)
            pygame.draw.circle(surface, settings.COLOR_TEXT, center, settings.FLIGHT_ORB_RADIUS, 1)

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

        for chest, zone in self.doors:
            shown_zone = zone.move(-camera, 0)
            if shown_zone.right < 0 or shown_zone.left > width:
                continue
            outline = settings.COLOR_DIM if chest.opened else settings.COLOR_CHEST
            pygame.draw.rect(surface, outline, shown_zone, 1)
            icon = chest.rect.move(-camera, 0)
            body = settings.COLOR_DIM if chest.opened else settings.COLOR_CHEST
            pygame.draw.rect(surface, body, icon)
            pygame.draw.rect(surface, settings.COLOR_TEXT, icon, 1)
            text = None
            if chest.opened:
                text = chest.item
            elif settings.CHEST_LABELS_VISIBLE:
                text = self.level.item_for(state.phase_index, chest.choice)
            if text:
                label = self.font.render(text, False, settings.COLOR_TEXT)
                surface.blit(label, (icon.centerx - label.get_width() // 2, icon.top - 14))

        self.draw_bird(surface)

        passed = sum(1 for ring in self.rings if ring.state == "passed")
        progress_text = (
            f"{self.phase.name}   argolas {passed}/{len(self.rings)}   "
            f"baús {state.phase_index}/{len(self.phases)}"
        )
        surface.blit(self.font.render(progress_text, False, settings.COLOR_TEXT), (4, 2))
        draw_lives(surface, state.lives, settings.MAX_ATTEMPTS)
        draw_score(surface, self.font, state)

        if self.x >= self.rings[-1].x:
            draw_alert(surface, self.alert_font, self.prompt_font, state.messages["fork_prompt"])
        elif self.elapsed < 4.0:
            draw_text_centered(
                surface, state.messages["flight_hint"], self.font,
                settings.COLOR_HIGHLIGHT, width // 2, 176,
            )

        self.box.draw(surface)