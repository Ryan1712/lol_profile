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
