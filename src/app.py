from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src import cache, config, roster, scout
from src import riot_client as rc


class RiotIdBody(BaseModel):
    raw_ingame: str


class RenameBody(BaseModel):
    name: str


def _team_by_id(data, team_id):
    for t in data["teams"]:
        if t["id"] == team_id:
            return t
    return None


def _is_total_network_failure(team, snapshot):
    """True when EVERY member with a valid Riot ID errored with 'network'.

    A per-member 'needs_riot_id' is not a network problem, so it's excluded
    from the check — a team where some members are unscanned but the
    reachable ones succeeded is not a network failure.
    """
    checked = [
        m for m in team["members"]
        if snapshot["members"].get(m["stt"], {}).get("error") != "needs_riot_id"
    ]
    if not checked:
        return False
    return all(
        snapshot["members"].get(m["stt"], {}).get("error") == "network"
        for m in checked
    )


def build_app(client_factory=lambda: rc.RiotClient()):
    app = FastAPI(title="LOL Scouting Tool")

    @app.get("/")
    def index():
        return FileResponse(config.ROOT / "web" / "index.html")

    @app.get("/api/teams")
    def list_teams():
        data = roster.ensure_roster()
        out = []
        for t in data["teams"]:
            snap = cache.load_snapshot(t["id"])
            out.append({
                "id": t["id"],
                "name": t["name"],
                "region": t["region"],
                "member_count": len(t["members"]),
                "refreshed_at": snap["refreshed_at"] if snap else None,
            })
        return {"teams": out}

    @app.get("/api/team/{team_id}")
    def get_team(team_id: str):
        data = roster.ensure_roster()
        team = _team_by_id(data, team_id)
        if not team:
            return JSONResponse({"error": "not_found"}, status_code=404)
        return {"team": team, "snapshot": cache.load_snapshot(team_id)}

    @app.post("/api/team/{team_id}/refresh")
    def refresh(team_id: str):
        data = roster.ensure_roster()
        team = _team_by_id(data, team_id)
        if not team:
            return JSONResponse({"error": "not_found"}, status_code=404)
        client = client_factory()
        try:
            snapshot = scout.refresh_team(client, team)
        except rc.AuthError:
            return {"error": "auth", "snapshot": cache.load_snapshot(team_id)}
        except rc.NetworkError:
            return {"error": "network", "snapshot": cache.load_snapshot(team_id)}
        except rc.RiotError:
            return {"error": "network", "snapshot": cache.load_snapshot(team_id)}
        finally:
            close = getattr(client, "close", None)
            if callable(close):
                close()
        if _is_total_network_failure(team, snapshot):
            return {"error": "network", "snapshot": cache.load_snapshot(team_id)}
        cache.save_snapshot(team_id, snapshot)
        return {"snapshot": snapshot}

    @app.post("/api/member/{stt}/riot-id")
    def edit_riot_id(stt: str, body: RiotIdBody):
        data = roster.ensure_roster()
        try:
            data = roster.update_member_riot_id(data, stt, body.raw_ingame)
        except KeyError:
            return JSONResponse({"error": "not_found"}, status_code=404)
        roster.save_roster(data)
        team = next((t for t in data["teams"] for m in t["members"] if m["stt"] == stt), None)
        return {"ok": True, "team": team}

    @app.post("/api/team/{team_id}/rename")
    def rename(team_id: str, body: RenameBody):
        data = roster.ensure_roster()
        try:
            data = roster.rename_team(data, team_id, body.name)
        except KeyError:
            return JSONResponse({"error": "not_found"}, status_code=404)
        roster.save_roster(data)
        return {"ok": True}

    # static mounts (đặt cuối để không nuốt /api)
    if (config.ROOT / "web").exists():
        app.mount("/web", StaticFiles(directory=config.ROOT / "web"), name="web")
    if config.ASSETS_DIR.exists():
        app.mount("/assets", StaticFiles(directory=config.ASSETS_DIR), name="assets")
    return app


app = build_app()
