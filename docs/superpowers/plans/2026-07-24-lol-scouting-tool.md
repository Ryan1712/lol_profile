# LOL Scouting Tool Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tool web chạy local để soi các đội trong giải LOL công ty: chọn đội → Refresh → hiện rank, top tướng (KDA/winrate), lane chủ lực của từng thành viên, dữ liệu lấy từ Riot API (chỉ trận Đơn/Đôi + Linh hoạt, loại ARAM).

**Architecture:** Python + FastAPI phục vụ một trang tĩnh. Các module tách biệt: đọc/sửa danh sách đội (`roster`), gọi Riot API có điều tiết tốc độ (`riot_client`), tính thống kê thuần (`stats`), cache trận vĩnh viễn xuống đĩa (`cache`), và điều phối một lần refresh (`scout`). Trận đấu là bất biến nên chỉ tải trận mới; mất mạng vẫn xem được snapshot cũ.

**Tech Stack:** Python 3.12, FastAPI, uvicorn, httpx, openpyxl, python-dotenv, pytest.

## Global Constraints

- Python 3.12 (đã cài sẵn trên máy).
- Region cố định: `vn2`. Routing: platform `vn2` (league-v4/summoner-v4), account-v1 `asia`, match-v5 `sea`.
- Chỉ tính `queueId ∈ {420, 440}` (Đơn/Đôi, Linh hoạt). ARAM `450` bị loại. Lọc bằng `?type=ranked` ở match-v5 và kiểm lại queueId khi tính.
- Xác thực bằng `RIOT_API_KEY` (chuỗi `RGAPI-...`) đọc từ `.env`. KHÔNG hardcode key. KHÔNG lưu mật khẩu tài khoản game.
- **Không bao giờ ghi đè file Excel gốc** (`DS IRON FINGER.xlsx`). App đọc/ghi `data/roster.json`.
- Khoá định danh mỗi người = `STT` (email có thể trùng). Người thiếu STT được cấp id tổng hợp `x1, x2, ...`.
- N = 30 trận gần nhất để tính thống kê; Top 5 tướng mỗi người.
- Rate limit dev key: ≤ 20 req/giây và ≤ 100 req/2 phút. Gặp 429 → chờ theo `Retry-After` rồi thử lại.
- Ánh xạ vị trí: `{TOP:Top, JUNGLE:Jungle, MIDDLE:Mid, BOTTOM:ADC, UTILITY:Support}`.
- TDD: viết test trước, commit thường xuyên.

---

## File Structure

```
lol/
  .env                     # đã có (RIOT_API_KEY, REGION=vn2)
  .gitignore               # đã có
  requirements.txt         # Task 1
  run.py                   # Task 7 — khởi động server + mở browser
  README.md                # Task 9
  src/
    __init__.py
    config.py              # Task 1 — env, routing, hằng số, đường dẫn
    stats.py               # Task 2 — hàm thuần: top tướng/KDA/lane/winrate
    roster.py              # Task 3 — import Excel, chuẩn hoá, đọc/ghi/sửa roster.json
    cache.py               # Task 4 — cache trận + snapshot trên đĩa
    riot_client.py         # Task 5 — HTTP Riot API, rate limit, retry, lỗi
    scout.py               # Task 6 — điều phối refresh 1 đội
    app.py                 # Task 7 — FastAPI routes + phục vụ static
  web/
    index.html             # Task 8
    app.js                 # Task 8
    styles.css             # Task 8
  scripts/
    download_icons.py      # Task 9 — tải icon tướng (chạy 1 lần, mạng thông)
    smoke_test.py          # Task 9 — kiểm routing/key (chạy đầu tiên, mạng thông)
  assets/champions/        # (sinh ra) icon tướng
  data/                    # (sinh ra) roster.json, matches/, snapshots/
  tests/
    __init__.py
    conftest.py            # Task 2
    test_config.py         # Task 1
    test_stats.py          # Task 2
    test_roster.py         # Task 3
    test_cache.py          # Task 4
    test_riot_client.py    # Task 5
    test_scout.py          # Task 6
    test_app.py            # Task 7
    fixtures/              # dữ liệu mẫu
```

---

## Task 1: Scaffolding + config

**Files:**
- Create: `requirements.txt`, `src/__init__.py`, `src/config.py`, `tests/__init__.py`, `tests/test_config.py`

**Interfaces:**
- Consumes: `.env` (đã có: `RIOT_API_KEY`, `REGION=vn2`).
- Produces:
  - `config.REGION: str`, `config.RIOT_API_KEY: str`
  - `config.RANKED_QUEUE_IDS: set[int]`, `config.QUEUE_SOLO=420`, `config.QUEUE_FLEX=440`
  - `config.MATCH_TYPE="ranked"`, `config.MATCH_COUNT=30`, `config.TOP_CHAMPIONS=5`
  - `config.POSITION_LABELS: dict[str,str]`
  - `config.platform_host() -> str`, `config.account_host() -> str`, `config.match_host() -> str`
  - Đường dẫn: `config.ROOT, DATA_DIR, MATCH_CACHE_DIR, SNAPSHOT_DIR, ROSTER_PATH, ASSETS_DIR, CHAMPION_ICON_DIR, EXCEL_PATH`

- [ ] **Step 1: Tạo requirements.txt**

```
fastapi==0.115.0
uvicorn==0.30.6
httpx==0.27.2
openpyxl==3.1.5
python-dotenv==1.0.1
pytest==8.3.3
```

- [ ] **Step 2: Tạo package files rỗng**

Create `src/__init__.py` (empty) và `tests/__init__.py` (empty).

- [ ] **Step 3: Viết test cho config (failing)**

Create `tests/test_config.py`:

```python
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
```

- [ ] **Step 4: Chạy test — kỳ vọng FAIL**

Run: `python -m pytest tests/test_config.py -v`
Expected: FAIL (`ModuleNotFoundError` hoặc `AttributeError` vì `src/config.py` chưa có).

- [ ] **Step 5: Cài dependencies**

Run: `python -m pip install -r requirements.txt`
Expected: cài thành công (pypi không bị chặn).

- [ ] **Step 6: Viết src/config.py**

Create `src/config.py`:

```python
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
MATCH_COUNT = 30
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
```

- [ ] **Step 7: Chạy test — kỳ vọng PASS**

Run: `python -m pytest tests/test_config.py -v`
Expected: 4 passed.

- [ ] **Step 8: Commit**

```bash
git add requirements.txt src/__init__.py src/config.py tests/__init__.py tests/test_config.py
git commit -m "feat: scaffolding + config with VN2 routing"
```

> Nếu thư mục chưa phải git repo: chạy `git init` trước ở lần commit đầu tiên.

---

## Task 2: stats.py — thống kê thuần (trọng tâm, test kỹ)

**Files:**
- Create: `src/stats.py`, `tests/conftest.py`, `tests/test_stats.py`

