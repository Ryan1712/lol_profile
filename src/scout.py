from datetime import datetime, timezone

from src import cache, config, stats
from src import riot_client as rc


def _pick_rank(entries, queue_type):
    for e in entries or []:
        if e.get("queueType") == queue_type:
            return {
                "tier": e.get("tier"),
                "rank": e.get("rank"),
                "lp": e.get("leaguePoints", 0),
                "wins": e.get("wins", 0),
                "losses": e.get("losses", 0),
            }
    return None


def _load_matches(client, match_ids):
    matches = []
    for mid in match_ids:
        data = cache.get_match(mid)
        if data is None:
            data = client.get_match(mid)
            cache.put_match(mid, data)
        matches.append(data)
    return matches


def refresh_member(client, member):
    riot_id = f"{member.get('game_name','')}#{member.get('tag_line','')}"
    base = {
        "riot_id": riot_id,
        "puuid": None,
        "solo": None,
        "flex": None,
        "lanes": [],
        "top_champions": [],
        "matches_analyzed": 0,
        "error": None,
    }
    if member.get("status") != "ok" or not member.get("game_name") or not member.get("tag_line"):
        base["error"] = "needs_riot_id"
        return base
    try:
        acc = client.get_account_by_riot_id(member["game_name"], member["tag_line"])
        puuid = acc["puuid"]
        base["puuid"] = puuid
        entries = client.get_league_entries(puuid)
        base["solo"] = _pick_rank(entries, "RANKED_SOLO_5x5")
        base["flex"] = _pick_rank(entries, "RANKED_FLEX_SR")
        match_ids = client.get_ranked_match_ids(puuid, count=config.MATCH_COUNT)
        matches = _load_matches(client, match_ids)
        summary = stats.summarize(matches, puuid)
        base["lanes"] = summary["lanes"]
        base["top_champions"] = summary["top_champions"]
        base["matches_analyzed"] = summary["matches_analyzed"]
    except rc.NotFoundError:
        base["error"] = "not_found"
    except (rc.NetworkError, rc.RateLimitError):
        base["error"] = "network"
    return base


def refresh_team(client, team):
    results = {}
    for member in team["members"]:
        results[member["stt"]] = refresh_member(client, member)
    return {
        "team_id": team["id"],
        "team_name": team["name"],
        "refreshed_at": datetime.now(timezone.utc).isoformat(),
        "members": results,
    }
