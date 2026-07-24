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


def import_excel(path=None):
    if path is None:
        path = config.EXCEL_PATH
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


def save_roster(roster, path=None):
    if path is None:
        path = config.ROSTER_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(roster, f, ensure_ascii=False, indent=2)


def load_roster(path=None):
    if path is None:
        path = config.ROSTER_PATH
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