**Interfaces:**
- Consumes: `config.RANKED_QUEUE_IDS`, `config.TOP_CHAMPIONS`, `config.POSITION_LABELS`.
- Produces (tất cả hàm thuần, không đụng mạng/đĩa):
  - `extract_participations(matches: list[dict], puuid: str) -> list[dict]` — mỗi phần tử: `{queueId:int, champion:str, kills:int, deaths:int, assists:int, win:bool, position:str, gameCreation:int}`
  - `filter_ranked(parts: list[dict]) -> list[dict]` — giữ `queueId ∈ RANKED_QUEUE_IDS`
  - `kda(kills:int, deaths:int, assists:int) -> float`
  - `top_champions(parts: list[dict], n:int=TOP_CHAMPIONS) -> list[dict]` — mỗi phần tử: `{champion:str, games:int, wins:int, winrate:float, kda:float, k:float, d:float, a:float}`, sắp theo games giảm dần
  - `lane_distribution(parts: list[dict]) -> list[list]` — `[[label:str, fraction:float], ...]` sắp giảm dần, dùng nhãn từ `POSITION_LABELS`
  - `summarize(matches: list[dict], puuid: str) -> dict` — `{matches_analyzed:int, top_champions:list, lanes:list}`

- [ ] **Step 1: Viết fixtures dùng chung (conftest)**

Create `tests/conftest.py`:

```python
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
```

- [ ] **Step 2: Viết test cho stats (failing)**

Create `tests/test_stats.py`:

```python
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
```

- [ ] **Step 3: Chạy test — kỳ vọng FAIL**

Run: `python -m pytest tests/test_stats.py -v`
Expected: FAIL (`ModuleNotFoundError: src.stats`).

- [ ] **Step 4: Viết src/stats.py**

Create `src/stats.py`:

```python
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
```

- [ ] **Step 5: Chạy test — kỳ vọng PASS**

Run: `python -m pytest tests/test_stats.py -v`
Expected: 6 passed.

- [ ] **Step 6: Commit**

```bash
git add src/stats.py tests/conftest.py tests/test_stats.py
git commit -m "feat: pure stats (top champs, KDA, lane, winrate, ARAM excluded)"
```

---

## Task 3: roster.py — import Excel, chuẩn hoá, sửa

**Files:**
- Create: `src/roster.py`, `tests/test_roster.py`

**Interfaces:**
- Consumes: `config.EXCEL_PATH`, `config.ROSTER_PATH`.
- Produces:
  - `parse_riot_id(raw: str) -> tuple[str, str] | None` — cắt tại `#` cuối, trim; None nếu không có `#` hợp lệ
  - `normalize_team_name(name: str) -> str` — trim; `"3 Tuấn 4 Tuất" -> "Tuấn 4 Tuất"`
  - `import_excel(path=config.EXCEL_PATH) -> dict` — trả roster `{imported_at, source_excel, teams: [...]}`
  - `save_roster(roster: dict, path=config.ROSTER_PATH) -> None`
  - `load_roster(path=config.ROSTER_PATH) -> dict`
  - `ensure_roster() -> dict` — nếu roster.json chưa có thì import từ Excel rồi lưu
  - `update_member_riot_id(roster, stt, raw_ingame) -> dict`
  - `rename_team(roster, team_id, new_name) -> dict`
  - Cấu trúc team: `{id:str, name:str, region:str, members:[{stt, full_name, email, raw_ingame, game_name, tag_line, status}]}` với `status ∈ {"ok","needs_riot_id"}`

- [ ] **Step 1: Viết test cho roster (failing)**

Create `tests/test_roster.py`:

```python
import openpyxl

from src import roster


def _make_excel(tmp_path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "LOL"
    ws.append(["STT ", "Khu vực ", "Tên đội ", "Họ tên ", "Mail ", "Tên ingame "])
    rows = [
        ["8", "Hà Nội", "The last dance", "A", "a@x.com", "skuukzky #Huynh"],
        ["9", "Hà Nội", "The last dance", "B", "b@x.com", "Rau cải nấu thịt #6677"],
        ["24", "Hà Nội", "All Star Cadets", "C", "c@x.com", "chloe"],       # thiếu tag
        ["62", "RE", "1 Tuấn 4 Tuất ", "D", "d@x.com", "Tunzzz #112003"],
        ["63", "RE", "2 Tuấn 4 Tuất ", "E", "e@x.com", "Be better #8888"],
        ["", "", "", "", "junk@x.com", ""],                                  # dòng rác
    ]
    for r in rows:
        ws.append(r)
    p = tmp_path / "sample.xlsx"
    wb.save(p)
    return p


def test_parse_riot_id_last_hash():
    assert roster.parse_riot_id("Rau cải nấu thịt #6677") == ("Rau cải nấu thịt", "6677")
    assert roster.parse_riot_id("ieatburger#ieb") == ("ieatburger", "ieb")
    assert roster.parse_riot_id("chloe") is None
    assert roster.parse_riot_id("  ") is None


def test_normalize_team_name_merges_tuan():
    assert roster.normalize_team_name("3 Tuấn 4 Tuất ") == "Tuấn 4 Tuất"
    assert roster.normalize_team_name(" The last dance ") == "The last dance"


def test_import_excel_groups_and_flags(tmp_path):
    r = roster.import_excel(_make_excel(tmp_path))
    teams = {t["name"]: t for t in r["teams"]}
    assert "The last dance" in teams
    assert "Tuấn 4 Tuất" in teams          # 62 + 63 gộp
    assert len(teams["Tuấn 4 Tuất"]["members"]) == 2
    # dòng rác bị loại
    assert all(m["full_name"] for t in r["teams"] for m in t["members"])
    # thành viên thiếu tag bị đánh dấu
    cadet = teams["All Star Cadets"]["members"][0]
    assert cadet["status"] == "needs_riot_id"
    ldance = teams["The last dance"]["members"][0]
    assert ldance["status"] == "ok"
    assert ldance["game_name"] == "skuukzky"


def test_update_member_riot_id(tmp_path):
    r = roster.import_excel(_make_excel(tmp_path))
    r = roster.update_member_riot_id(r, "24", "Chloe#VN2")
    member = next(m for t in r["teams"] for m in t["members"] if m["stt"] == "24")
    assert member["status"] == "ok"
    assert member["game_name"] == "Chloe"
    assert member["tag_line"] == "VN2"


def test_save_and_load_roundtrip(tmp_path):
    r = roster.import_excel(_make_excel(tmp_path))
    p = tmp_path / "roster.json"
    roster.save_roster(r, p)
    r2 = roster.load_roster(p)
    assert r2["teams"] == r["teams"]
```

- [ ] **Step 2: Chạy test — kỳ vọng FAIL**

Run: `python -m pytest tests/test_roster.py -v`
Expected: FAIL (`ModuleNotFoundError: src.roster`).

- [ ] **Step 3: Viết src/roster.py**

Create `src/roster.py`:

