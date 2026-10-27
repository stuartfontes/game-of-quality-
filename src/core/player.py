import pygame

from src.core import settings


class Player:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, settings.PLAYER_WIDTH, settings.PLAYER_HEIGHT)
        self.pos_x = float(x)
        self.pos_y = float(y)
        self.vel_y = 0.0
        self.on_ground = False
        self.standing_on = None
        self.coyote_timer = 0.0
        self.jump_buffer = 0.0
        self.air_jump = False
        self.facing = 1
        self.dash_time = 0.0
        self.dash_cooldown = 0.0
        self.dash_dir = 1
        self.dash_available = True
        self.invuln_time = 0.0

    @property
    def dashing(self):
        return self.dash_time > 0

    @property
    def can_dash(self):
        return self.dash_available and self.dash_cooldown <= 0 and not self.dashing

    @property
    def invulnerable(self):
        return self.dashing or self.invuln_time > 0

    def end_dash(self):
        self.dash_time = 0.0
        self.dash_cooldown = settings.DASH_COOLDOWN
        self.invuln_time = max(self.invuln_time, settings.DASH_GRACE)

    def start_jump(self):
        self.vel_y = -settings.JUMP_SPEED
        self.on_ground = False
        self.standing_on = None
        self.coyote_timer = 0.0
        self.jump_buffer = 0.0

    def bounce(self, ground_y):
        self.rect.bottom = min(self.rect.bottom, ground_y)
        self.pos_y = float(self.rect.y)
        self.vel_y = -settings.STOMP_BOUNCE
        self.on_ground = False
        self.standing_on = None
        self.coyote_timer = 0.0
        self.air_jump = True
        self.dash_available = True

    def clamp_left(self, x):
        if self.rect.left < x:
            self.rect.left = x
            self.pos_x = float(self.rect.x)

    def update(self, dt, inputs, solids, platforms=()):
        self.invuln_time = max(0.0, self.invuln_time - dt)

        if self.on_ground:
            self.coyote_timer = settings.COYOTE_TIME
            self.air_jump = False
        else:
            self.coyote_timer = max(0.0, self.coyote_timer - dt)

        if inputs.pressed("jump"):
            self.jump_buffer = settings.JUMP_BUFFER
        else:
            self.jump_buffer = max(0.0, self.jump_buffer - dt)

        direction = int(inputs.held("right")) - int(inputs.held("left"))
        if direction:
            self.facing = direction

        self.dash_cooldown = max(0.0, self.dash_cooldown - dt)

        if inputs.pressed("dash") and self.can_dash:
            self.dash_time = settings.DASH_DURATION
            self.dash_dir = direction or self.facing
            self.dash_available = False

        if self.dashing:
            self.dash_time -= dt
            vel_x = self.dash_dir * settings.DASH_SPEED
            self.vel_y = 0.0
            if self.dash_time <= 0:
                self.end_dash()
        else:
            vel_x = direction * settings.PLAYER_SPEED
            if self.jump_buffer > 0:
                if self.coyote_timer > 0:
                    self.start_jump()
                elif self.air_jump:
                    self.air_jump = False
                    self.start_jump()
            self.vel_y = min(
                self.vel_y + settings.GRAVITY * dt, settings.MAX_FALL_SPEED
            )

        carry = self.standing_on.dx if self.standing_on is not None else 0
        move_x = vel_x * dt + carry
        self.pos_x += move_x
        self.rect.x = round(self.pos_x)
        for tile in solids:
            if self.rect.colliderect(tile):
                if move_x > 0:
                    self.rect.right = tile.left
                elif move_x < 0:
                    self.rect.left = tile.right
                self.pos_x = float(self.rect.x)
                if self.dashing:
                    self.end_dash()

        old_bottom = self.rect.bottom
        self.pos_y += self.vel_y * dt
        self.rect.y = round(self.pos_y)
        for tile in solids:
            if self.rect.colliderect(tile):
                if self.vel_y > 0:
                    self.rect.bottom = tile.top
                elif self.vel_y < 0:
                    self.rect.top = tile.bottom
                self.vel_y = 0.0
                self.pos_y = float(self.rect.y)

        if self.vel_y >= 0:
            for plat in platforms:
                if not plat.solid:
                    continue
                if (
                    self.rect.colliderect(plat.rect)
                    and old_bottom <= plat.rect.top + settings.ONE_WAY_TOLERANCE
                ):
                    self.rect.bottom = plat.rect.top
                    self.pos_y = float(self.rect.y)
                    self.vel_y = 0.0

        probe = self.rect.move(0, 1)
        self.standing_on = None
        self.on_ground = any(probe.colliderect(tile) for tile in solids)
        if not self.on_ground and self.vel_y >= 0:
            for plat in platforms:
                if (
                    plat.solid
                    and probe.colliderect(plat.rect)
                    and self.rect.bottom <= plat.rect.top + settings.ONE_WAY_TOLERANCE
                ):
                    self.on_ground = True
                    self.standing_on = plat
                    break
        if self.on_ground and self.vel_y > 0:
            self.vel_y = 0.0
            self.pos_y = float(self.rect.y)
        if self.on_ground:
            self.dash_available = True