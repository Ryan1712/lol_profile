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