```python
import json
import re
from datetime import datetime, timezone

import openpyxl

from src import config

_TUAN_PREFIX = re.compile(r"^\s*\d+\s+(Tuấn 4 Tuất)\s*$")


def parse_riot_id(raw):
    if not raw:
        return None
    s = str(raw).strip()
    if "#" not in s:
        return None
    name, _, tag = s.rpartition("#")
    name = name.strip()
    tag = tag.strip()
    if not name or not tag:
        return None
    return name, tag


def normalize_team_name(name):
    s = str(name or "").strip()
    m = _TUAN_PREFIX.match(s)
    if m:
        return m.group(1)
    return s


def _member(stt, full_name, email, raw_ingame):
    parsed = parse_riot_id(raw_ingame)
    if parsed:
        game_name, tag_line, status = parsed[0], parsed[1], "ok"
    else:
        game_name, tag_line, status = "", "", "needs_riot_id"
    return {
        "stt": str(stt),
        "full_name": str(full_name or "").strip(),
        "email": str(email or "").strip(),
        "raw_ingame": str(raw_ingame or "").strip(),
        "game_name": game_name,
        "tag_line": tag_line,
        "status": status,
    }


def import_excel(path=config.EXCEL_PATH):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.worksheets[0]
    teams = {}          # key normalized name -> team dict
    order = []          # giữ thứ tự xuất hiện
    synthetic = 0
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i == 0:
            continue  # header
        cells = list(row) + [None] * (6 - len(row))
        stt, region, team_raw, full_name, email, ingame = cells[:6]
        full_name = str(full_name or "").strip()
        # dòng rác: không tên -> bỏ
        if not full_name:
            continue
        stt = str(stt or "").strip()
        if not stt:
            synthetic += 1
            stt = f"x{synthetic}"
        team_name = normalize_team_name(team_raw)
        region = str(region or "").strip()
        if team_name not in teams:
            teams[team_name] = {
                "id": f"t{len(order) + 1}",
                "name": team_name,
                "region": region,
                "members": [],
            }
            order.append(team_name)
        teams[team_name]["members"].append(_member(stt, full_name, email, ingame))
    return {
        "imported_at": datetime.now(timezone.utc).isoformat(),
        "source_excel": str(path),
        "teams": [teams[name] for name in order],
    }


def save_roster(roster, path=config.ROSTER_PATH):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(roster, f, ensure_ascii=False, indent=2)


def load_roster(path=config.ROSTER_PATH):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def ensure_roster():
    if config.ROSTER_PATH.exists():
        return load_roster()
    roster = import_excel()
    save_roster(roster)
    return roster


def update_member_riot_id(roster, stt, raw_ingame):
    for team in roster["teams"]:
        for m in team["members"]:
            if m["stt"] == str(stt):
                m["raw_ingame"] = str(raw_ingame or "").strip()
                parsed = parse_riot_id(raw_ingame)
                if parsed:
                    m["game_name"], m["tag_line"], m["status"] = parsed[0], parsed[1], "ok"
                else:
                    m["game_name"], m["tag_line"], m["status"] = "", "", "needs_riot_id"
                return roster
    raise KeyError(f"STT không tồn tại: {stt}")


def rename_team(roster, team_id, new_name):
    for team in roster["teams"]:
        if team["id"] == team_id:
            team["name"] = str(new_name or "").strip()
            return roster
    raise KeyError(f"team_id không tồn tại: {team_id}")
```

- [ ] **Step 4: Chạy test — kỳ vọng PASS**

Run: `python -m pytest tests/test_roster.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add src/roster.py tests/test_roster.py
git commit -m "feat: roster import/normalize/edit (merge Tuan4Tuat, flag missing tags)"
```

---

## Task 4: cache.py — cache trận + snapshot trên đĩa

**Files:**
- Create: `src/cache.py`, `tests/test_cache.py`

**Interfaces:**
- Consumes: `config.MATCH_CACHE_DIR`, `config.SNAPSHOT_DIR`.
- Produces:
  - `get_match(match_id: str) -> dict | None`
  - `put_match(match_id: str, data: dict) -> None`
  - `has_match(match_id: str) -> bool`
  - `save_snapshot(team_id: str, snapshot: dict) -> None`
  - `load_snapshot(team_id: str) -> dict | None`

- [ ] **Step 1: Viết test cho cache (failing)**

Create `tests/test_cache.py`:

```python
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
```

- [ ] **Step 2: Chạy test — kỳ vọng FAIL**

Run: `python -m pytest tests/test_cache.py -v`
Expected: FAIL (`ModuleNotFoundError: src.cache`).

- [ ] **Step 3: Viết src/cache.py**

Create `src/cache.py`:

```python
import json

from src import config


def _match_path(match_id):
    return config.MATCH_CACHE_DIR / f"{match_id}.json"


def has_match(match_id):
    return _match_path(match_id).exists()


def get_match(match_id):
    p = _match_path(match_id)
    if not p.exists():
        return None
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def put_match(match_id, data):
    config.MATCH_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(_match_path(match_id), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


def _snapshot_path(team_id):
    return config.SNAPSHOT_DIR / f"{team_id}.json"


def save_snapshot(team_id, snapshot):
    config.SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    with open(_snapshot_path(team_id), "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)


def load_snapshot(team_id):
    p = _snapshot_path(team_id)
    if not p.exists():
        return None
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)
```

- [ ] **Step 4: Chạy test — kỳ vọng PASS**

Run: `python -m pytest tests/test_cache.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add src/cache.py tests/test_cache.py
git commit -m "feat: disk cache for matches (permanent) and team snapshots"
```

---

## Task 5: riot_client.py — HTTP Riot API + rate limit + lỗi

**Files:**
- Create: `src/riot_client.py`, `tests/test_riot_client.py`

**Interfaces:**
- Consumes: `config.RIOT_API_KEY`, `config.platform_host/account_host/match_host`, `config.MATCH_TYPE`, `config.MATCH_COUNT`.
- Produces:
  - Exceptions: `RiotError`, `AuthError` (401/403), `NotFoundError` (404), `RateLimitError`, `NetworkError`
  - Class `RiotClient(api_key=config.RIOT_API_KEY, transport=None, sleep_fn=time.sleep)`
    - `get_account_by_riot_id(game_name: str, tag_line: str) -> dict` (có `puuid`)
    - `get_league_entries(puuid: str) -> list[dict]` (mỗi entry có `queueType, tier, rank, leaguePoints, wins, losses`)
    - `get_ranked_match_ids(puuid: str, count:int=config.MATCH_COUNT) -> list[str]`
    - `get_match(match_id: str) -> dict`
  - `transport` cho phép tiêm `httpx.MockTransport` khi test; `sleep_fn` tiêm để test retry không chờ thật.

- [ ] **Step 1: Viết test cho riot_client (failing)**

Create `tests/test_riot_client.py`:

```python
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
```

- [ ] **Step 2: Chạy test — kỳ vọng FAIL**

