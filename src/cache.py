import json

from src import config


def _match_path(match_id):
    return config.MATCH_CACHE_DIR / f"{match_id}.json"


def has_match(match_id):
    return _match_path(match_id).exists()


def get_match(match_id):
    p = _match_path(match_id)
    if not p.exists():
        return None
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def put_match(match_id, data):
    config.MATCH_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(_match_path(match_id), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


def _snapshot_path(team_id):
    return config.SNAPSHOT_DIR / f"{team_id}.json"


def save_snapshot(team_id, snapshot):
    config.SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    with open(_snapshot_path(team_id), "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)


def load_snapshot(team_id):
    p = _snapshot_path(team_id)
    if not p.exists():
        return None
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)
