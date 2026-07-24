from fastapi.testclient import TestClient

from src import app as appmod
from src import cache, roster
from src import riot_client as rc


class FakeClient:
    def get_account_by_riot_id(self, name, tag):
        return {"puuid": "P1"}

    def get_league_entries(self, puuid):
        return [{"queueType": "RANKED_SOLO_5x5", "tier": "GOLD", "rank": "I",
                 "leaguePoints": 50, "wins": 10, "losses": 5}]

    def get_ranked_match_ids(self, puuid, count=30):
        return ["VN2_1"]

    def get_match(self, mid):
        return {"info": {"queueId": 420, "gameCreation": 1,
                         "participants": [{"puuid": "P1", "championName": "Ahri",
                                           "kills": 5, "deaths": 1, "assists": 5, "win": True,
                                           "teamPosition": "MIDDLE"}]}}


class AuthErrorClient:
    def get_account_by_riot_id(self, name, tag):
        raise rc.AuthError("401: key sai hoặc hết hạn")


class NetworkErrorClient:
    def get_account_by_riot_id(self, name, tag):
        raise rc.NetworkError("connection reset")


def _seed_roster(tmp_path, monkeypatch):
    monkeypatch.setattr(roster.config, "ROSTER_PATH", tmp_path / "roster.json")
    monkeypatch.setattr(cache.config, "MATCH_CACHE_DIR", tmp_path / "m")
    monkeypatch.setattr(cache.config, "SNAPSHOT_DIR", tmp_path / "s")
    data = {
        "imported_at": "x", "source_excel": "x",
        "teams": [{"id": "t1", "name": "Alpha", "region": "Hà Nội",
                   "members": [{"stt": "1", "full_name": "A", "email": "a@x.com",
                                "raw_ingame": "A#VN2", "game_name": "A", "tag_line": "VN2",
                                "status": "ok"}]}],
    }
    roster.save_roster(data, tmp_path / "roster.json")


def _client(tmp_path, monkeypatch):
    _seed_roster(tmp_path, monkeypatch)
    application = appmod.build_app(client_factory=lambda: FakeClient())
    return TestClient(application)


def test_list_teams(tmp_path, monkeypatch):
    c = _client(tmp_path, monkeypatch)
    r = c.get("/api/teams")
    assert r.status_code == 200
    assert r.json()["teams"][0]["name"] == "Alpha"


def test_refresh_team(tmp_path, monkeypatch):
    c = _client(tmp_path, monkeypatch)
    r = c.post("/api/team/t1/refresh")
    assert r.status_code == 200
    snap = r.json()["snapshot"]
    assert snap["members"]["1"]["solo"]["tier"] == "GOLD"


def test_edit_riot_id(tmp_path, monkeypatch):
    c = _client(tmp_path, monkeypatch)
    r = c.post("/api/member/1/riot-id", json={"raw_ingame": "New#TAG"})
    assert r.status_code == 200
    r2 = c.get("/api/team/t1")
    m = r2.json()["team"]["members"][0]
    assert m["game_name"] == "New" and m["tag_line"] == "TAG"


def test_rename_team(tmp_path, monkeypatch):
    c = _client(tmp_path, monkeypatch)
    r = c.post("/api/team/t1/rename", json={"name": "Beta"})
    assert r.status_code == 200
    assert c.get("/api/team/t1").json()["team"]["name"] == "Beta"


def _seed_old_snapshot():
    cache.save_snapshot("t1", {
        "team_id": "t1", "team_name": "Alpha", "refreshed_at": "OLD",
        "members": {"1": {"solo": {"tier": "OLD_TIER"}}},
    })


def test_refresh_auth_error_preserves_snapshot(tmp_path, monkeypatch):
    _seed_roster(tmp_path, monkeypatch)
    _seed_old_snapshot()
    application = appmod.build_app(client_factory=lambda: AuthErrorClient())
    c = TestClient(application)
    r = c.post("/api/team/t1/refresh")
    assert r.status_code == 200
    body = r.json()
    assert body["error"] == "auth"
    assert body["snapshot"]["members"]["1"]["solo"]["tier"] == "OLD_TIER"
    on_disk = cache.load_snapshot("t1")
    assert on_disk["refreshed_at"] == "OLD"
    assert on_disk["members"]["1"]["solo"]["tier"] == "OLD_TIER"


def test_refresh_network_outage_preserves_snapshot(tmp_path, monkeypatch):
    _seed_roster(tmp_path, monkeypatch)
    _seed_old_snapshot()
    application = appmod.build_app(client_factory=lambda: NetworkErrorClient())
    c = TestClient(application)
    r = c.post("/api/team/t1/refresh")
    assert r.status_code == 200
    body = r.json()
    assert body["error"] == "network"
    assert body["snapshot"]["members"]["1"]["solo"]["tier"] == "OLD_TIER"
    on_disk = cache.load_snapshot("t1")
    assert on_disk["refreshed_at"] == "OLD"
    assert on_disk["members"]["1"]["solo"]["tier"] == "OLD_TIER"


def test_edit_riot_id_unknown_stt_returns_404(tmp_path, monkeypatch):
    c = _client(tmp_path, monkeypatch)
    r = c.post("/api/member/999/riot-id", json={"raw_ingame": "X#TAG"})
    assert r.status_code == 404
    assert r.json() == {"error": "not_found"}


def test_rename_unknown_team_returns_404(tmp_path, monkeypatch):
    c = _client(tmp_path, monkeypatch)
    r = c.post("/api/team/nope/rename", json={"name": "X"})
    assert r.status_code == 404
    assert r.json() == {"error": "not_found"}
