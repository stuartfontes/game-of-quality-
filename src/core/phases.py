import json

from src.core import settings


class Phase:
    def __init__(self, data):
        self.name = data["name"]
        self.kind = data["kind"]
        self.intro = data["intro"]
        self.group = data.get("group", "f1")
        self.duration = data.get("duration", 30)
        self.portals = data.get("portals", [])
        self.rings = data.get("rings", settings.FLIGHT_RINGS)
        self.free_camera = data.get("free_camera", False)


def load_phases():
    with open(settings.DATA_DIR / "phases.json", encoding="utf-8") as f:
        raw = json.load(f)
    return [Phase(item) for item in raw["phases"]]