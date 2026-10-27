import json
import time
from datetime import datetime

from src.core import settings, storage


class GameState:
    def __init__(self):
        path = settings.DATA_DIR / "messages.json"
        with open(path, encoding="utf-8") as f:
            self.messages = json.load(f)

        self.game_id = None
        self.lives = settings.MAX_ATTEMPTS
        self.result = None
        self.kills = 0
        self.rings = 0
        self.play_time = 0.0
        self._started = time.monotonic()

    def start_run(self, game_id):
        self.game_id = game_id
        self.lives = settings.MAX_ATTEMPTS
        self.result = None
        self.kills = 0
        self.rings = 0
        self.play_time = 0.0
        self._started = time.monotonic()

    @property
    def attempt(self):
        return min(settings.MAX_ATTEMPTS - self.lives + 1, settings.MAX_ATTEMPTS)

    @property
    def game_over(self):
        return self.result is not None

    @property
    def score(self):
        return (
            self.kills * settings.SCORE_KILL
            + self.rings * settings.SCORE_RING
            + int(self.play_time) * settings.SCORE_PER_SECOND
        )

    def add_kill(self):
        self.kills += 1

    def add_ring(self):
        self.rings += 1

    def add_time(self, dt):
        if not self.game_over:
            self.play_time += dt

    def score_text(self):
        return (
            f"Pontos: {self.score}\n"
            f"Inimigos {self.kills}  Argolas {self.rings}  Tempo {int(self.play_time)} s"
        )

    def lose_life(self):
        if self.game_over:
            return ""
        lost = self.messages["attempt_lost"]
        index = min(settings.MAX_ATTEMPTS - self.lives, len(lost) - 1)
        self.lives -= 1
        if self.lives <= 0:
            self._finish("lost")
        return lost[index]

    def win(self):
        if not self.game_over:
            self._finish("won")

    def _finish(self, result):
        self.result = result
        run = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "game_id": self.game_id,
            "result": result,
            "lives_left": max(self.lives, 0),
            "duration": round(time.monotonic() - self._started, 1),
            "score": self.score,
            "kills": self.kills,
            "rings": self.rings,
            "play_time": round(self.play_time, 1),
        }
        storage.save_run(run)