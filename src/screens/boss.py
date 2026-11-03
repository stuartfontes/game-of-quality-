import random

import pygame

from src.core import progress, settings
from src.core.chests import Chest
from src.core.level import Level
from src.core.phases import load_phases
from src.core.player import Player
from src.core.screen import Screen
from src.core.ui import (
    MessageBox,
    draw_alert,
    draw_lives,
    draw_score,
    draw_text_centered,
)


class Step:
    def __init__(self, x, top, width):
        self.rect = pygame.Rect(x, top, width, settings.ARENA_PLATFORM_THICKNESS)
        self.dx = 0
        self.solid = True


class Barrel:
    def __init__(self, x, bottom, direction):
        size = settings.BARREL_SIZE
        self.rect = pygame.Rect(0, 0, size, size)
        self.rect.midbottom = (x, bottom)
        self.pos_x = float(self.rect.x)
        self.pos_y = float(self.rect.y)
        self.dir = direction
        self.vel_y = 0.0
        self.grounded = False
        self.fallen = 0.0
        self.dead = False

    def update(self, dt, solids):
        self.pos_x += self.dir * settings.BARREL_SPEED * dt
        self.rect.x = round(self.pos_x)

        self.vel_y = min(self.vel_y + settings.GRAVITY * dt, settings.MAX_FALL_SPEED)
        self.pos_y += self.vel_y * dt
        self.rect.y = round(self.pos_y)
        for tile in solids:
            if self.rect.colliderect(tile) and self.vel_y >= 0:
                self.rect.bottom = tile.top
                self.pos_y = float(self.rect.y)
                self.vel_y = 0.0

        probe = self.rect.move(0, 1)
        self.grounded = any(probe.colliderect(tile) for tile in solids)
        if self.grounded:
            if self.fallen > 6:
                self.dir *= -1
            self.fallen = 0.0
        else:
            self.fallen += max(0.0, self.vel_y) * dt

        outside = (
            self.rect.right < -20
            or self.rect.left > settings.INTERNAL_WIDTH + 20
            or self.rect.top > settings.INTERNAL_HEIGHT + 20
        )
        if outside:
            self.dead = True


class Stone:
    def __init__(self, x, y):
        size = settings.STONE_SIZE
        self.rect = pygame.Rect(0, 0, size, size)
        self.rect.midbottom = (x, y)
        self.pos_y = float(self.rect.y)
        self.vel_y = 0.0
        self.landed = False

    def update(self, dt, floor):
        if self.landed:
            return
        self.vel_y = min(self.vel_y + settings.GRAVITY * dt, settings.MAX_FALL_SPEED)
        self.pos_y += self.vel_y * dt
        self.rect.y = round(self.pos_y)
        if self.rect.bottom >= floor.top:
            self.rect.bottom = floor.top
            self.pos_y = float(self.rect.y)
            self.landed = True


class Shot:
    def __init__(self, x, y, direction):
        size = settings.STONE_SIZE
        self.rect = pygame.Rect(0, 0, size, size)
        self.rect.center = (x, y)
        self.pos_x = float(self.rect.x)
        self.pos_y = float(self.rect.y)
        self.vel_x = direction * settings.STONE_THROW_SPEED
        self.vel_y = -settings.STONE_THROW_LIFT
        self.dead = False

    def update(self, dt, solids):
        self.vel_y += settings.STONE_GRAVITY * dt
        self.pos_x += self.vel_x * dt
        self.pos_y += self.vel_y * dt
        self.rect.topleft = (round(self.pos_x), round(self.pos_y))
        if any(self.rect.colliderect(tile) for tile in solids):
            self.dead = True
        if self.rect.right < 0 or self.rect.left > settings.INTERNAL_WIDTH:
            self.dead = True


