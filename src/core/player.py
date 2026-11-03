import math

import pygame

from src.core import settings


class Player:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, settings.PLAYER_WIDTH, settings.PLAYER_HEIGHT)
        self.pos_x = float(x)
        self.pos_y = float(y)
        self.vel_x = 0.0
        self.vel_y = 0.0
        self.launch_vx = 0.0
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
        self.chain = None
        self.angle = 0.0
        self.ang_vel = 0.0
        self.peak = 0.0
        self.released = None
        self.grab_lock = 0.0

    @property
    def dashing(self):
        return self.dash_time > 0

    @property
    def hanging(self):
        return self.chain is not None

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

    def grab(self, chain):
        dx = self.rect.centerx - chain.anchor_x
        dy = self.rect.centery - chain.anchor_y
        angle = math.atan2(dx, max(dy, 1.0))
        limit = settings.SWING_MAX_ANGLE
        self.angle = max(-limit, min(limit, angle))
        tangent = self.vel_x * math.cos(self.angle) - self.vel_y * math.sin(self.angle)
        cap = settings.SWING_MAX_OMEGA
        omega = tangent / chain.length * settings.SWING_GRAB_SCALE
        self.ang_vel = max(-cap, min(cap, omega))

        rate = settings.SWING_GRAVITY / chain.length
        cos_peak = math.cos(self.angle) - (self.ang_vel ** 2) / (2 * rate)
        if cos_peak <= math.cos(limit):
            energy_peak = limit
        else:
            energy_peak = math.acos(min(1.0, cos_peak))
        self.peak = max(abs(self.angle), energy_peak)

        self.chain = chain
        self.dash_time = 0.0
        self.vel_y = 0.0
        self.launch_vx = 0.0
        self.coyote_timer = 0.0
        self.jump_buffer = 0.0
        self.on_ground = False
        self.standing_on = None

    def release(self):
        chain = self.chain
        speed = chain.length * self.ang_vel
        scale = settings.SWING_RELEASE_SCALE
        self.launch_vx = speed * math.cos(self.angle) * scale
        self.vel_y = -speed * math.sin(self.angle) * scale - settings.SWING_RELEASE_BOOST
        self.released = chain
        self.grab_lock = settings.CHAIN_REGRAB_LOCK
        self.chain = None
        self.on_ground = False
        self.standing_on = None
        self.coyote_timer = 0.0
        self.jump_buffer = 0.0
        self.air_jump = False
        self.dash_available = True

    def update_hang(self, dt, inputs):
        chain = self.chain
        direction = int(inputs.held("right")) - int(inputs.held("left"))
        if direction:
            self.facing = direction

        accel = -settings.SWING_GRAVITY / chain.length * math.sin(self.angle)
        accel -= settings.SWING_DAMPING * self.ang_vel
        accel += direction * settings.SWING_PUMP
        self.ang_vel += accel * dt
        cap = settings.SWING_MAX_OMEGA
        self.ang_vel = max(-cap, min(cap, self.ang_vel))
        self.angle += self.ang_vel * dt

        limit = settings.SWING_MAX_ANGLE
        if self.angle > limit:
            self.angle = limit
            self.ang_vel = min(self.ang_vel, 0.0)
        elif self.angle < -limit:
            self.angle = -limit
            self.ang_vel = max(self.ang_vel, 0.0)

        self.peak = max(abs(self.angle), self.peak - 0.25 * dt)

        tip_x = chain.anchor_x + chain.length * math.sin(self.angle)
        tip_y = chain.anchor_y + chain.length * math.cos(self.angle)
        self.rect.midtop = (round(tip_x), round(tip_y))
        self.pos_x = float(self.rect.x)
        self.pos_y = float(self.rect.y)
        self.vel_x = 0.0
        self.vel_y = 0.0

        if inputs.pressed("jump"):
            self.release()

    def try_grab(self, chains):
        cx, cy = self.rect.center
        radius = settings.CHAIN_GRAB_RADIUS
        for chain in chains:
            if chain is self.released and self.grab_lock > 0:
                continue
            tx, ty = chain.tip
            if (cx - tx) ** 2 + (cy - ty) ** 2 <= radius * radius:
                self.grab(chain)
                return

    def update(self, dt, inputs, solids, platforms=(), chains=()):
        self.invuln_time = max(0.0, self.invuln_time - dt)
        self.grab_lock = max(0.0, self.grab_lock - dt)
        self.dash_cooldown = max(0.0, self.dash_cooldown - dt)

        if self.chain is not None:
            self.update_hang(dt, inputs)
            return

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

        if inputs.pressed("dash") and self.can_dash:
            self.dash_time = settings.DASH_DURATION
            self.dash_dir = direction or self.facing
            self.dash_available = False
            self.launch_vx = 0.0

        if self.dashing:
            self.dash_time -= dt
            vel_x = self.dash_dir * settings.DASH_SPEED
            self.vel_y = 0.0
            if self.dash_time <= 0:
                self.end_dash()
        else:
            self.launch_vx *= max(0.0, 1.0 - settings.LAUNCH_DRAG * dt)
            vel_x = direction * settings.PLAYER_SPEED + self.launch_vx
            if self.jump_buffer > 0:
                if self.coyote_timer > 0:
                    self.start_jump()
                elif self.air_jump:
                    self.air_jump = False
                    self.start_jump()
            self.vel_y = min(
                self.vel_y + settings.GRAVITY * dt, settings.MAX_FALL_SPEED
            )
        self.vel_x = vel_x

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
                self.launch_vx = 0.0
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
            self.launch_vx = 0.0
        else:
            self.try_grab(chains)