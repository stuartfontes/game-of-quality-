import json
import math
import random

import pygame

from src.core import settings


class MobKind:
    def __init__(self, name, data):
        self.name = name
        self.width = data["width"]
        self.height = data["height"]
        self.speed = data["speed"]
        self.hp = data["hp"]
        self.stompable = data["stompable"]
        self.flying = data["flying"]
        self.weight = data["weight"]
        self.color = tuple(data["color"])


def load_mob_kinds():
    with open(settings.DATA_DIR / "mobs.json", encoding="utf-8") as f:
        raw = json.load(f)
    return [MobKind(name, data) for name, data in raw.items()]


class Mob:
    def __init__(self, kind, x, y):
        self.kind = kind
        self.hp = kind.hp
        self.rect = pygame.Rect(0, 0, kind.width, kind.height)
        if kind.flying:
            self.rect.center = (x, y)
        else:
            self.rect.midbottom = (x, y)
        self.pos_x = float(self.rect.x)
        self.pos_y = float(self.rect.y)
        self.base_y = float(self.rect.y)
        self.dir = -1
        self.vel_y = 0.0
        self.active = False
        self.dying = False
        self.removed = False
        self.hurt_time = 0.0
        self.phase = random.uniform(0, math.tau)

    @property
    def alive(self):
        return not self.dying and not self.removed

    def hit(self):
        self.hp -= 1
        self.hurt_time = settings.MOB_HURT_TIME
        if self.hp <= 0:
            self.dying = True
            self.vel_y = -settings.MOB_DEATH_POP
            return True
        bottom = self.rect.bottom
        self.rect.height = max(4, round(self.kind.height * self.hp / self.kind.hp))
        self.rect.bottom = bottom
        self.pos_y = float(self.rect.y)
        return False

    def update(self, dt, solids, camera_x):
        if self.dying:
            self.vel_y += settings.GRAVITY * dt
            self.pos_y += self.vel_y * dt
            self.rect.y = round(self.pos_y)
            if self.rect.top > settings.INTERNAL_HEIGHT + 40:
                self.removed = True
            return

        if not self.active:
            limit = settings.INTERNAL_WIDTH + settings.MOB_ACTIVATION_MARGIN
            if self.rect.left - camera_x < limit:
                self.active = True
            else:
                return

        if self.rect.right < camera_x - 96:
            self.removed = True
            return

        self.hurt_time = max(0.0, self.hurt_time - dt)

        if self.kind.flying:
            self.pos_x -= self.kind.speed * dt
            self.phase += dt * settings.FLYER_WAVE_SPEED
            self.rect.x = round(self.pos_x)
            wave = math.sin(self.phase) * settings.FLYER_WAVE_AMPLITUDE
            self.rect.y = round(self.base_y + wave)
            return

        self.pos_x += self.dir * self.kind.speed * dt
        self.rect.x = round(self.pos_x)
        for tile in solids:
            if self.rect.colliderect(tile):
                if self.dir > 0:
                    self.rect.right = tile.left
                else:
                    self.rect.left = tile.right
                self.pos_x = float(self.rect.x)
                self.dir *= -1

        self.vel_y = min(self.vel_y + settings.GRAVITY * dt, settings.MAX_FALL_SPEED)
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

        probe = self.rect.move(0, 1)
        grounded = any(probe.colliderect(tile) for tile in solids)
        if grounded and self.vel_y > 0:
            self.vel_y = 0.0
            self.pos_y = float(self.rect.y)
        if grounded:
            edge_x = self.rect.right + 1 if self.dir > 0 else self.rect.left - 2
            edge = pygame.Rect(edge_x, self.rect.bottom + 1, 1, 1)
            if not any(edge.colliderect(tile) for tile in solids):
                self.dir *= -1