Run: `python -m pytest tests/test_riot_client.py -v`
Expected: FAIL (`ModuleNotFoundError: src.riot_client`).

- [ ] **Step 3: Viết src/riot_client.py**

Create `src/riot_client.py`:

```python
import time
from collections import deque
from urllib.parse import quote

import httpx

from src import config


class RiotError(Exception):
    pass


class AuthError(RiotError):
    pass


class NotFoundError(RiotError):
    pass


class RateLimitError(RiotError):
    pass


class NetworkError(RiotError):
    pass


class _RateLimiter:
    """Giữ dưới 20 req/giây và 100 req/2 phút cho dev key."""

    def __init__(self, sleep_fn):
        self._sleep = sleep_fn
        self._sec = deque()
        self._long = deque()

    def _now(self):
        return time.monotonic()

    def acquire(self):
        while True:
            now = self._now()
            while self._sec and now - self._sec[0] >= 1:
                self._sec.popleft()
            while self._long and now - self._long[0] >= 120:
                self._long.popleft()
            if len(self._sec) < 20 and len(self._long) < 100:
                self._sec.append(now)
                self._long.append(now)
                return
            wait_sec = 1 - (now - self._sec[0]) if len(self._sec) >= 20 else 0
            wait_long = 120 - (now - self._long[0]) if len(self._long) >= 100 else 0
            self._sleep(max(0.02, wait_sec, wait_long))


class RiotClient:
    def __init__(self, api_key=config.RIOT_API_KEY, transport=None, sleep_fn=time.sleep,
                 max_retries=3):
        self.api_key = api_key
        self.sleep_fn = sleep_fn
        self.max_retries = max_retries
        self.limiter = _RateLimiter(sleep_fn)
        self._client = httpx.Client(
            transport=transport,
            timeout=15.0,
            headers={"X-Riot-Token": api_key},
        )

    def close(self):
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def _get(self, url, params=None):
        attempt = 0
        while True:
            attempt += 1
            self.limiter.acquire()
            try:
                resp = self._client.get(url, params=params)
            except httpx.HTTPError as e:
                raise NetworkError(str(e)) from e
            code = resp.status_code
            if code == 200:
                return resp.json()
            if code in (401, 403):
                raise AuthError(f"{code}: key sai hoặc hết hạn")
            if code == 404:
                raise NotFoundError(f"404: {url}")
            if code == 429:
                retry_after = float(resp.headers.get("Retry-After", "1"))
                if attempt > self.max_retries:
                    raise RateLimitError("429 quá nhiều lần")
                self.sleep_fn(retry_after)
                continue
            if 500 <= code < 600:
                if attempt > self.max_retries:
                    raise RiotError(f"{code}: lỗi máy chủ Riot")
                self.sleep_fn(1.0)
                continue
            raise RiotError(f"{code}: {url}")

    def get_account_by_riot_id(self, game_name, tag_line):
        url = (f"{config.account_host()}/riot/account/v1/accounts/by-riot-id/"
               f"{quote(game_name)}/{quote(tag_line)}")
        return self._get(url)

    def get_league_entries(self, puuid):
        # Ưu tiên endpoint by-puuid (mới). Nếu 404 -> fallback qua summoner-v4.
        url = f"{config.platform_host()}/lol/league/v4/entries/by-puuid/{quote(puuid)}"
        try:
            return self._get(url)
        except NotFoundError:
            surl = f"{config.platform_host()}/lol/summoner/v4/summoners/by-puuid/{quote(puuid)}"
            summoner = self._get(surl)
            sid = summoner.get("id")
            if not sid:
                return []
            lurl = f"{config.platform_host()}/lol/league/v4/entries/by-summoner/{quote(sid)}"
            return self._get(lurl)

    def get_ranked_match_ids(self, puuid, count=config.MATCH_COUNT):
        url = f"{config.match_host()}/lol/match/v5/matches/by-puuid/{quote(puuid)}/ids"
        return self._get(url, params={"type": config.MATCH_TYPE, "start": 0, "count": count})

    def get_match(self, match_id):
        url = f"{config.match_host()}/lol/match/v5/matches/{quote(match_id)}"
        return self._get(url)
```

- [ ] **Step 4: Chạy test — kỳ vọng PASS**

Run: `python -m pytest tests/test_riot_client.py -v`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add src/riot_client.py tests/test_riot_client.py
git commit -m "feat: Riot API client with rate limiting, retry, typed errors"
```

---

## Task 6: scout.py — điều phối refresh 1 đội

**Files:**
- Create: `src/scout.py`, `tests/test_scout.py`

**Interfaces:**
- Consumes: `riot_client.RiotClient` (hoặc bất kỳ object cùng phương thức), `cache`, `stats`, `config`, exceptions từ `riot_client`.
- Produces:
  - `refresh_member(client, member: dict) -> dict` — trả `{riot_id, puuid, solo, flex, lanes, top_champions, matches_analyzed, error}` (`error=None` nếu OK; `"needs_riot_id"`, `"not_found"`, hoặc `"network"`)
  - `refresh_team(client, team: dict) -> dict` — snapshot `{team_id, team_name, refreshed_at, members: {stt: member_result}}`
  - `_pick_rank(entries, queue_type) -> dict | None` — chọn entry theo `RANKED_SOLO_5x5`/`RANKED_FLEX_SR`

- [ ] **Step 1: Viết test cho scout (failing)**

Create `tests/test_scout.py`:

```python
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
```

- [ ] **Step 2: Chạy test — kỳ vọng FAIL**

Run: `python -m pytest tests/test_scout.py -v`
Expected: FAIL (`ModuleNotFoundError: src.scout`).

- [ ] **Step 3: Viết src/scout.py**

Create `src/scout.py`:

```python
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
```

> Lưu ý: `AuthError` KHÔNG bắt ở đây — để nó nổi lên `app.py` xử lý (báo banner "key hết hạn") và giữ nguyên snapshot cũ.

- [ ] **Step 4: Chạy test — kỳ vọng PASS**

Run: `python -m pytest tests/test_scout.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add src/scout.py tests/test_scout.py
git commit -m "feat: scout orchestration (rank + champs per member, match cache reuse)"
```

---

## Task 7: app.py — FastAPI routes + run.py

**Files:**
- Create: `src/app.py`, `run.py`, `tests/test_app.py`

**Interfaces:**
- Consumes: `roster`, `scout`, `cache`, `config`, `riot_client`.
- Produces (HTTP JSON API + static):
  - `GET /` → `web/index.html`
  - `GET /api/teams` → `{teams:[{id,name,region,member_count, refreshed_at|null}]}`
  - `GET /api/team/{team_id}` → `{team:{...}, snapshot:{...}|null}`
  - `POST /api/team/{team_id}/refresh` → `{snapshot:{...}}` hoặc `{error:"auth"|"network", snapshot:{...}|null}` (HTTP 200; lỗi nằm trong body để giữ snapshot cũ)
  - `POST /api/member/{stt}/riot-id` body `{raw_ingame}` → `{ok:true, team:{...}}`
  - `POST /api/team/{team_id}/rename` body `{name}` → `{ok:true}`
  - App exposes `app` (FastAPI) và factory `build_app(client_factory=...)` để test tiêm client giả.
  - `web/` mount ở `/`; `assets/` mount ở `/assets`.

- [ ] **Step 1: Viết test cho app (failing)**

Create `tests/test_app.py`:

```python
from fastapi.testclient import TestClient

