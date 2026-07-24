from src import scout
from src import riot_client as rc
from src import cache


class FakeClient:
    def __init__(self, matches):
        self._matches = matches
        self.match_calls = 0

    def get_account_by_riot_id(self, name, tag):
        if name == "Ghost":
            raise rc.NotFoundError("404")
        return {"puuid": "P1"}

    def get_league_entries(self, puuid):
        return [
            {"queueType": "RANKED_SOLO_5x5", "tier": "DIAMOND", "rank": "IV",
             "leaguePoints": 34, "wins": 123, "losses": 108},
        ]

    def get_ranked_match_ids(self, puuid, count=30):
        return list(self._matches.keys())

    def get_match(self, mid):
        self.match_calls += 1
        return self._matches[mid]


def _match(queue_id, champ):
    return {"info": {"queueId": queue_id, "gameCreation": 1,
                     "participants": [{"puuid": "P1", "championName": champ,
                                       "kills": 5, "deaths": 2, "assists": 7, "win": True,
                                       "teamPosition": "MIDDLE"}]}}


def test_refresh_member_ok(tmp_path, monkeypatch):
    monkeypatch.setattr(cache.config, "MATCH_CACHE_DIR", tmp_path / "m")
    client = FakeClient({"VN2_1": _match(420, "Ahri"), "VN2_2": _match(450, "Lux")})
    member = {"stt": "8", "game_name": "A", "tag_line": "VN2", "status": "ok"}
    res = scout.refresh_member(client, member)
    assert res["error"] is None
    assert res["solo"]["tier"] == "DIAMOND"
    assert res["matches_analyzed"] == 1          # ARAM 450 loại
    assert res["top_champions"][0]["champion"] == "Ahri"


def test_refresh_member_missing_tag():
    member = {"stt": "24", "game_name": "", "tag_line": "", "status": "needs_riot_id"}
    res = scout.refresh_member(FakeClient({}), member)
    assert res["error"] == "needs_riot_id"


def test_refresh_member_not_found():
    member = {"stt": "9", "game_name": "Ghost", "tag_line": "VN2", "status": "ok"}
    res = scout.refresh_member(FakeClient({}), member)
    assert res["error"] == "not_found"


def test_match_cache_avoids_refetch(tmp_path, monkeypatch):
    monkeypatch.setattr(cache.config, "MATCH_CACHE_DIR", tmp_path / "m")
    client = FakeClient({"VN2_1": _match(420, "Ahri")})
    member = {"stt": "8", "game_name": "A", "tag_line": "VN2", "status": "ok"}
    scout.refresh_member(client, member)
    scout.refresh_member(client, member)
    assert client.match_calls == 1               # lần 2 lấy từ cache
