import json

from src.core import settings


class GameState:
    def __init__(self):
        path = settings.DATA_DIR / "messages.json"
        with open(path, encoding="utf-8") as f:
            self.messages = json.load(f)

        self.game_id = None
        self.lives = settings.MAX_ATTEMPTS
        self.result = None  # None (em andamento), "won" ou "lost"

    def start_run(self, game_id):
        """Começa uma partida nova: devolve as vidas e limpa o resultado."""
        self.game_id = game_id
        self.lives = settings.MAX_ATTEMPTS
        self.result = None

    @property
    def attempt(self):
        """Número da tentativa atual (1 a MAX_ATTEMPTS)."""
        return min(settings.MAX_ATTEMPTS - self.lives + 1, settings.MAX_ATTEMPTS)

    @property
    def game_over(self):
        return self.result is not None

    def lose_life(self):
        """Perde uma vida e devolve a mensagem da tentativa perdida."""
        if self.game_over:
            return ""
        lost = self.messages["attempt_lost"]
        index = min(settings.MAX_ATTEMPTS - self.lives, len(lost) - 1)
        self.lives -= 1
        if self.lives <= 0:
            self.result = "lost"
        return lost[index]

    def win(self):
        if not self.game_over:
            self.result = "won"