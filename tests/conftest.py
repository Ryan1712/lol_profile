import pytest

PUUID = "PUUID_TARGET"


def _match(queue_id, champion, k, d, a, win, position, ts):
    """Dựng 1 match-v5 tối giản với người chơi mục tiêu = PUUID."""
    return {
        "info": {
            "queueId": queue_id,
            "gameCreation": ts,
            "participants": [
                {
                    "puuid": PUUID,
                    "championName": champion,
                    "kills": k,
                    "deaths": d,
                    "assists": a,
                    "win": win,
                    "teamPosition": position,
                    "individualPosition": position,
                },
                {
                    "puuid": "OTHER",
                    "championName": "Teemo",
                    "kills": 0, "deaths": 0, "assists": 0,
                    "win": not win, "teamPosition": "TOP",
                    "individualPosition": "TOP",
                },
            ],
        }
    }


@pytest.fixture
def sample_matches():
    # 3 Ahri (2 solo win, 1 flex loss), 2 Lux solo (1 win 1 loss),
    # 1 ARAM Ahri (phải bị loại)
    return [
        _match(420, "Ahri", 10, 2, 8, True, "MIDDLE", 1000),
        _match(420, "Ahri", 6, 4, 10, True, "MIDDLE", 2000),
        _match(440, "Ahri", 3, 7, 5, False, "MIDDLE", 3000),
        _match(420, "Lux", 5, 5, 12, True, "UTILITY", 4000),
        _match(420, "Lux", 2, 8, 6, False, "BOTTOM", 5000),
        _match(450, "Ahri", 20, 1, 20, True, "MIDDLE", 6000),  # ARAM
    ]