from src import app as appmod
from src import cache, roster


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
```

- [ ] **Step 2: Chạy test — kỳ vọng FAIL**

Run: `python -m pytest tests/test_app.py -v`
Expected: FAIL (`ModuleNotFoundError: src.app` hoặc `AttributeError: build_app`).

- [ ] **Step 3: Viết src/app.py**

Create `src/app.py`:

```python
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src import cache, config, roster, scout
from src import riot_client as rc


class RiotIdBody(BaseModel):
    raw_ingame: str


class RenameBody(BaseModel):
    name: str


def _team_by_id(data, team_id):
    for t in data["teams"]:
        if t["id"] == team_id:
            return t
    return None


def build_app(client_factory=lambda: rc.RiotClient()):
    app = FastAPI(title="LOL Scouting Tool")

    @app.get("/")
    def index():
        return FileResponse(config.ROOT / "web" / "index.html")

    @app.get("/api/teams")
    def list_teams():
        data = roster.ensure_roster()
        out = []
        for t in data["teams"]:
            snap = cache.load_snapshot(t["id"])
            out.append({
                "id": t["id"],
                "name": t["name"],
                "region": t["region"],
                "member_count": len(t["members"]),
                "refreshed_at": snap["refreshed_at"] if snap else None,
            })
        return {"teams": out}

    @app.get("/api/team/{team_id}")
    def get_team(team_id: str):
        data = roster.ensure_roster()
        team = _team_by_id(data, team_id)
        if not team:
            return JSONResponse({"error": "not_found"}, status_code=404)
        return {"team": team, "snapshot": cache.load_snapshot(team_id)}

    @app.post("/api/team/{team_id}/refresh")
    def refresh(team_id: str):
        data = roster.ensure_roster()
        team = _team_by_id(data, team_id)
        if not team:
            return JSONResponse({"error": "not_found"}, status_code=404)
        client = client_factory()
        try:
            snapshot = scout.refresh_team(client, team)
        except rc.AuthError:
            return {"error": "auth", "snapshot": cache.load_snapshot(team_id)}
        except rc.NetworkError:
            return {"error": "network", "snapshot": cache.load_snapshot(team_id)}
        finally:
            close = getattr(client, "close", None)
            if callable(close):
                close()
        cache.save_snapshot(team_id, snapshot)
        return {"snapshot": snapshot}

    @app.post("/api/member/{stt}/riot-id")
    def edit_riot_id(stt: str, body: RiotIdBody):
        data = roster.ensure_roster()
        data = roster.update_member_riot_id(data, stt, body.raw_ingame)
        roster.save_roster(data)
        team = next((t for t in data["teams"] for m in t["members"] if m["stt"] == stt), None)
        return {"ok": True, "team": team}

    @app.post("/api/team/{team_id}/rename")
    def rename(team_id: str, body: RenameBody):
        data = roster.ensure_roster()
        data = roster.rename_team(data, team_id, body.name)
        roster.save_roster(data)
        return {"ok": True}

    # static mounts (đặt cuối để không nuốt /api)
    if (config.ROOT / "web").exists():
        app.mount("/web", StaticFiles(directory=config.ROOT / "web"), name="web")
    if config.ASSETS_DIR.exists():
        app.mount("/assets", StaticFiles(directory=config.ASSETS_DIR), name="assets")
    return app


app = build_app()
```

- [ ] **Step 4: Chạy test — kỳ vọng PASS**

Run: `python -m pytest tests/test_app.py -v`
Expected: 4 passed.

- [ ] **Step 5: Viết run.py (khởi động + mở browser)**

Create `run.py`:

```python
import threading
import webbrowser

import uvicorn

HOST = "127.0.0.1"
PORT = 8000


def _open():
    webbrowser.open(f"http://{HOST}:{PORT}/")


if __name__ == "__main__":
    threading.Timer(1.2, _open).start()
    uvicorn.run("src.app:app", host=HOST, port=PORT, reload=False)
```

- [ ] **Step 6: Chạy toàn bộ test**

Run: `python -m pytest -v`
Expected: tất cả test từ Task 1–7 pass.

- [ ] **Step 7: Commit**

```bash
git add src/app.py run.py tests/test_app.py
git commit -m "feat: FastAPI routes (teams, refresh, edit roster) + run.py launcher"
```

---

## Task 8: Web frontend

**Files:**
- Create: `web/index.html`, `web/styles.css`, `web/app.js`

**Interfaces:**
- Consumes API: `/api/teams`, `/api/team/{id}`, `/api/team/{id}/refresh`, `/api/member/{stt}/riot-id`, `/api/team/{id}/rename`.
- Consumes assets: `/assets/champions/{Champion}.png` (fallback nếu thiếu ảnh).
- Produces: giao diện 2 màn (danh sách đội → chi tiết đội), nút Refresh, sửa Riot ID/tên đội tại chỗ, banner lỗi, nút "Mở LMSS+".

- [ ] **Step 1: Viết web/index.html**

Create `web/index.html`:

```html
<!doctype html>
<html lang="vi">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>LOL Scouting — Soi đội</title>
  <link rel="stylesheet" href="/web/styles.css" />
</head>
<body>
  <header>
    <h1 id="title">Soi đội LOL</h1>
    <input id="search" placeholder="Tìm đội…" hidden />
    <button id="back" hidden>← Danh sách đội</button>
  </header>
  <div id="banner" class="banner" hidden></div>
  <main id="view"></main>
  <script src="/web/app.js"></script>
</body>
</html>
```

- [ ] **Step 2: Viết web/styles.css**

Create `web/styles.css`:

```css
:root { --bg:#0f1116; --card:#191c24; --line:#2a2f3a; --fg:#e6e8ee; --muted:#9aa3b2;
  --win:#3fb950; --loss:#f85149; --accent:#4c8dff; }
* { box-sizing: border-box; }
body { margin:0; font:15px/1.45 system-ui,Segoe UI,Roboto,sans-serif;
  background:var(--bg); color:var(--fg); }
header { display:flex; gap:12px; align-items:center; padding:14px 20px;
  border-bottom:1px solid var(--line); position:sticky; top:0; background:var(--bg); z-index:5; }
h1 { font-size:18px; margin:0; }
#search { margin-left:auto; padding:8px 12px; border-radius:8px; border:1px solid var(--line);
  background:var(--card); color:var(--fg); min-width:220px; }