class BossScreen(Screen):
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
        self.player = None
        self.boss_rect = pygame.Rect(0, 0, *settings.BOSS_SIZE)
        self.boss_hp = settings.BOSS_HP
        self.boss_hit_timer = 0.0
        self.boss_dead = False
        self.barrels = []
        self.stones = []
        self.shots = []
        self.chests = []
        self.carrying = False
        self.barrel_side = True
        self.barrel_timer = 0.0
        self.stone_timer = 0.0
        self.elapsed = 0.0
        self.build_arena()

    @property
    def phase(self):
        return self.phases[self.manager.state.phase_index]

    def build_arena(self):
        width = settings.INTERNAL_WIDTH
        thick = settings.ARENA_PLATFORM_THICKNESS
        top = settings.ARENA_FLOOR_TOP
        l1, l2 = settings.ARENA_LEVELS
        start1, end1 = settings.ARENA_L1_SPAN
        start2, end2 = settings.ARENA_L2_SPAN
        self.floor = pygame.Rect(0, top, width, settings.INTERNAL_HEIGHT - top)
        self.platforms = [
            pygame.Rect(start1, l1, end1 - start1, thick),
            pygame.Rect(start2, l2, end2 - start2, thick),
        ]
        self.steps = [Step(x, y, w) for x, y, w in settings.ARENA_STEPS]
        walls = [pygame.Rect(-40, -300, 40, 700), pygame.Rect(width, -300, 40, 700)]
        self.rolling = [self.floor] + self.platforms
        self.solids = self.rolling + walls
        self.boss_rect.midbottom = (width // 2, l2)

    def on_enter(self):
        self.manager.state.resume = False
        self.boss_hp = settings.BOSS_HP
        self.boss_hit_timer = 0.0
        self.boss_dead = False
        self.barrels = []
        self.stones = []
        self.shots = []
        self.chests = []
        self.carrying = False
        self.barrel_side = True
        self.barrel_timer = 1.5
        self.stone_timer = 1.0
        self.elapsed = 0.0
        self.box_action = None
        self.box.hide()
        self.spawn_player()

    def spawn_player(self):
        self.player = Player(24, settings.ARENA_FLOOR_TOP - settings.PLAYER_HEIGHT)
        self.player.invuln_time = settings.RESPAWN_INVULN

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
            self.spawn_player()

    def lose_life(self, extra=""):
        state = self.manager.state
        parts = [state.lose_life()]
        if extra:
            parts.append(extra)
        if state.game_over:
            parts.append(state.score_text())
            action = "hub"
        elif self.boss_dead:
            action = "continue"
        else:
            action = "respawn"
        self.show_box("\n".join(parts), "Atenção", action)

    def spawn_barrel(self):
        l2 = settings.ARENA_LEVELS[1]
        direction = 1 if self.barrel_side else -1
        self.barrel_side = not self.barrel_side
        if direction > 0:
            x = self.boss_rect.right + 10
        else:
            x = self.boss_rect.left - 10
        self.barrels.append(Barrel(x, l2, direction))

    def spawn_stone(self):
        low = 40
        high = settings.INTERNAL_WIDTH - 90
        x = random.randint(low, high)
        self.stones.append(Stone(x, settings.ARENA_FLOOR_TOP - 70))

    def hit_boss(self):
        if self.boss_hit_timer > 0:
            return
        self.boss_hp -= 1
        self.boss_hit_timer = settings.BOSS_HIT_INVULN
        if self.boss_hp <= 0:
            self.defeat_boss()

    def defeat_boss(self):
        self.boss_dead = True
        self.barrels = []
        self.stones = []
        self.shots = []
        self.carrying = False
        self.manager.state.add_kill()
        l1, l2 = settings.ARENA_LEVELS
        spots = (
            ("up", l2),
            ("straight", l1),
            ("down", settings.ARENA_FLOOR_TOP),
        )
        x = settings.INTERNAL_WIDTH // 2
        self.chests = [Chest(choice, x, bottom, 0) for choice, bottom in spots]

    def update_boss(self, dt):
        self.boss_hit_timer = max(0.0, self.boss_hit_timer - dt)
        if self.boss_dead:
            return

        self.barrel_timer -= dt
        if self.barrel_timer <= 0:
            self.spawn_barrel()
            hits = settings.BOSS_HP - self.boss_hp
            interval = settings.BOSS_BARREL_INTERVAL - 0.35 * hits
            self.barrel_timer = max(settings.BOSS_BARREL_MIN_INTERVAL, interval)

        self.stone_timer -= dt
        if self.stone_timer <= 0:
            self.stone_timer = settings.STONE_INTERVAL
            if len(self.stones) < settings.STONE_MAX:
                self.spawn_stone()

    def update_barrels(self, dt):
        for barrel in self.barrels:
            barrel.update(dt, self.rolling)
        self.barrels = [barrel for barrel in self.barrels if not barrel.dead]

    def update_stones(self, dt):
        for stone in self.stones:
            stone.update(dt, self.floor)
        if self.carrying:
            return
        for stone in self.stones:
            if stone.landed and self.player.rect.colliderect(stone.rect):
                self.stones.remove(stone)
                self.carrying = True
                return

    def update_shots(self, dt):
        for shot in self.shots:
            shot.update(dt, self.rolling)
            if shot.dead or self.boss_dead:
                continue
            if shot.rect.colliderect(self.boss_rect):
                shot.dead = True
                self.hit_boss()
        self.shots = [shot for shot in self.shots if not shot.dead]

    def chest_in_reach(self):
        reach = settings.CHEST_REACH * 2
        for chest in self.chests:
            if chest.opened or chest.hidden:
                continue
            if self.player.rect.colliderect(chest.rect.inflate(reach, reach)):
                return chest
        return None

    def open_chest(self, chest):
        state = self.manager.state
        chest.opened = True
        chest.item = self.level.item_for(state.phase_index, chest.choice)
        result = progress.resolve_choice(state, self.level, self.phases, chest.choice)
        if result["correct"]:
            self.show_box(result["text"], result["title"], result["action"])
        else:
            self.lose_life(state.messages["chest_wrong"] + " " + result["item"])

    def throw(self):
        player = self.player
        self.shots.append(
            Shot(player.rect.centerx, player.rect.centery - 4, player.facing)
        )
        self.carrying = False

    def interact(self):
        chest = self.chest_in_reach()
        if chest is not None:
            self.open_chest(chest)
            return
        if self.carrying:
            self.throw()

    def check_barrels(self):
        player = self.player
        for barrel in self.barrels:
            if player.rect.colliderect(barrel.rect) and not player.invulnerable:
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
        state.add_time(dt)

        self.player.update(step, inputs, self.solids, self.steps)
        self.update_boss(step)
        self.update_barrels(step)
        self.update_stones(step)
        self.update_shots(step)

        if inputs.pressed("interact"):
            self.interact()
            if self.box.visible:
                return
        self.check_barrels()

    def draw_boss(self, surface):
        if self.boss_dead:
            return
        flash = self.boss_hit_timer > 0 and int(self.elapsed * 15) % 2 == 0
        color = settings.COLOR_TEXT if flash else settings.COLOR_BOSS
        pygame.draw.rect(surface, color, self.boss_rect)
        pygame.draw.rect(surface, settings.COLOR_TEXT, self.boss_rect, 1)
        eye_y = self.boss_rect.y + 10
        for eye_x in (self.boss_rect.x + 9, self.boss_rect.right - 15):
            pygame.draw.rect(surface, settings.COLOR_BG, (eye_x, eye_y, 6, 6))

    def draw(self, surface):
        surface.fill(settings.COLOR_BG)
        state = self.manager.state
        width = settings.INTERNAL_WIDTH

        pygame.draw.rect(surface, settings.COLOR_PANEL, self.floor)
        pygame.draw.line(
            surface, settings.COLOR_DIM,
            (0, self.floor.top), (width, self.floor.top),
        )
        for plat in self.platforms:
            pygame.draw.rect(surface, settings.COLOR_PANEL, plat)
            pygame.draw.rect(surface, settings.COLOR_DIM, plat, 1)
        for step in self.steps:
            pygame.draw.rect(surface, settings.COLOR_PANEL, step.rect)
            pygame.draw.rect(surface, settings.COLOR_HIGHLIGHT, step.rect, 1)

        self.draw_boss(surface)

        for barrel in self.barrels:
            pygame.draw.circle(
                surface, settings.COLOR_BARREL, barrel.rect.center, barrel.rect.width // 2
            )
            pygame.draw.circle(
                surface, settings.COLOR_TEXT, barrel.rect.center, barrel.rect.width // 2, 1
            )

        for stone in self.stones:
            pygame.draw.rect(surface, settings.COLOR_STONE, stone.rect)
        for shot in self.shots:
            pygame.draw.rect(surface, settings.COLOR_STONE, shot.rect)

        for chest in self.chests:
            if chest.hidden:
                continue
            body = settings.COLOR_DIM if chest.opened else settings.COLOR_CHEST
            pygame.draw.rect(surface, body, chest.rect)
            pygame.draw.rect(surface, settings.COLOR_TEXT, chest.rect, 1)
            text = None
            if chest.opened:
                text = chest.item
            elif settings.CHEST_LABELS_VISIBLE:
                text = self.level.item_for(state.phase_index, chest.choice)
            if text:
                label = self.font.render(text, False, settings.COLOR_TEXT)
                surface.blit(
                    label, (chest.rect.centerx - label.get_width() // 2, chest.rect.top - 14)
                )

        player = self.player
        blink = (
            player.invuln_time > 0
            and not player.dashing
            and int(self.elapsed * 12) % 2 == 0
        )
        if not blink:
            if player.dashing:
                color = settings.COLOR_TEXT
            elif player.can_dash:
                color = settings.COLOR_HIGHLIGHT
            else:
                color = settings.COLOR_DIM
            pygame.draw.rect(surface, color, player.rect)
        if self.carrying:
            held = pygame.Rect(0, 0, 8, 8)
            held.midbottom = (player.rect.centerx, player.rect.top - 1)
            pygame.draw.rect(surface, settings.COLOR_STONE, held)

        if self.chest_in_reach() is not None:
            hint = self.font.render("E abrir", False, settings.COLOR_HIGHLIGHT)
            surface.blit(
                hint, (player.rect.centerx - hint.get_width() // 2, player.rect.top - 14)
            )

        progress_text = f"{self.phase.name}   baús {state.phase_index}/{len(self.phases)}"
        surface.blit(self.font.render(progress_text, False, settings.COLOR_TEXT), (4, 2))
        if not self.boss_dead:
            bar = pygame.Rect(46, 19, 120, 6)
            pygame.draw.rect(surface, settings.COLOR_PANEL, bar)
            ratio = self.boss_hp / settings.BOSS_HP
            fill = pygame.Rect(bar.x, bar.y, round(bar.width * ratio), bar.height)
            pygame.draw.rect(surface, settings.COLOR_ERROR, fill)
            pygame.draw.rect(surface, settings.COLOR_DIM, bar, 1)
            surface.blit(self.font.render("Chefe", False, settings.COLOR_TEXT), (4, 16))
        if self.carrying:
            held_text = self.font.render("Pedra: E joga", False, settings.COLOR_HIGHLIGHT)
            surface.blit(held_text, (4, 28))
        draw_lives(surface, state.lives, settings.MAX_ATTEMPTS)
        draw_score(surface, self.font, state)

        if self.boss_dead:
            draw_alert(surface, self.alert_font, self.prompt_font, state.messages["fork_prompt"])
        elif self.elapsed < 6.0:
            draw_text_centered(
                surface, state.messages["boss_hint"], self.font,
                settings.COLOR_HIGHLIGHT, width // 2, 196,
            )

        self.box.draw(surface)