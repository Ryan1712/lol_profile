from src import stats
from tests.conftest import PUUID


def test_extract_participations_only_target_player(sample_matches):
    parts = stats.extract_participations(sample_matches, PUUID)
    assert len(parts) == 6
    assert all(p["champion"] != "Teemo" for p in parts)


def test_filter_ranked_excludes_aram(sample_matches):
    parts = stats.filter_ranked(stats.extract_participations(sample_matches, PUUID))
    assert len(parts) == 5
    assert all(p["queueId"] in (420, 440) for p in parts)


def test_kda_perfect_when_no_deaths():
    assert stats.kda(5, 0, 5) == 10.0
    assert stats.kda(3, 3, 3) == 2.0


def test_top_champions_counts_and_winrate(sample_matches):
    parts = stats.filter_ranked(stats.extract_participations(sample_matches, PUUID))
    tops = stats.top_champions(parts)
    assert tops[0]["champion"] == "Ahri"
    assert tops[0]["games"] == 3
    assert tops[0]["wins"] == 2
    assert round(tops[0]["winrate"], 2) == 0.67
    # KDA Ahri = ( (10+8)+(6+10)+(3+5) ) / (2+4+7) = 42/13 = 3.23
    assert round(tops[0]["kda"], 2) == 3.23


def test_lane_distribution(sample_matches):
    parts = stats.filter_ranked(stats.extract_participations(sample_matches, PUUID))
    lanes = stats.lane_distribution(parts)
    # 3 Mid, 1 Support, 1 ADC trên 5 trận ranked
    top_lane = lanes[0]
    assert top_lane[0] == "Mid"
    assert round(top_lane[1], 2) == 0.60


def test_summarize(sample_matches):
    s = stats.summarize(sample_matches, PUUID)
    assert s["matches_analyzed"] == 5
    assert s["top_champions"][0]["champion"] == "Ahri"
    assert s["lanes"][0][0] == "Mid"
