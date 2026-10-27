import random

import pygame

from src.core import settings
from src.core.chests import Barrier, Chest
from src.core.mobs import Mob, load_mob_kinds
from src.core.platforms import CrumblePlatform, MovingPlatform


class Chunk:
    def __init__(self, name, difficulty, group, rows):
        self.name = name
        self.difficulty = difficulty
        self.group = group
        self.rows = rows
        self.cols = len(rows[0])
        self.markers = []
        self.barriers = []
        self.platform_specs = []
        for r, row in enumerate(rows):
            for c, char in enumerate(row):
                if char in settings.CHEST_MARKERS:
                    self.markers.append((r, c, settings.CHEST_MARKERS[char]))
                elif char == settings.BARRIER_CHAR:
                    self.barriers.append((r, c))
            c = 0
            while c < len(row):
                char = row[c]
                if char in settings.PLATFORM_CHARS:
                    start = c
                    while c < len(row) and row[c] == char:
                        c += 1
                    kind = settings.PLATFORM_CHARS[char]
                    self.platform_specs.append((kind, r, start, c - start))
                else:
                    c += 1

    def build(self, offset_x):
        size = settings.TILE_SIZE
        tiles = []
        for r, row in enumerate(self.rows):
            for c, char in enumerate(row):
                if char == "#":
                    tiles.append(
                        pygame.Rect(offset_x + c * size, r * size, size, size)
                    )
        return tiles

    def walker_spots(self):
        last = len(self.rows) - 1
        spots = []
        for c in range(4, self.cols - 2):
            ok = True
            for cc in (c - 1, c, c + 1):
                if self.rows[last][cc] != "#":
                    ok = False
                if any(self.rows[r][cc] == "#" for r in range(last - 3, last)):
                    ok = False
            if ok:
                spots.append(c)
        return spots


class PlacedChunk:
    def __init__(self, name, start, end, tiles):
        self.name = name
        self.start = start
        self.end = end
        self.tiles = tiles
        self.fork_id = None
        self.resolved = False


def load_chunks(filename):
    with open(settings.DATA_DIR / filename, encoding="utf-8") as f:
        lines = [line.rstrip("\r\n") for line in f]

    raw = []
    current = None
    for line in lines:
        if line.startswith("@"):
            parts = line[1:].split()
            group = parts[2] if len(parts) > 2 else "f1"
            current = {
                "name": parts[0],
                "difficulty": int(parts[1]),
                "group": group,
                "rows": [],
            }
            raw.append(current)
        elif line.strip() and current is not None:
            current["rows"].append(line.strip())

    chunks = []
    for item in raw:
        rows = item["rows"]
        if len(rows) != settings.MAP_ROWS:
            raise ValueError(
                f"O bloco '{item['name']}' tem {len(rows)} linhas, esperado {settings.MAP_ROWS}"
            )
        width = max(len(row) for row in rows)
        for r, row in enumerate(rows):
            if len(row) < width:
                print(f"[chunks] bloco '{item['name']}' linha {r} completada com vazio")
        rows = [row.ljust(width, ".") for row in rows]
        chunks.append(Chunk(item["name"], item["difficulty"], item["group"], rows))
    return chunks


