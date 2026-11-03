import math

import pygame

from src.core import progress, settings
from src.core.level import Level
from src.core.level_generator import LevelGenerator
from src.core.phases import load_phases
from src.core.player import Player
from src.core.screen import Screen
from src.core.ui import MessageBox, draw_alert, draw_lives, draw_score


class PlatformScreen(Screen):
    def __init__(self, manager):
        super().__init__(manager)
        self.generator = LevelGenerator()
        self.level = Level()
        self.phases = load_phases()
        if len(self.phases) != self.level.fork_count:
            raise ValueError(
                f"phases.json tem {len(self.phases)} fases e level.json tem "
                f"{self.level.fork_count} etapas"
            )
        self.player = None
        self.redirect = None
        self.camera_x = 0
        self.checkpoint = 0
        self.elapsed = 0.0
        self.phase_time = 0.0
        self.pending_portals = []
        self.fork_scheduled = False
        self.inverted = False
        self.flash = 0.0
        self.box_lock = 0.0
        self.box_action = None

        assets = manager.assets
        self.font = assets.font(settings.FONT_FILE, settings.FONT_SIZE_SMALL)
        self.prompt_font = assets.font(settings.FONT_FILE, settings.FONT_SIZE_PROMPT)
        self.alert_font = assets.font(settings.FONT_FILE, settings.FONT_SIZE_ALERT)
        self.box = MessageBox((16, 96, 352, 108), self.font)

        size = (settings.INTERNAL_WIDTH, settings.INTERNAL_HEIGHT)
        self.world = pygame.Surface(size)
        self.flash_surface = pygame.Surface(size)
        self.flash_surface.fill((255, 255, 255))
        self.portal_band = pygame.Surface((settings.TILE_SIZE, settings.INTERNAL_HEIGHT))
        self.portal_band.fill(settings.COLOR_PORTAL)

    @property
    def phase(self):
        return self.phases[self.manager.state.phase_index]

    def on_enter(self):
        state = self.manager.state
        self.redirect = None
        if state.resume:
            state.resume = False
        else:
            state.start_run("plataforma")
            state.phase_index = settings.DEBUG_START_PHASE
            kind = self.phases[state.phase_index].kind
            if kind != "platformer":
                self.redirect = progress.SCREENS[kind]
        self.elapsed = 0.0
        self.begin_phase()

    def begin_phase(self):
        phase = self.phase
        self.generator.reset(phase.group)
        self.phase_time = 0.0
        self.pending_portals = sorted(phase.portals)
        self.fork_scheduled = False
        self.checkpoint = 0
        self.flash = 0.0
        self.box_action = None
        self.box.hide()
        self.schedule_events()
        self.spawn(0)

    def spawn(self, chunk_start):
        placed = self.generator.chunk_at(chunk_start)
        self.inverted = placed.orient
        for portal in self.generator.portals:
            if portal.rect.right > chunk_start:
                portal.used = False
        size = settings.TILE_SIZE
        px = chunk_start + size + (size - settings.PLAYER_WIDTH) // 2
        py = (settings.MAP_ROWS - 1) * size - settings.PLAYER_HEIGHT
        self.player = Player(px, py)
        self.camera_x = max(0, self.player.rect.centerx - settings.CAMERA_OFFSET_X)
        self.generator.ensure(self.camera_x + settings.INTERNAL_WIDTH)

    def schedule_events(self):
        phase = self.phase
        while self.pending_portals:
            moment = max(0.0, self.pending_portals[0] * phase.duration - settings.PORTAL_LEAD)
            if self.phase_time < moment:
                break
            self.pending_portals.pop(0)
            self.generator.request_portal()
        if not self.fork_scheduled and self.phase_time >= phase.duration - settings.FORK_LEAD:
            self.fork_scheduled = True
            self.generator.request_fork()

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

    def try_open_chest(self):
        chest = self.chest_in_reach()
        if chest is None:
            return False

        state = self.manager.state
        chest.opened = True
        chest.item = self.level.item_for(state.phase_index, chest.choice)
        result = progress.resolve_choice(state, self.level, self.phases, chest.choice)
        if result["correct"]:
            self.generator.resolve_fork(chest.fork_id, chest)
            self.show_box(result["text"], result["title"], result["action"])
        else:
            self.lose_life(state.messages["chest_wrong"] + " " + result["item"])
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

    def check_portals(self):
        for portal in self.generator.portals:
            if portal.used:
                continue
            if self.player.rect.colliderect(portal.rect):
                portal.used = True
                self.inverted = not self.inverted
                self.flash = settings.PORTAL_FLASH

    def update(self, dt):
        self.box.update(dt)
        self.box_lock = max(0.0, self.box_lock - dt)
        inputs = self.manager.input

        if self.redirect is not None:
            target = self.redirect
            self.redirect = None
            self.manager.state.resume = True
            self.manager.go_to(target)
            return

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
        self.phase_time += dt
        self.flash = max(0.0, self.flash - dt)
        self.manager.state.add_time(dt)
        self.schedule_events()
        self.generator.ensure(self.camera_x + settings.INTERNAL_WIDTH)
        self.generator.update_platforms(step, self.player, self.camera_x)

        left = self.player.rect.left - settings.TILE_SIZE * 2
        right = self.player.rect.right + settings.TILE_SIZE * 2
        solids = self.generator.solids_near(left, right)
        platforms = self.generator.platforms_near(left, right)
        chains = self.generator.chains_near(left - 160, right + 160)
        self.player.update(step, inputs, solids, platforms, chains)

        player = self.player
        if self.phase.free_camera:
            if player.hanging:
                target = player.chain.anchor_x - settings.INTERNAL_WIDTH // 2
            else:
                target = player.rect.centerx - settings.CAMERA_OFFSET_X
            target = max(0, target)
            blend = min(1.0, settings.CAMERA_SMOOTH * step)
            self.camera_x += (target - self.camera_x) * blend
            player.clamp_left(0)
        else:
            target = max(0, player.rect.centerx - settings.CAMERA_OFFSET_X)
            self.camera_x = max(self.camera_x, target)
            player.clamp_left(self.camera_x)
        self.generator.update_mobs(step, self.camera_x)
        self.check_portals()

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

    def to_screen(self, rect):
        if not self.inverted:
            return rect
        return pygame.Rect(
            rect.x, settings.INTERNAL_HEIGHT - rect.bottom, rect.width, rect.height
        )

    def draw(self, surface):
        world = self.world
        world.fill(settings.COLOR_BG)
        camera_x = int(self.camera_x)
        width = settings.INTERNAL_WIDTH

        for tile in self.generator.tiles_near(camera_x, camera_x + width):
            shown = tile.move(-camera_x, 0)
            if shown.right < 0 or shown.left > width:
                continue
            pygame.draw.rect(world, settings.COLOR_PANEL, shown)
            pygame.draw.rect(world, settings.COLOR_DIM, shown, 1)

        for plat in self.generator.platforms_near(camera_x, camera_x + width):
            if not plat.solid:
                continue
            shown = plat.rect.move(-camera_x + plat.jitter(), 0)
            pygame.draw.rect(world, plat.color(), shown)

        pulse = 70 + int(40 * math.sin(self.elapsed * 5))
        for portal in self.generator.portals:
            shown = portal.rect.move(-camera_x, 0)
            if shown.right < 0 or shown.left > width:
                continue
            self.portal_band.set_alpha(40 if portal.used else pulse)
            world.blit(self.portal_band, (shown.x, 0))

        for chain in self.generator.chains_near(camera_x - 160, camera_x + width + 160):
            anchor = (chain.anchor_x - camera_x, chain.anchor_y)
            if self.player.chain is chain:
                hand = self.player.rect.midtop
                end = (hand[0] - camera_x, hand[1])
            else:
                end = (chain.anchor_x - camera_x, chain.anchor_y + chain.length)
            pygame.draw.line(world, settings.COLOR_CHAIN, anchor, end, 2)
            pygame.draw.circle(world, settings.COLOR_CHAIN, end, 4)
            anchor_block = pygame.Rect(anchor[0] - 4, anchor[1] - 4, 8, 8)
            pygame.draw.rect(world, settings.COLOR_DIM, anchor_block)

        for barrier in self.generator.barriers:
            if barrier.open:
                continue
            shown = barrier.rect.move(-camera_x, 0)
            if shown.right < 0 or shown.left > width:
                continue
            pygame.draw.rect(world, settings.COLOR_PANEL, shown)
            pygame.draw.rect(world, settings.COLOR_ERROR, shown, 2)

        for chest in self.generator.chests:
            if chest.hidden:
                continue
            shown = chest.rect.move(-camera_x, 0)
            if shown.right < 0 or shown.left > width:
                continue
            body = settings.COLOR_DIM if chest.opened else settings.COLOR_CHEST
            pygame.draw.rect(world, body, shown)
            pygame.draw.rect(world, settings.COLOR_TEXT, shown, 1)

        for mob in self.generator.mobs:
            shown = mob.rect.move(-camera_x, 0)
            if shown.right < 0 or shown.left > width:
                continue
            pygame.draw.rect(world, mob.kind.color, shown)

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
            pygame.draw.rect(world, color, player.rect.move(-camera_x, 0))

        if self.inverted:
            surface.blit(pygame.transform.flip(world, False, True), (0, 0))
        else:
            surface.blit(world, (0, 0))

        state = self.manager.state
        for chest in self.generator.chests:
            if chest.hidden:
                continue
            shown = self.to_screen(chest.rect.move(-camera_x, 0))
            if shown.right < 0 or shown.left > width:
                continue
            text = None
            if chest.opened:
                text = chest.item
            elif settings.CHEST_LABELS_VISIBLE and state.phase_index < len(self.phases):
                text = self.level.item_for(state.phase_index, chest.choice)
            if text:
                label = self.font.render(text, False, settings.COLOR_TEXT)
                surface.blit(label, (shown.centerx - label.get_width() // 2, shown.top - 12))

        if self.chest_in_reach() is not None:
            hint = self.font.render("E abrir", False, settings.COLOR_HIGHLIGHT)
            shown = self.to_screen(player.rect.move(-camera_x, 0))
            surface.blit(hint, (shown.centerx - hint.get_width() // 2, shown.top - 14))

        if player.hanging:
            ratio = min(1.0, player.peak / settings.SWING_MAX_ANGLE)
            bar = pygame.Rect(0, 0, 80, 6)
            bar.midbottom = (settings.INTERNAL_WIDTH // 2, settings.INTERNAL_HEIGHT - 22)
            pygame.draw.rect(surface, settings.COLOR_PANEL, bar)
            fill = pygame.Rect(bar.x, bar.y, round(bar.width * ratio), bar.height)
            ready = ratio >= settings.SWING_READY
            fill_color = settings.COLOR_SUCCESS if ready else settings.COLOR_HIGHLIGHT
            pygame.draw.rect(surface, fill_color, fill)
            pygame.draw.rect(surface, settings.COLOR_DIM, bar, 1)
            hang_label = self.font.render(
                "SETAS balançam   ESPAÇO solta", False, settings.COLOR_HIGHLIGHT
            )
            hang_x = settings.INTERNAL_WIDTH // 2 - hang_label.get_width() // 2
            surface.blit(hang_label, (hang_x, settings.INTERNAL_HEIGHT - 18))

        if self.flash > 0:
            self.flash_surface.set_alpha(int(220 * self.flash / settings.PORTAL_FLASH))
            surface.blit(self.flash_surface, (0, 0))

        progress_text = (
            f"{self.phase.name}   baús {state.phase_index}/{len(self.phases)}"
        )
        surface.blit(self.font.render(progress_text, False, settings.COLOR_TEXT), (4, 2))
        if settings.DEBUG_HUD:
            chunk = self.generator.chunk_at(player.rect.centerx)
            debug = f"{self.phase_time:.1f} s   bloco {chunk.name}   inv {int(self.inverted)}"
            surface.blit(self.font.render(debug, False, settings.COLOR_DIM), (4, 16))
            help_text = "ESPAÇO pular  SHIFT dash  E abrir  R reiniciar  BACKSPACE sair"
            surface.blit(self.font.render(help_text, False, settings.COLOR_DIM), (4, 28))
        draw_lives(surface, state.lives, settings.MAX_ATTEMPTS)
        draw_score(surface, self.font, state)

        if self.fork_prompt_visible():
            draw_alert(surface, self.alert_font, self.prompt_font, state.messages["fork_prompt"])

        self.box.draw(surface)