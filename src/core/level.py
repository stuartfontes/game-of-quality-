import json

from src.core import settings

VALID_CHOICES = ("up", "straight", "down")


class Level:
    def __init__(self):
        path = settings.DATA_DIR / "level.json"
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        self.parkour_seconds = data["parkour_seconds"]
        self.correct_sequence = data["correct_sequence"]
        self._item_correct = data["placeholder_correct"]
        self._item_wrong = data["placeholder_wrong"]

        for choice in self.correct_sequence:
            if choice not in VALID_CHOICES:
                raise ValueError(f"Escolha inválida em level.json: {choice}")

    @property
    def fork_count(self):
        return len(self.correct_sequence)

    def is_correct(self, fork_index, choice):
        return self.correct_sequence[fork_index] == choice

    def item_for(self, fork_index, choice):
        return self._item_correct if self.is_correct(fork_index, choice) else self._item_wrong