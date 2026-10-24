import json

from src.core import settings


def load_runs():
    if not settings.RESULTS_FILE.exists():
        return []

    runs = []
    with open(settings.RESULTS_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                runs.append(json.loads(line))
            except json.JSONDecodeError:
                print(f"[storage] linha inválida ignorada: {line[:60]}")
    return runs


def save_run(run):
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(settings.RESULTS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(run, ensure_ascii=False) + "\n")


def top_runs(game_id, limit=5):
    wins = [
        r for r in load_runs()
        if r.get("game_id") == game_id and r.get("result") == "won"
    ]
    wins.sort(key=lambda r: (-r.get("lives_left", 0), r.get("duration", 0)))
    return wins[:limit]