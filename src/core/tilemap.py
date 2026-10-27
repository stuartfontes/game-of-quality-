import pygame

from src.core import settings


class TileMap:
    def __init__(self, filename):
        with open(settings.DATA_DIR / filename, encoding="utf-8") as f:
            rows = [line.rstrip("\r\n") for line in f if line.strip()]

        self.rows = len(rows)
        self.cols = max(len(row) for row in rows)
        size = settings.TILE_SIZE
        self.width = self.cols * size
        self.height = self.rows * size

        self.solids = []
        self.spawn = (0, 0)
        for r, row in enumerate(rows):
            if len(row) < self.cols:
                print(f"[tilemap] linha {r} tem {len(row)} colunas, esperado {self.cols}")
                row = row.ljust(self.cols, ".")
            for c, char in enumerate(row):
                if char == "#":
                    self.solids.append(pygame.Rect(c * size, r * size, size, size))
                elif char == "P":
                    self.spawn = (c * size, r * size)

    def draw(self, surface, camera_x=0):
        view = pygame.Rect(
            camera_x, 0, settings.INTERNAL_WIDTH, settings.INTERNAL_HEIGHT
        )
        for tile in self.solids:
            if tile.colliderect(view):
                shown = tile.move(-camera_x, 0)
                pygame.draw.rect(surface, settings.COLOR_PANEL, shown)
                pygame.draw.rect(surface, settings.COLOR_DIM, shown, 1)