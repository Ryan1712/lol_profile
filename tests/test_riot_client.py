import httpx
import pytest

from src import riot_client as rc


def _client(handler):
    return rc.RiotClient(api_key="TESTKEY", transport=httpx.MockTransport(handler),
                         sleep_fn=lambda s: None)


def test_account_by_riot_id_ok():
    def handler(request):
        assert "/riot/account/v1/accounts/by-riot-id/" in request.url.path
        assert request.headers["X-Riot-Token"] == "TESTKEY"
        return httpx.Response(200, json={"puuid": "P1", "gameName": "A", "tagLine": "VN2"})
    acc = _client(handler).get_account_by_riot_id("A", "VN2")
    assert acc["puuid"] == "P1"


def test_ranked_match_ids_uses_type_ranked():
    seen = {}
    def handler(request):
        seen["type"] = request.url.params.get("type")
        seen["count"] = request.url.params.get("count")
        return httpx.Response(200, json=["VN2_1", "VN2_2"])
    ids = _client(handler).get_ranked_match_ids("P1", count=30)
    assert ids == ["VN2_1", "VN2_2"]
    assert seen["type"] == "ranked"
    assert seen["count"] == "30"


def test_auth_error_on_403():
    def handler(request):
        return httpx.Response(403, json={})
    with pytest.raises(rc.AuthError):
        _client(handler).get_account_by_riot_id("A", "VN2")


def test_not_found_on_404():
    def handler(request):
        return httpx.Response(404, json={})
    with pytest.raises(rc.NotFoundError):
        _client(handler).get_account_by_riot_id("Ghost", "VN2")


def test_retry_on_429_then_success():
    calls = {"n": 0}
    def handler(request):
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(429, headers={"Retry-After": "0"}, json={})
        return httpx.Response(200, json={"puuid": "P1"})
    acc = _client(handler).get_account_by_riot_id("A", "VN2")
    assert acc["puuid"] == "P1"
    assert calls["n"] == 2


def test_network_error_wraps_connect_failure():
    def handler(request):
        raise httpx.ConnectError("reset")
    with pytest.raises(rc.NetworkError):
        _client(handler).get_account_by_riot_id("A", "VN2")
