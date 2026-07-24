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
