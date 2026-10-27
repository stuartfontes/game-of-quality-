import pygame

from src.core import settings
from src.core.level import Level
from src.core.level_generator import LevelGenerator
from src.core.phases import load_phases
from src.core.player import Player
from src.core.screen import Screen
from src.core.ui import MessageBox, draw_lives, draw_score, wrap_text


class PlatformScreen(Screen):
    def __init__(self, manager):
        super().__init__(manager)
        self.generator = LevelGenerator()
        self.level = Level()
        self.phases = load_phases()
        self.phase_index = 0
        self.phase_forks = 0
        self.player = None
        self.camera_x = 0
        self.checkpoint = 0
        self.elapsed = 0.0
        self.fork_index = 0
        self.next_fork_request = 0.0
        self.box_lock = 0.0
        self.box_action = None
        assets = manager.assets
        self.font = assets.font(settings.FONT_FILE, settings.FONT_SIZE_SMALL)
        self.prompt_font = assets.font(settings.FONT_FILE, settings.FONT_SIZE_PROMPT)
        self.alert_font = assets.font(settings.FONT_FILE, settings.FONT_SIZE_ALERT)
        self.box = MessageBox((16, 96, 352, 108), self.font)

    def on_enter(self):
        self.manager.state.start_run("plataforma")
        self.phase_index = 0
        self.phase_forks = 0
        self.generator.reset(self.phases[0].group)
        self.checkpoint = 0
        self.elapsed = 0.0
        self.fork_index = 0
        self.next_fork_request = settings.FORK_INTERVAL - settings.FORK_LEAD
        self.box_action = None
        self.box.hide()
        self.spawn(0)

    def spawn(self, chunk_start):
        size = settings.TILE_SIZE
        px = chunk_start + size + (size - settings.PLAYER_WIDTH) // 2
        py = (settings.MAP_ROWS - 1) * size - settings.PLAYER_HEIGHT
        self.player = Player(px, py)
        self.camera_x = max(0, self.player.rect.centerx - settings.CAMERA_OFFSET_X)
        self.generator.ensure(self.camera_x + settings.INTERNAL_WIDTH)

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
        if action == "flight":
            self.manager.go_to("voo")
            return
        self.box.hide()
        if action == "respawn":
            self.spawn(self.checkpoint)
            self.player.invuln_time = settings.RESPAWN_INVULN

    def lose_life(self, extra=""):
        state = self.manager.state
        parts = [state.lose_life()]
        if extra:
            parts.append(extra)
        if state.game_over:
            parts.append(state.score_text())
        action = "hub" if state.game_over else "respawn"
        self.show_box("\n".join(parts), "Atenção", action)

    def schedule_fork(self):
        if self.fork_index >= self.level.fork_count:
            return
        if self.elapsed < self.next_fork_request or self.generator.fork_busy:
            return
        self.generator.request_fork()
        self.next_fork_request = self.elapsed + settings.FORK_INTERVAL

    def chest_in_reach(self):
        reach = settings.CHEST_REACH * 2
        for chest in self.generator.chests:
            if chest.hidden or chest.opened:
                continue
            if self.player.rect.colliderect(chest.rect.inflate(reach, reach)):
                return chest
        return None

    def fork_prompt_visible(self):
        placed = self.generator.pending_fork()
        if placed is None:
            return False
        player = self.player
        return (
            player.rect.right > placed.start - settings.FORK_PROMPT_DISTANCE
            and player.rect.left < placed.end
        )

    def after_correct(self, item):
        state = self.manager.state
        phase = self.phases[self.phase_index]
        last_phase = self.phase_index >= len(self.phases) - 1
        finished = self.fork_index >= self.level.fork_count

        if self.phase_forks >= phase.forks or finished:
            if finished or last_phase:
                self.show_box(state.messages["wings"], "Asas!", "flight")
                return
            self.phase_index += 1
            self.phase_forks = 0
            following = self.phases[self.phase_index]
            self.generator.set_group(following.group)
            self.show_box(following.intro, following.name, "continue")
            return

        text = state.messages["chest_correct"] + "\n" + item
        self.show_box(text, "Correto", "continue")

    def try_open_chest(self):
        chest = self.chest_in_reach()
        if chest is None:
            return False

        state = self.manager.state
        chest.opened = True
        item = self.level.item_for(self.fork_index, chest.choice)
        chest.item = item

        if self.level.is_correct(self.fork_index, chest.choice):
            self.generator.resolve_fork(chest.fork_id, chest)
            self.fork_index += 1
            self.phase_forks += 1
            self.after_correct(item)
        else:
            self.lose_life(state.messages["chest_wrong"] + " " + item)
        return True

    def check_mobs(self):
        player = self.player
        for mob in self.generator.mobs:
            if not mob.alive or not mob.active:
                continue
            if not player.rect.colliderect(mob.rect):
                continue
            stomp = (
                mob.kind.stompable
                and player.vel_y > 0
                and mob.hurt_time <= 0
                and player.rect.bottom - mob.rect.top <= settings.STOMP_TOLERANCE
            )
            if stomp:
                if mob.hit():
                    self.manager.state.add_kill()
                player.bounce(mob.rect.top)
                continue
            if mob.hurt_time > 0 or player.invulnerable:
                continue
            self.lose_life()
            return True
        return False

    def update(self, dt):
        self.box.update(dt)
        self.box_lock = max(0.0, self.box_lock - dt)
        inputs = self.manager.input

        if self.box.visible:
            if inputs.pressed("confirm") and self.box_lock <= 0:
                self.close_box()
            return

        if inputs.pressed("back"):
            self.manager.go_to("hub")
            return
        if settings.DEBUG_HUD and inputs.pressed("restart"):
            self.spawn(self.checkpoint)
            return

        step = min(dt, 1 / 30)
        self.elapsed += dt
        self.manager.state.add_time(dt)
        self.schedule_fork()
        self.generator.ensure(self.camera_x + settings.INTERNAL_WIDTH)
        self.generator.update_platforms(step, self.player, self.camera_x)

        left = self.player.rect.left - settings.TILE_SIZE * 2
        right = self.player.rect.right + settings.TILE_SIZE * 2
        solids = self.generator.solids_near(left, right)
        platforms = self.generator.platforms_near(left, right)
        self.player.update(step, inputs, solids, platforms)

        target = max(0, self.player.rect.centerx - settings.CAMERA_OFFSET_X)
        self.camera_x = max(self.camera_x, target)
        self.player.clamp_left(self.camera_x)
        self.generator.update_mobs(step, self.camera_x)

        if self.player.on_ground:
            self.checkpoint = self.generator.chunk_at(self.player.rect.centerx).start

        if inputs.pressed("interact") and self.try_open_chest():
            return
        if self.check_mobs():
            return

        if self.player.rect.top > settings.MAP_ROWS * settings.TILE_SIZE:
            if settings.FALL_COSTS_LIFE:
                self.lose_life()
            else:
                self.spawn(self.checkpoint)

    def draw_prompt(self, surface, text):
        center_x = settings.INTERNAL_WIDTH // 2

        mark = self.alert_font.render("!", False, settings.COLOR_HIGHLIGHT).convert_alpha()
        mark.set_alpha(settings.PROMPT_ALPHA)
        surface.blit(mark, (center_x - mark.get_width() // 2, settings.PROMPT_MARK_Y))

        font = self.prompt_font
        lines = wrap_text(text, font, settings.INTERNAL_WIDTH - 24)
        line_h = font.get_linesize()
        y = settings.INTERNAL_HEIGHT - settings.PROMPT_BOTTOM_MARGIN - line_h * len(lines)
        for line in lines:
            shadow = font.render(line, False, settings.COLOR_BG)
            label = font.render(line, False, settings.COLOR_HIGHLIGHT)
            x = center_x - label.get_width() // 2
            surface.blit(shadow, (x + 1, y + 1))
            surface.blit(label, (x, y))
            y += line_h

    def draw(self, surface):
        surface.fill(settings.COLOR_BG)
        camera_x = self.camera_x
        width = settings.INTERNAL_WIDTH

        for tile in self.generator.tiles_near(camera_x, camera_x + width):
            shown = tile.move(-camera_x, 0)
            if shown.right < 0 or shown.left > width:
                continue
            pygame.draw.rect(surface, settings.COLOR_PANEL, shown)
            pygame.draw.rect(surface, settings.COLOR_DIM, shown, 1)

        for plat in self.generator.platforms_near(camera_x, camera_x + width):
            if not plat.solid:
                continue
            shown = plat.rect.move(-camera_x + plat.jitter(), 0)
            pygame.draw.rect(surface, plat.color(), shown)

        for barrier in self.generator.barriers:
            if barrier.open:
                continue
            shown = barrier.rect.move(-camera_x, 0)
            if shown.right < 0 or shown.left > width:
                continue
            pygame.draw.rect(surface, settings.COLOR_PANEL, shown)
            pygame.draw.rect(surface, settings.COLOR_ERROR, shown, 2)

        for chest in self.generator.chests:
            if chest.hidden:
                continue
            shown = chest.rect.move(-camera_x, 0)
            if shown.right < 0 or shown.left > width:
                continue
            body = settings.COLOR_DIM if chest.opened else settings.COLOR_CHEST
            pygame.draw.rect(surface, body, shown)
            pygame.draw.rect(surface, settings.COLOR_TEXT, shown, 1)
            text = None
            if chest.opened:
                text = chest.item
            elif settings.CHEST_LABELS_VISIBLE and self.fork_index < self.level.fork_count:
                text = self.level.item_for(self.fork_index, chest.choice)
            if text:
                label = self.font.render(text, False, settings.COLOR_TEXT)
                surface.blit(label, (shown.centerx - label.get_width() // 2, shown.top - 12))

        for mob in self.generator.mobs:
            shown = mob.rect.move(-camera_x, 0)
            if shown.right < 0 or shown.left > width:
                continue
            pygame.draw.rect(surface, mob.kind.color, shown)

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
            pygame.draw.rect(surface, color, player.rect.move(-camera_x, 0))

        if self.chest_in_reach() is not None:
            hint = self.font.render("E abrir", False, settings.COLOR_HIGHLIGHT)
            hx = player.rect.centerx - camera_x - hint.get_width() // 2
            surface.blit(hint, (hx, player.rect.top - 14))

        phase = self.phases[self.phase_index]
        progress = f"{phase.name}   baús {self.fork_index}/{self.level.fork_count}"
        surface.blit(self.font.render(progress, False, settings.COLOR_TEXT), (4, 2))
        if settings.DEBUG_HUD:
            chunk = self.generator.chunk_at(player.rect.centerx)
            debug = f"{self.elapsed:.1f} s   bloco {chunk.name}"
            surface.blit(self.font.render(debug, False, settings.COLOR_DIM), (4, 16))
            help_text = "ESPAÇO pular  SHIFT dash  E abrir  R reiniciar  BACKSPACE sair"
            surface.blit(self.font.render(help_text, False, settings.COLOR_DIM), (4, 28))
        draw_lives(surface, self.manager.state.lives, settings.MAX_ATTEMPTS)
        draw_score(surface, self.font, self.manager.state)

        if self.fork_prompt_visible():
            self.draw_prompt(surface, self.manager.state.messages["fork_prompt"])

        self.box.draw(surface)