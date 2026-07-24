import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
MATCH_CACHE_DIR = DATA_DIR / "matches"
SNAPSHOT_DIR = DATA_DIR / "snapshots"
ROSTER_PATH = DATA_DIR / "roster.json"
ASSETS_DIR = ROOT / "assets"
CHAMPION_ICON_DIR = ASSETS_DIR / "champions"
EXCEL_PATH = ROOT / "DS IRON FINGER.xlsx"

RIOT_API_KEY = os.getenv("RIOT_API_KEY", "")
REGION = os.getenv("REGION", "vn2").lower()

# Platform routing: league-v4, summoner-v4
PLATFORM_ROUTING = {"vn2": "vn2"}
# account-v1 chỉ nhận americas/asia/europe -> VN2 dùng asia
ACCOUNT_ROUTING = {"vn2": "asia"}
# match-v5 nhận americas/asia/europe/sea -> VN2 dùng sea
MATCH_ROUTING = {"vn2": "sea"}

QUEUE_SOLO = 420
QUEUE_FLEX = 440
RANKED_QUEUE_IDS = {QUEUE_SOLO, QUEUE_FLEX}
MATCH_TYPE = "ranked"
MATCH_COUNT = 20
TOP_CHAMPIONS = 5

POSITION_LABELS = {
    "TOP": "Top",
    "JUNGLE": "Jungle",
    "MIDDLE": "Mid",
    "BOTTOM": "ADC",
    "UTILITY": "Support",
}


def platform_host() -> str:
    return f"https://{PLATFORM_ROUTING[REGION]}.api.riotgames.com"


def account_host() -> str:
    return f"https://{ACCOUNT_ROUTING[REGION]}.api.riotgames.com"


def match_host() -> str:
    return f"https://{MATCH_ROUTING[REGION]}.api.riotgames.com"
