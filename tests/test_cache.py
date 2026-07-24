from src import cache


def test_match_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(cache.config, "MATCH_CACHE_DIR", tmp_path / "m")
    assert cache.has_match("VN2_1") is False
    assert cache.get_match("VN2_1") is None
    cache.put_match("VN2_1", {"info": {"queueId": 420}})
    assert cache.has_match("VN2_1") is True
    assert cache.get_match("VN2_1")["info"]["queueId"] == 420


def test_snapshot_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(cache.config, "SNAPSHOT_DIR", tmp_path / "s")
    assert cache.load_snapshot("t1") is None
    cache.save_snapshot("t1", {"team_id": "t1", "members": {}})
    assert cache.load_snapshot("t1")["team_id"] == "t1"
