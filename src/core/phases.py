import json

from src.core import settings


class Phase:
    def __init__(self, data):
        self.name = data["name"]
        self.group = data["group"]
        self.forks = data["forks"]
        self.intro = data["intro"]


def load_phases():
    with open(settings.DATA_DIR / "phases.json", encoding="utf-8") as f:
        raw = json.load(f)
    return [Phase(item) for item in raw["phases"]]