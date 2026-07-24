from src import config


def test_region_is_vn2():
    assert config.REGION == "vn2"


def test_routing_hosts():
    assert config.platform_host() == "https://vn2.api.riotgames.com"
    assert config.account_host() == "https://asia.api.riotgames.com"
    assert config.match_host() == "https://sea.api.riotgames.com"


def test_ranked_queue_ids_exclude_aram():
    assert config.RANKED_QUEUE_IDS == {420, 440}
    assert 450 not in config.RANKED_QUEUE_IDS


def test_position_labels():
    assert config.POSITION_LABELS["BOTTOM"] == "ADC"
    assert config.POSITION_LABELS["UTILITY"] == "Support"
    assert config.POSITION_LABELS["MIDDLE"] == "Mid"