class LevelGenerator:
    def __init__(self, filename="chunks.txt"):
        self.library = load_chunks(filename)
        self.mob_kinds = load_mob_kinds()
        intros = [c for c in self.library if c.name == settings.INTRO_CHUNK]
        if not intros:
            raise ValueError(f"Bloco inicial '{settings.INTRO_CHUNK}' não existe")
        self.intro = intros[0]
        forks = [c for c in self.library if c.name == settings.FORK_CHUNK]
        self.fork_chunk = forks[0] if forks else None
        self.group = "f1"
        self.pool = []
        self.queue = []
        self.chunks = []
        self.mobs = []
        self.chests = []
        self.barriers = []
        self.platforms = []
        self.width = 0
        self.last = None
        self.fork_requested = False
        self.pending_forks = 0
        self.fork_counter = 0
        self.reset()

    @property
    def fork_busy(self):
        return self.fork_requested or self.pending_forks > 0

    def _rebuild_pool(self):
        self.pool = [
            c for c in self.library
            if c.group == self.group
            and settings.DIFFICULTY_MIN <= c.difficulty <= settings.DIFFICULTY_MAX
        ]
        if not self.pool:
            raise ValueError(
                f"Nenhum bloco do grupo '{self.group}' na faixa de dificuldade configurada"
            )

    def reset(self, group="f1"):
        self.group = group
        self._rebuild_pool()
        self.queue = []
        self.chunks = []
        self.mobs = []
        self.chests = []
        self.barriers = []
        self.platforms = []
        self.width = 0
        self.last = None
        self.fork_requested = False
        self.pending_forks = 0
        self.fork_counter = 0
        self._append(self.intro, spawn_mobs=False)

    def set_group(self, group):
        self.group = group
        self._rebuild_pool()
        self.queue.append(self.intro)

    def request_fork(self):
        if self.fork_chunk is not None and not self.fork_busy:
            self.fork_requested = True

    def resolve_fork(self, fork_id, opened):
        for chest in self.chests:
            if chest.fork_id == fork_id and chest is not opened:
                chest.hidden = True
        for barrier in self.barriers:
            if barrier.fork_id == fork_id:
                barrier.open = True
        for placed in self.chunks:
            if placed.fork_id == fork_id:
                placed.resolved = True
        self.pending_forks = max(0, self.pending_forks - 1)

    def pending_fork(self):
        for placed in self.chunks:
            if placed.fork_id is not None and not placed.resolved:
                return placed
        return None

    def _append(self, chunk, spawn_mobs=True):
        size = settings.TILE_SIZE
        start = self.width
        end = start + chunk.cols * size
        placed = PlacedChunk(chunk.name, start, end, chunk.build(start))
        self.chunks.append(placed)
        self.width = end
        self.last = chunk

        for kind, row, col, length in chunk.platform_specs:
            x = start + col * size
            y = row * size
            width = length * size
            if kind == "moving":
                self.platforms.append(MovingPlatform(x, y, width))
            else:
                self.platforms.append(CrumblePlatform(x, y, width))

        if chunk.markers:
            fork_id = self.fork_counter
            self.fork_counter += 1
            self.pending_forks += 1
            placed.fork_id = fork_id
            for row, col, choice in chunk.markers:
                x = start + col * size + size // 2
                bottom = (row + 1) * size
                self.chests.append(Chest(choice, x, bottom, fork_id))
            for row, col in chunk.barriers:
                x = start + col * size
                if row == 0:
                    rect = pygame.Rect(
                        x, -settings.BARRIER_EXTRA, size, settings.BARRIER_EXTRA + size
                    )
                else:
                    rect = pygame.Rect(x, row * size, size, size)
                self.barriers.append(Barrier(rect, fork_id))
        elif spawn_mobs:
            self._spawn_mobs(chunk, start)

    def _spawn_mobs(self, chunk, start):
        size = settings.TILE_SIZE
        floor_y = (settings.MAP_ROWS - 1) * size
        spots = chunk.walker_spots()
        count = random.randint(settings.MOBS_PER_CHUNK_MIN, settings.MOBS_PER_CHUNK_MAX)
        weights = [kind.weight for kind in self.mob_kinds]
        for _ in range(count):
            kind = random.choices(self.mob_kinds, weights=weights)[0]
            if kind.flying:
                col = random.randint(4, chunk.cols - 3)
                y = random.randint(settings.FLYER_MIN_Y, settings.FLYER_MAX_Y)
                self.mobs.append(Mob(kind, start + col * size + size // 2, y))
            elif spots:
                col = random.choice(spots)
                spots = [s for s in spots if abs(s - col) > 2]
                self.mobs.append(Mob(kind, start + col * size + size // 2, floor_y))

    def _pick(self):
        if self.fork_requested and self.fork_chunk is not None:
            self.fork_requested = False
            return self.fork_chunk
        if self.queue:
            return self.queue.pop(0)
        options = [c for c in self.pool if c is not self.last] or self.pool
        return random.choice(options)

    def ensure(self, x):
        while self.width < x + settings.GENERATION_LOOKAHEAD:
            self._append(self._pick())

    def tiles_near(self, x_left, x_right):
        tiles = []
        for placed in self.chunks:
            if placed.end >= x_left and placed.start <= x_right:
                tiles.extend(placed.tiles)
        return tiles

    def solids_near(self, x_left, x_right):
        solids = self.tiles_near(x_left, x_right)
        for barrier in self.barriers:
            if barrier.open:
                continue
            if barrier.rect.right >= x_left and barrier.rect.left <= x_right:
                solids.append(barrier.rect)
        return solids

    def platforms_near(self, x_left, x_right):
        return [
            p for p in self.platforms
            if p.rect.right >= x_left and p.rect.left <= x_right
        ]

    def update_platforms(self, dt, player, camera_x):
        near_left = camera_x - 200
        near_right = camera_x + settings.INTERNAL_WIDTH + 400
        for plat in self.platforms:
            if plat.rect.right < near_left or plat.rect.left > near_right:
                continue
            plat.update(dt, player.standing_on is plat)

    def chunk_at(self, x):
        for placed in reversed(self.chunks):
            if placed.start <= x:
                return placed
        return self.chunks[0]

    def update_mobs(self, dt, camera_x):
        for mob in self.mobs:
            solids = []
            if mob.active and mob.alive and not mob.kind.flying:
                solids = self.solids_near(mob.rect.left - 48, mob.rect.right + 48)
            mob.update(dt, solids, camera_x)
        self.mobs = [mob for mob in self.mobs if not mob.removed]