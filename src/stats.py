from collections import defaultdict

from src import config


def extract_participations(matches, puuid):
    out = []
    for m in matches:
        info = m.get("info", {})
        for p in info.get("participants", []):
            if p.get("puuid") != puuid:
                continue
            position = p.get("teamPosition") or p.get("individualPosition") or ""
            out.append(
                {
                    "queueId": info.get("queueId"),
                    "champion": p.get("championName", ""),
                    "kills": p.get("kills", 0),
                    "deaths": p.get("deaths", 0),
                    "assists": p.get("assists", 0),
                    "win": bool(p.get("win")),
                    "position": position,
                    "gameCreation": info.get("gameCreation", 0),
                }
            )
    return out


def filter_ranked(parts):
    return [p for p in parts if p.get("queueId") in config.RANKED_QUEUE_IDS]


def kda(kills, deaths, assists):
    return (kills + assists) / (deaths if deaths > 0 else 1)


def top_champions(parts, n=config.TOP_CHAMPIONS):
    agg = defaultdict(lambda: {"games": 0, "wins": 0, "k": 0, "d": 0, "a": 0})
    for p in parts:
        c = agg[p["champion"]]
        c["games"] += 1
        c["wins"] += 1 if p["win"] else 0
        c["k"] += p["kills"]
        c["d"] += p["deaths"]
        c["a"] += p["assists"]
    rows = []
    for champ, c in agg.items():
        g = c["games"]
        rows.append(
            {
                "champion": champ,
                "games": g,
                "wins": c["wins"],
                "winrate": c["wins"] / g if g else 0.0,
                "kda": kda(c["k"], c["d"], c["a"]),
                "k": c["k"] / g if g else 0.0,
                "d": c["d"] / g if g else 0.0,
                "a": c["a"] / g if g else 0.0,
            }
        )
    rows.sort(key=lambda r: (r["games"], r["winrate"]), reverse=True)
    return rows[:n]


def lane_distribution(parts):
    counts = defaultdict(int)
    total = 0
    for p in parts:
        label = config.POSITION_LABELS.get(p["position"])
        if not label:
            continue
        counts[label] += 1
        total += 1
    if total == 0:
        return []
    rows = [[label, n / total] for label, n in counts.items()]
    rows.sort(key=lambda r: r[1], reverse=True)
    return rows


def summarize(matches, puuid):
    parts = filter_ranked(extract_participations(matches, puuid))
    return {
        "matches_analyzed": len(parts),
        "top_champions": top_champions(parts),
        "lanes": lane_distribution(parts),
    }
