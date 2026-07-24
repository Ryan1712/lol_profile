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