button { cursor:pointer; border:1px solid var(--line); background:var(--card); color:var(--fg);
  padding:8px 14px; border-radius:8px; }
button.primary { background:var(--accent); border-color:var(--accent); color:#fff; }
.banner { margin:12px 20px; padding:12px 14px; border-radius:8px; background:#3a1d1d;
  border:1px solid var(--loss); color:#ffd7d7; }
main { padding:20px; }
.region-title { color:var(--muted); text-transform:uppercase; font-size:12px;
  letter-spacing:.08em; margin:22px 0 8px; }
.grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(220px,1fr)); gap:12px; }
.team-card { background:var(--card); border:1px solid var(--line); border-radius:12px;
  padding:14px; cursor:pointer; }
.team-card:hover { border-color:var(--accent); }
.team-card h3 { margin:0 0 6px; font-size:16px; }
.team-card .meta { color:var(--muted); font-size:13px; }
table { width:100%; border-collapse:collapse; }
th,td { text-align:left; padding:10px 12px; border-bottom:1px solid var(--line);
  vertical-align:top; }
th { color:var(--muted); font-weight:600; font-size:13px; }
.rank-badge { font-weight:600; }
.tier-IRON{color:#7c7c7c}.tier-BRONZE{color:#b06a3b}.tier-SILVER{color:#9fb0c3}
.tier-GOLD{color:#e2b13c}.tier-PLATINUM{color:#4bbfa5}.tier-EMERALD{color:#37a86b}
.tier-DIAMOND{color:#5aa0ff}.tier-MASTER{color:#b054e0}.tier-GRANDMASTER{color:#e0555b}
.tier-CHALLENGER{color:#63d0ff}
.wr-win{color:var(--win)} .wr-loss{color:var(--loss)}
.champs { display:flex; gap:10px; flex-wrap:wrap; }
.champ { display:flex; gap:6px; align-items:center; }
.champ img { width:34px; height:34px; border-radius:6px; background:#000; }
.champ .c-meta { font-size:12px; color:var(--muted); }
.tag-warn { color:#ffcf6b; font-size:13px; }
.edit-inline { display:flex; gap:6px; }
.edit-inline input { padding:6px 8px; border-radius:6px; border:1px solid var(--line);
  background:var(--bg); color:var(--fg); }
.lmss { font-size:12px; color:var(--accent); text-decoration:none; }
.muted { color:var(--muted); }
```

- [ ] **Step 3: Viết web/app.js**

Create `web/app.js`:

```javascript
const view = document.getElementById("view");
const banner = document.getElementById("banner");
const backBtn = document.getElementById("back");
const search = document.getElementById("search");
let allTeams = [];

function showBanner(msg) { banner.textContent = msg; banner.hidden = !msg; }
function api(path, opts) {
  return fetch(path, opts).then((r) => r.json());
}
function pct(x) { return Math.round((x || 0) * 100) + "%"; }
function esc(s) { return (s || "").replace(/[&<>"]/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c])); }

async function showTeams() {
  backBtn.hidden = true;
  const data = await api("/api/teams");
  allTeams = data.teams;
  search.hidden = false;
  renderTeams(allTeams);
}

function renderTeams(teams) {
  const byRegion = {};
  teams.forEach((t) => { (byRegion[t.region] = byRegion[t.region] || []).push(t); });
  view.innerHTML = Object.keys(byRegion).map((region) => `
    <div class="region-title">${esc(region)}</div>
    <div class="grid">
      ${byRegion[region].map((t) => `
        <div class="team-card" data-id="${t.id}">
          <h3>${esc(t.name)}</h3>
          <div class="meta">${t.member_count} người</div>
          <div class="meta">${t.refreshed_at
            ? "cập nhật " + new Date(t.refreshed_at).toLocaleString("vi-VN")
            : "chưa quét"}</div>
        </div>`).join("")}
    </div>`).join("");
  view.querySelectorAll(".team-card").forEach((el) =>
    el.addEventListener("click", () => showTeam(el.dataset.id)));
}

search.addEventListener("input", () => {
  const q = search.value.toLowerCase();
  renderTeams(allTeams.filter((t) => t.name.toLowerCase().includes(q)));
});

async function showTeam(teamId) {
  showBanner("");
  backBtn.hidden = false;
  search.hidden = true;
  const { team, snapshot } = await api("/api/team/" + teamId);
  renderTeam(team, snapshot);
}

function rankCell(rank) {
  if (!rank) return '<span class="muted">Chưa xếp hạng</span>';
  const total = (rank.wins || 0) + (rank.losses || 0);
  const wr = total ? rank.wins / total : 0;
  const wrClass = wr >= 0.5 ? "wr-win" : "wr-loss";
  return `<span class="rank-badge tier-${rank.tier}">${rank.tier} ${rank.rank}</span>
    · ${rank.lp} LP<br><span class="${wrClass}">${rank.wins}T/${rank.losses}B (${pct(wr)})</span>`;
}

function champCell(champs) {
  if (!champs || !champs.length) return '<span class="muted">—</span>';
  return `<div class="champs">${champs.map((c) => `
    <div class="champ" title="KDA ${c.kda.toFixed(2)} — ${c.k.toFixed(1)}/${c.d.toFixed(1)}/${c.a.toFixed(1)} · ${c.games} trận">
      <img src="/assets/champions/${esc(c.champion)}.png"
           onerror="this.style.visibility='hidden'" alt="${esc(c.champion)}" />
      <div class="c-meta">${esc(c.champion)}<br>KDA ${c.kda.toFixed(1)} · ${pct(c.winrate)}</div>
    </div>`).join("")}</div>`;
}

function laneCell(lanes) {
  if (!lanes || !lanes.length) return '<span class="muted">—</span>';
  return lanes.slice(0, 2).map((l) => `${l[0]} ${pct(l[1])}`).join(" · ");
}

function memberRow(m, res) {
  const lmss = m.game_name
    ? `https://lmssplus.org/?name=${encodeURIComponent(m.game_name)}&tag=${encodeURIComponent(m.tag_line)}`
    : "https://lmssplus.org/";
  const idCell = m.status === "ok"
    ? `${esc(m.game_name)}#${esc(m.tag_line)}`
    : `<span class="tag-warn">⚠ cần bổ sung Riot ID</span>`;
  const edit = `<div class="edit-inline">
      <input placeholder="Tên#TAG" value="${esc(m.raw_ingame)}" data-stt="${m.stt}" />
      <button data-save="${m.stt}">Lưu</button></div>`;
  if (!res || res.error === "needs_riot_id") {
    return `<tr>
      <td><b>${esc(m.full_name)}</b><br>${idCell}<br>${edit}
        <a class="lmss" href="${lmss}" target="_blank">Mở LMSS+</a></td>
      <td colspan="4" class="muted">${res && res.error === "needs_riot_id"
        ? "Chưa tra được — thiếu Riot ID" : "Chưa quét"}</td></tr>`;
  }
  if (res.error === "not_found") {
    return `<tr><td><b>${esc(m.full_name)}</b><br>${idCell}<br>${edit}</td>
      <td colspan="4" class="tag-warn">Không tìm thấy Riot ID này — sửa lại?</td></tr>`;
  }
  if (res.error === "network") {
    return `<tr><td><b>${esc(m.full_name)}</b><br>${idCell}</td>
      <td colspan="4" class="wr-loss">Lỗi mạng khi tra</td></tr>`;
  }
  return `<tr>
    <td><b>${esc(m.full_name)}</b><br>${idCell}<br>${edit}
      <a class="lmss" href="${lmss}" target="_blank">Mở LMSS+</a></td>
    <td>${rankCell(res.solo)}</td>
    <td>${rankCell(res.flex)}</td>
    <td>${laneCell(res.lanes)}</td>
    <td>${champCell(res.top_champions)}</td></tr>`;
}

function renderTeam(team, snapshot) {
  const results = (snapshot && snapshot.members) || {};
  view.innerHTML = `
    <div style="display:flex;gap:12px;align-items:center;margin-bottom:12px">
      <input id="team-name" value="${esc(team.name)}" style="font-size:18px;font-weight:700" />
      <button id="save-name">Đổi tên</button>
      <button id="refresh" class="primary">⟳ Refresh</button>
      <span id="refreshed" class="muted">${snapshot
        ? "cập nhật " + new Date(snapshot.refreshed_at).toLocaleString("vi-VN") : ""}</span>
    </div>
    <table>
      <thead><tr><th>Người</th><th>Đơn/Đôi</th><th>Linh hoạt</th>
        <th>Lane</th><th>Top tướng</th></tr></thead>
      <tbody>${team.members.map((m) => memberRow(m, results[m.stt])).join("")}</tbody>
    </table>`;

  document.getElementById("refresh").addEventListener("click", async (e) => {
    e.target.disabled = true; e.target.textContent = "Đang quét…"; showBanner("");
    const out = await api("/api/team/" + team.id + "/refresh", { method: "POST" });
    if (out.error === "auth") showBanner("Không kết nối được Riot API — key sai/hết hạn. Gia hạn key ở developer.riotgames.com rồi thử lại.");
    else if (out.error === "network") showBanner("Không kết nối được Riot API — kiểm tra mạng/VPN. Đang xem dữ liệu cũ.");
    renderTeam(team, out.snapshot);
  });
  document.getElementById("save-name").addEventListener("click", async () => {
    const name = document.getElementById("team-name").value;
    await api("/api/team/" + team.id + "/rename", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }) });
    showBanner("Đã đổi tên đội.");
  });
  view.querySelectorAll("button[data-save]").forEach((btn) =>
    btn.addEventListener("click", async () => {
      const stt = btn.dataset.save;
      const input = view.querySelector(`input[data-stt="${stt}"]`);
      const r = await api("/api/member/" + stt + "/riot-id", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ raw_ingame: input.value }) });
      renderTeam(r.team, snapshot);
      showBanner("Đã lưu Riot ID. Bấm Refresh để tra lại.");
    }));
}

backBtn.addEventListener("click", showTeams);
showTeams();
```

- [ ] **Step 4: Kiểm thử thủ công (smoke, không cần mạng Riot)**

Run: `python run.py`
Expected: trình duyệt mở `http://127.0.0.1:8000/`, hiện danh sách đội gom theo khu vực (đọc từ `data/roster.json`, tự import Excel lần đầu). Bấm vào 1 đội → thấy bảng thành viên. Bấm Refresh khi máy chặn Riot → hiện banner đỏ "kiểm tra mạng/VPN", KHÔNG crash. Dừng bằng Ctrl+C.

- [ ] **Step 5: Commit**

```bash
git add web/index.html web/styles.css web/app.js
git commit -m "feat: web UI (team list, scout table, inline edit, LMSS+ link, error banner)"
```

---

## Task 9: Scripts (icon downloader, smoke test) + README

**Files:**
- Create: `scripts/download_icons.py`, `scripts/smoke_test.py`, `README.md`

**Interfaces:**
- `download_icons.py`: tải icon tướng từ ddragon vào `assets/champions/{Champion}.png`. Chạy 1 lần trên mạng thông.
- `smoke_test.py`: dùng `RiotClient` thật + 1 Riot ID hợp lệ để xác nhận routing (account `asia`, match `sea`), key còn hạn, và league-v4 by-puuid có hoạt động không. Chạy ĐẦU TIÊN trên mạng thông trước khi tin vào routing.

- [ ] **Step 1: Viết scripts/download_icons.py**

Create `scripts/download_icons.py`:

```python
"""Tải icon tướng từ Data Dragon về assets/champions/. Chạy 1 lần trên mạng thông."""
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "champions"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with httpx.Client(timeout=30.0) as c:
        versions = c.get("https://ddragon.leagueoflegends.com/api/versions.json").json()
        ver = versions[0]
        data = c.get(f"https://ddragon.leagueoflegends.com/cdn/{ver}/data/en_US/champion.json").json()
        champs = list(data["data"].keys())
        print(f"DDragon {ver}: {len(champs)} tướng → {OUT}")
        for i, name in enumerate(champs, 1):
            dest = OUT / f"{name}.png"
            if dest.exists():
                continue
            url = f"https://ddragon.leagueoflegends.com/cdn/{ver}/img/champion/{name}.png"
            img = c.get(url)
            if img.status_code == 200:
                dest.write_bytes(img.content)
            print(f"  [{i}/{len(champs)}] {name}", end="\r")
    print("\nXong.")


if __name__ == "__main__":
    try:
        main()
    except httpx.HTTPError as e:
        print(f"Lỗi mạng (ddragon có thể bị firewall chặn): {e}", file=sys.stderr)
        sys.exit(1)
```

- [ ] **Step 2: Viết scripts/smoke_test.py**

Create `scripts/smoke_test.py`:

```python
"""Kiểm tra routing + API key trên mạng thông. Dùng: python scripts/smoke_test.py "Name#TAG" """
import sys

from src import riot_client as rc
from src import config


def main(riot_id):
    if "#" not in riot_id:
        print("Cần dạng Name#TAG"); return 2
    name, tag = riot_id.rsplit("#", 1)
    print(f"Region={config.REGION} account={config.account_host()} match={config.match_host()}")
    with rc.RiotClient() as client:
        acc = client.get_account_by_riot_id(name.strip(), tag.strip())
        puuid = acc["puuid"]
        print("account-v1 OK, puuid =", puuid[:12], "…")
        entries = client.get_league_entries(puuid)
        print("league-v4 OK, số hàng rank =", len(entries))
        for e in entries:
            print("  ", e.get("queueType"), e.get("tier"), e.get("rank"), e.get("leaguePoints"), "LP")
        ids = client.get_ranked_match_ids(puuid, count=5)
        print("match-v5 ids OK:", ids)
        if ids:
            m = client.get_match(ids[0])
            print("match-v5 detail OK, queueId =", m["info"]["queueId"])
    print("SMOKE TEST PASS ✅")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Dùng: python scripts/smoke_test.py "Name#TAG"'); sys.exit(2)
    try:
        sys.exit(main(sys.argv[1]))
    except rc.AuthError:
        print("❌ Key sai/hết hạn — regenerate ở developer.riotgames.com"); sys.exit(1)
    except rc.NotFoundError:
        print("❌ Không tìm thấy Riot ID — kiểm tra Name#TAG"); sys.exit(1)
    except rc.NetworkError as e:
        print(f"❌ Mạng bị chặn (firewall?) — thử 4G/VPN: {e}"); sys.exit(1)
```

- [ ] **Step 3: Viết README.md**

Create `README.md`:

```markdown
# LOL Scouting Tool

Soi các đội trong giải LOL công ty: rank, top tướng (KDA/winrate), lane chủ lực — dữ liệu từ Riot API (chỉ Đơn/Đôi + Linh hoạt, loại ARAM).

## Cài đặt (một lần)

```
python -m pip install -r requirements.txt
```

Tạo `.env` (đã có sẵn):
```
RIOT_API_KEY=RGAPI-...   # lấy ở https://developer.riotgames.com (hết hạn 24h, regenerate khi cần)
REGION=vn2
```

## Trước khi chạy thật (trên mạng KHÔNG chặn Riot — 4G/VPN/mạng nhà)

1. Kiểm tra routing + key:
   ```
   python scripts/smoke_test.py "Faker#VN2"
   ```
   Phải in `SMOKE TEST PASS ✅`. Nếu báo mạng bị chặn → đổi sang 4G/VPN.
   Nếu `league-v4 by-puuid` lỗi, client tự fallback qua summoner-v4 (đã xử lý).

2. Tải icon tướng (một lần, để xem offline):
   ```
   python scripts/download_icons.py
   ```

## Chạy

```
python run.py
```
Trình duyệt mở `http://127.0.0.1:8000/`. Chọn đội → **Refresh**.

## Ghi chú

- **Firewall công ty chặn Riot API.** Chạy trên 4G/VPN/mạng nhà. Dữ liệu đã quét được cache, mất mạng vẫn xem lại được.
- **Không sửa Excel gốc.** Mọi chỉnh sửa (Riot ID, tên đội) lưu ở `data/roster.json`.
- Đội thiếu tag (vd All Star Cadets): điền `Tên#TAG` vào ô trên web rồi Refresh.
- Import lại từ Excel: xoá `data/roster.json` rồi khởi động lại.

## Test

```
python -m pytest -v
```
```

- [ ] **Step 4: Chạy lại toàn bộ test**

Run: `python -m pytest -v`
Expected: tất cả pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/download_icons.py scripts/smoke_test.py README.md
git commit -m "feat: icon downloader, smoke test, README"
```

---

## Task 10: Chạy thật đầu-cuối (trên mạng thông) + verify routing

**Files:** không tạo file mới — bước xác minh thực tế.

**Interfaces:** Consumes toàn bộ hệ thống đã build.

- [ ] **Step 1: Chuyển sang mạng không chặn Riot** (4G hotspot / VPN / mạng nhà).

- [ ] **Step 2: Regenerate API key** ở developer.riotgames.com (key cũ đã hết hạn 24h) và cập nhật `.env`.

- [ ] **Step 3: Smoke test với một Riot ID có thật trong giải**

Run: `python scripts/smoke_test.py "seasouth#0711"`
Expected: `SMOKE TEST PASS ✅`.
- Nếu `match-v5` báo 404/NotFound ở bước ids nhưng account OK → routing `sea` sai; thử đổi `MATCH_ROUTING["vn2"]` sang `"asia"` trong `src/config.py`, chạy lại. (Đây là điểm rủi ro đã biết trong spec.)

- [ ] **Step 4: Tải icon**

Run: `python scripts/download_icons.py`
Expected: `assets/champions/` có ~160+ file .png.

- [ ] **Step 5: Chạy app, refresh một đội thật**

Run: `python run.py` → mở web → chọn đội "G0AT" → Refresh.
Expected: sau ~1–2 phút hiện rank, top tướng có icon, KDA, winrate, lane cho từng người. Refresh lần 2 nhanh hơn nhiều (cache trận).

- [ ] **Step 6: Kiểm tra ca thiếu tag** — vào đội "All Star Cadets", điền `Tên#TAG` cho một người, Lưu, Refresh → người đó có dữ liệu.

- [ ] **Step 7: Commit trạng thái cuối (nếu có chỉnh routing)**

```bash
git add -A
git commit -m "chore: verify end-to-end on live network; lock routing"
```

---

## Self-Review (đã thực hiện khi viết plan)

**Spec coverage:**
- Rank Đơn/Đôi + Linh hoạt → Task 5 (`get_league_entries`), Task 6 (`_pick_rank`), Task 8 (`rankCell`). ✓
- Top 5 tướng + KDA + winrate → Task 2 (`top_champions`), Task 8 (`champCell`). ✓
- Lane chủ lực → Task 2 (`lane_distribution`). ✓
- Loại ARAM → Task 2 (`filter_ranked`) + `?type=ranked` Task 5. ✓
- Cache trận vĩnh viễn → Task 4 + Task 6 (`_load_matches`). ✓
- Sửa Riot ID + tên đội trên web, không đụng Excel → Task 3 + Task 7 + Task 8. ✓
- Gộp "Tuấn 4 Tuất", chuẩn hoá, bỏ rác, thiếu tag → Task 3. ✓
- Định danh theo STT → Task 3. ✓
- Xử lý lỗi 401/403/429/reset/404 → Task 5 + Task 7 (banner) + Task 8. ✓
- Icon offline + rank badge → Task 8 (CSS badge cho rank; icon tướng tải qua Task 9). Rank dùng badge CSS thay vì emblem PNG (ddragon không có emblem) — đơn giản, offline-safe. ✓
- API key trong `.env`, không lưu mật khẩu → Task 1 + README. ✓
- Routing vn2 verify → Task 9 smoke_test + Task 10. ✓

**Placeholder scan:** không có TBD/TODO; mọi step có code/lệnh cụ thể. ✓

**Type consistency:** tên hàm/khoá nhất quán across tasks: `refresh_member/refresh_team`, `get_league_entries`, `get_ranked_match_ids`, member keys `game_name/tag_line/status/stt`, snapshot `members[stt]` với `solo/flex/lanes/top_champions/matches_analyzed/error`. Frontend đọc đúng các khoá này. ✓

**Sai khác nhỏ có chủ đích:** Rank hiển thị bằng badge CSS (không tải emblem PNG) — lệch nhẹ so với spec 5.3 nhưng bền hơn khi offline và tránh nguồn ảnh dễ vỡ.
