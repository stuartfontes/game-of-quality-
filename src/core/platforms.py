import random

import pygame

from src.core import settings


class MovingPlatform:
    def __init__(self, x, y, width):
        self.rect = pygame.Rect(x, y, width, settings.PLATFORM_THICKNESS)
        half = settings.MOVING_RANGE_TILES * settings.TILE_SIZE / 2
        self.min_x = x - half
        self.max_x = x + half
        self.pos_x = random.uniform(self.min_x, self.max_x)
        self.dir = random.choice((-1, 1))
        self.dx = 0
        self.rect.x = round(self.pos_x)

    @property
    def solid(self):
        return True

    def update(self, dt, standing):
        old = self.rect.x
        self.pos_x += self.dir * settings.MOVING_SPEED * dt
        if self.pos_x >= self.max_x:
            self.pos_x = self.max_x
            self.dir = -1
        elif self.pos_x <= self.min_x:
            self.pos_x = self.min_x
            self.dir = 1
        self.rect.x = round(self.pos_x)
        self.dx = self.rect.x - old

    def color(self):
        return settings.COLOR_MOVING

    def jitter(self):
        return 0


class CrumblePlatform:
    def __init__(self, x, y, width):
        self.rect = pygame.Rect(x, y, width, settings.PLATFORM_THICKNESS)
        self.dx = 0
        self.stand_time = 0.0
        self.broken = False
        self.respawn_timer = 0.0

    @property
    def solid(self):
        return not self.broken

    def update(self, dt, standing):
        if self.broken:
            self.respawn_timer -= dt
            if self.respawn_timer <= 0:
                self.broken = False
                self.stand_time = 0.0
            return
        if standing:
            self.stand_time += dt
            if self.stand_time >= settings.CRUMBLE_TIME:
                self.broken = True
                self.respawn_timer = settings.CRUMBLE_RESPAWN
        else:
            self.stand_time = max(0.0, self.stand_time - dt * 0.5)

    def color(self):
        ratio = min(1.0, self.stand_time / settings.CRUMBLE_TIME)
        base = settings.COLOR_CRUMBLE
        warn = settings.COLOR_ERROR
        return tuple(int(base[i] + (warn[i] - base[i]) * ratio) for i in range(3))

    def jitter(self):
        if self.stand_time <= 0.5:
            return 0
        return 1 if int(self.stand_time * 30) % 2 == 0 else -1