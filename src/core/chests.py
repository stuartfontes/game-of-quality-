import pygame

from src.core import settings


class Chest:
    def __init__(self, choice, x, bottom, fork_id):
        self.choice = choice
        self.fork_id = fork_id
        self.rect = pygame.Rect(0, 0, settings.CHEST_WIDTH, settings.CHEST_HEIGHT)
        self.rect.midbottom = (x, bottom)
        self.opened = False
        self.hidden = False
        self.item = None


class Barrier:
    def __init__(self, rect, fork_id):
        self.rect = rect
        self.fork_id = fork_id
        self.open = False