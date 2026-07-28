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

## Test từ điện thoại (không có máy tính)

Chỉ cần iPhone + GitHub, chọn 1 trong 2 cách:

### Cách A — Deploy lên Render.com (khuyên dùng, ít thao tác nhất trên điện thoại)

1. Mở [render.com](https://render.com) bằng Safari, đăng nhập bằng tài khoản GitHub.
2. **New +** → **Web Service** → chọn repo `lol_profile`.
3. Render tự nhận diện `render.yaml` trong repo (build: `pip install -r requirements.txt`, start: `python run.py`). Nếu Render không tự đọc, tự nhập 2 lệnh đó vào ô Build/Start Command.
4. Ở mục **Environment Variables**, thêm `RIOT_API_KEY` = key lấy từ https://developer.riotgames.com (key tạm hết hạn 24h, cần vào lấy key mới rồi cập nhật lại khi hết hạn). `REGION` đã có sẵn giá trị `vn2` trong `render.yaml`.
5. Bấm **Deploy**. Đợi build xong, Render cho 1 URL dạng `https://lol-scouting-tool.onrender.com` — mở thẳng URL đó bằng Safari.
6. Free tier sẽ "ngủ" sau ~15 phút không ai truy cập, lần mở lại đầu tiên chậm khoảng 30-50s — bình thường.

### Cách B — GitHub Codespaces

1. Mở repo trên github.com bằng Safari → nút **Code** → tab **Codespaces** → **Create codespace on <branch>**.
2. Trong terminal của Codespace (giao diện VS Code trên web): chạy `pip install -r requirements.txt`, tạo file `.env` với `RIOT_API_KEY` và `REGION=vn2`, rồi chạy `python run.py`.
3. Codespaces tự phát hiện port 8000 đang mở, hiện thông báo/nút **Open in Browser** ở góc dưới — bấm để mở app trong tab Safari mới. Có thể đổi visibility của port sang **Public** ở tab **Ports** nếu muốn share link cho người khác.
4. Free tier cá nhân: 60 giờ Codespaces/tháng miễn phí.

## Ghi chú

- **Firewall công ty chặn Riot API.** Chạy trên 4G/VPN/mạng nhà. Dữ liệu đã quét được cache, mất mạng vẫn xem lại được.
- **Không sửa Excel gốc.** Mọi chỉnh sửa (Riot ID, tên đội) lưu ở `data/roster.json`.
- Đội thiếu tag (vd All Star Cadets): điền `Tên#TAG` vào ô trên web rồi Refresh.
- Import lại từ Excel: xoá `data/roster.json` rồi khởi động lại.

## Test

```
python -m pytest -v
```
