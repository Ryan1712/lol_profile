# LOL Scouting Tool — Thiết kế

**Ngày:** 2026-07-24
**Trạng thái:** Đã duyệt thiết kế + đã đọc dữ liệu thật, chờ viết implementation plan

## 1. Mục tiêu

Tool web chạy local giúp soi (scout) các đội tham gia giải Liên minh huyền thoại nội bộ công ty. Chọn một đội, bấm **Refresh**, tool tra cứu **toàn bộ thành viên** của đội trên **Riot Games API** (server Việt Nam) rồi hiển thị:

- **Rank + winrate mùa hiện tại** — Xếp hạng Đơn/Đôi và Linh hoạt (tier/division/LP, thắng/thua, % thắng)
- **Top tướng hay đánh gần đây** — 5 tướng chơi nhiều nhất trong N trận xếp hạng gần nhất, kèm KDA và winrate riêng từng tướng
- **Vị trí (lane) chủ lực** — phân bổ % theo lane (Top/Jungle/Mid/ADC/Support)

**Chỉ tính trận Xếp hạng Đơn/Đôi (queueId 420) và Linh hoạt (queueId 440). KHÔNG tính ARAM (450) hay chế độ khác.**

Số thành viên mỗi đội **không cố định 5** — dữ liệu thật có đội 5, 6, 7 người. Tool hiện hết.

## 2. Bối cảnh & ràng buộc quan trọng

### 2.1 Nguồn dữ liệu: Riot API (không phải scrape lmssplus.org)
Người dùng ban đầu muốn scrape lmssplus.org, nhưng đã chọn dùng **Riot Games API chính chủ** vì:
- Lọc `queueId` ngay tại tầng API (`type=ranked`) → loại ARAM tại nguồn, không lọc chắp vá.
- Dữ liệu JSON sạch, chính xác.
- lmssplus.org bản thân cũng lấy dữ liệu từ Riot API — dùng thẳng API thì bớt một lớp trung gian dễ lỗi thời.
- Vẫn để nút "Mở LMSS+" cạnh mỗi người để soi sâu thủ công khi cần.

**Xác thực = API key, KHÔNG phải tài khoản game.** Tool chỉ cần chuỗi `RGAPI-...` lấy từ developer.riotgames.com dán vào `.env`. Không bao giờ nhận/lưu mật khẩu tài khoản game của người dùng.

### 2.2 Firewall chặn theo category gaming
Đo thực tế trên máy người dùng (2026-07-24): DNS phân giải OK, TCP bắt tay OK, nhưng kết nối bị **reset ở bước TLS** (chặn theo SNI) với: `lmssplus.org`, `*.api.riotgames.com`, `ddragon.leagueoflegends.com`, `www.op.gg`, `github.com`. Trong khi google/microsoft/wikipedia/**pypi/npm** vẫn 200.

Kết luận: cài package được, nhưng **fetch dữ liệu LoL bị chặn trên mạng này**. Người dùng chưa quyết mạng nào để chạy (4G/VPN/mạng nhà). → **Thiết kế phải chịu được mạng lúc thông lúc chặn.**

### 2.3 Development key hết hạn 24h
Riot development key hết hạn sau 24 giờ (phải regenerate) hoặc xin Personal key (miễn phí, chờ duyệt) để dùng lâu dài. Rate limit dev key: 20 req/giây, 100 req/2 phút.

### 2.4 Thực tế dữ liệu Excel (đã đọc file "DS IRON FINGER.xlsx")
File 70 dòng, cột: `STT, Khu vực, Tên đội, Họ tên, Mail, Tên ingame`. ~11 đội có thể thi đấu. Các vấn đề dữ liệu phải xử lý:

- **Thiếu tag:** đội **All Star Cadets** (5 người) không có `#tag`; vài người khác bỏ trống nick (8127 có 2 người trống; nhóm "Chưa có đội" 8 người trống hết). Riot API **bắt buộc** có tag mới tra được (không còn tìm theo tên trần).
- **Tên đội bị tách:** khu vực RE có 6 người ghi `1 Tuấn 4 Tuất`…`6 Tuấn 4 Tuất` → thực chất **1 đội "Tuấn 4 Tuất"**.
- **Đội không đủ/thừa 5 người:** 5–7 người tuỳ đội.
- **Rác:** thừa dấu cách đầu/cuối, space thừa quanh `#`, dòng chỉ có email, ký tự đặc biệt (`領域展開`, `Øƒ`, tiếng Nhật).
- **Email trùng:** cùng email ở 2 người khác nhau → **không dùng email làm khoá định danh**. Dùng `STT` (ổn định) làm khoá.

## 3. Nguyên tắc nền: cache trận vĩnh viễn

**Một trận đã kết thúc là bất biến** → cache chi tiết trận vĩnh viễn xuống đĩa. Mỗi lần Refresh chỉ tải các trận *mới xuất hiện*.

Hệ quả:
- Quét đầu 1 đội: ~100–140 lượt gọi API → ~2–3 phút (do rate limit, tuỳ số người/đội).
- Lần sau: ~vài chục lượt → vài giây.
- **Mất mạng vẫn xem được toàn bộ dữ liệu đã quét**, kèm nhãn thời điểm cập nhật.

## 4. Kiến trúc

### 4.1 Stack
Python 3.12 (có sẵn) + FastAPI + trang HTML tĩnh. Không build step, không npm. Chạy: `python -m app` rồi mở trình duyệt.

### 4.2 Module (mỗi phần một việc, test độc lập)

| Module | Trách nhiệm | Phụ thuộc |
|---|---|---|
| `roster.py` | Import Excel → danh sách làm việc đã chuẩn hoá (gom đội, tách Riot ID). Không biết gì về Riot API. | openpyxl |
| `riot_client.py` | Gọi HTTP Riot API, tự điều tiết tốc độ, retry, phân loại lỗi. Không biết gì về đội. | httpx |
| `stats.py` | List trận → top tướng/KDA/lane/winrate. **Hàm thuần, không đụng mạng.** | — |
| `cache.py` | Đọc/ghi JSON trên đĩa: roster làm việc, snapshot kết quả, cache trận vĩnh viễn. | — |
| `app.py` | FastAPI: phục vụ web, API refresh đội, API sửa roster. | fastapi, uvicorn |

`stats.py` chứa toàn bộ logic nghiệp vụ và không đụng mạng → test dễ nhất, test kỹ nhất.

### 4.3 Roster: import, chuẩn hoá, và sửa trên web

**Không bao giờ ghi đè file Excel gốc.** Excel chỉ là nguồn import ban đầu.

- **Import (lần đầu):** `roster.py` đọc Excel → sinh `data/roster.json` (danh sách làm việc). Khi import áp dụng chuẩn hoá:
  - Trim khoảng trắng thừa ở mọi ô (khu vực, tên đội, nick).
  - Tách Riot ID: cắt tại dấu `#` **cuối cùng**, trim hai bên → `gameName` + `tagLine`. Ví dụ `Rau cải nấu thịt #6677` → name=`Rau cải nấu thịt`, tag=`6677`.
  - Nick không có `#` hoặc trống → đánh dấu `status = "cần bổ sung Riot ID"` (vẫn hiện trong đội, chưa tra được).
  - Gom đội theo tên đã chuẩn hoá; gộp `N Tuấn 4 Tuất` (bỏ tiền tố số) thành một đội **"Tuấn 4 Tuất"**.
  - Bỏ dòng rác (chỉ có email, không tên/nick).
  - Khoá định danh mỗi người = `STT`.
- **Sửa trên web (theo yêu cầu người dùng):** người dùng sửa trực tiếp trong giao diện, mọi thay đổi ghi vào `data/roster.json` (không đụng Excel):
  - Sửa **Riot ID** của một người (điền tag còn thiếu, sửa nick sai).
  - Sửa **tên đội**, và **chuyển người sang đội khác**.
  - Thêm/ẩn thành viên.
- **Re-import Excel** là hành động riêng, có cảnh báo (sẽ ghi đè `data/roster.json`). Mặc định app đọc `data/roster.json`, không tự đọc lại Excel.

### 4.4 Luồng khi Refresh một đội (với mỗi thành viên có Riot ID hợp lệ)

| Bước | Endpoint | Cache |
|---|---|---|
| 1. `gameName#tagLine` → `puuid` | account-v1 (regional) | vĩnh viễn |
| 2. Rank Đơn/Đôi + Linh hoạt, thắng/thua | league-v4 (platform: vn2) | tươi mỗi refresh |
| 3. ID các trận xếp hạng gần đây (`type=ranked`) | match-v5 (regional) | tươi |
| 4. Chi tiết từng trận **chưa có trong cache** | match-v5 | vĩnh viễn |
| 5. Tính top tướng / KDA / lane / winrate | *(thuần tính toán)* | snapshot |

Bước 3 dùng `type=ranked` → ARAM loại tại nguồn. Bước 5 vẫn kiểm lại `queueId ∈ {420, 440}` cho chắc. Người thiếu Riot ID → bỏ qua, hiện nhãn "cần bổ sung Riot ID".

> Routing (verify ở bước đầu implementation trước khi code cứng): account-v1 dùng regional routing; VN2 thuộc cụm nào cho match-v5 (sea vs asia).

## 5. Giao diện

### 5.1 Trang danh sách đội (màn hình đầu)
- Các đội gom theo **Khu vực**, mỗi đội một thẻ bấm được.
- Thẻ ghi: tên đội + số người + "đã quét X/Y · cập nhật 14:32".
- Ô tìm nhanh theo tên đội.

### 5.2 Trang một đội (bấm đội → nút Refresh)
Bảng thành viên (số dòng = số người thật của đội), mỗi người một dòng:

| Cột | Nội dung | Nguồn |
|---|---|---|
| Người | Họ tên + `Nick#TAG` **(sửa được)** + nút "Mở LMSS+" | roster.json |
| Rank Đơn/Đôi | Huy hiệu tier + LP + `123T/108B (53%)` | league-v4 |
| Rank Linh hoạt | Tương tự | league-v4 |
| Lane chủ lực | `Mid 68% · Top 22%` | stats |
| Top tướng | 5 icon tướng, mỗi tướng `KDA 3.4 · 61% (18 trận)` | stats |

- Rê chuột vào tướng → hiện kill/death/assist trung bình.
- Người thiếu Riot ID: dòng hiện ô nhập để điền `#tag` ngay tại chỗ.
- Tên đội sửa được ngay trên trang.

### 5.3 Icon offline
Ảnh tướng & huy hiệu rank đến từ CDN Riot (`ddragon`) — cũng bị firewall chặn. → **Tải sẵn bộ icon đóng kèm tool một lần** (thêm ~vài MB), để trang hiển thị đủ hình kể cả offline.

## 6. Xử lý lỗi & cấu hình

### 6.1 Cấu hình
File `.env`: `RIOT_API_KEY=...`, `REGION=vn2`. Không nhét key vào code. Không lưu mật khẩu tài khoản game ở bất kỳ đâu.

### 6.2 Khi mạng bị chặn / key hết hạn
Refresh **không làm hỏng dữ liệu cũ**. Trang vẫn hiện snapshot gần nhất + banner đỏ: *"Không kết nối được Riot API — đang xem dữ liệu lúc [giờ]. Kiểm tra mạng/VPN hoặc gia hạn key."*

Phân biệt 3 lỗi:
- **401/403** — key sai/hết hạn → báo gia hạn key.
- **429** — quá tốc độ → tự chờ theo header `Retry-After` rồi thử lại.
- **Connection reset** — firewall/mạng → báo kiểm tra mạng/VPN.
- **404 khi tra Riot ID** — nick/tag sai → gợi ý người dùng sửa Riot ID.

### 6.3 Điều tiết tốc độ
`riot_client.py` tự giới hạn dưới trần dev key (20 req/giây, 100 req/2 phút), tự chờ khi dính 429. Người dùng không phải canh.

## 7. Testing (TDD — viết test trước)

- **`stats.py`** — nhập list trận mẫu → kiểm KDA, winrate, xếp hạng tướng, % lane, và **ARAM bị loại đúng**. Phần quan trọng nhất, test kỹ nhất.
- **`roster.py`** — Excel mẫu (gồm các ca thật: thiếu tag, `N Tuấn 4 Tuất`, space thừa, email trùng, dòng rác) → parse & chuẩn hoá đúng; đánh dấu "cần bổ sung Riot ID" đúng.
- **`riot_client.py`** — giả lập 429/401/reset/404 → kiểm hành vi chờ/retry/không làm hỏng cache.

## 8. Mặc định đã chốt

- **N = 30 trận** xếp hạng gần nhất để tính thống kê.
- **Top 5 tướng** mỗi người.
- **Đóng kèm icon tướng** để xem offline.
- Nguồn: **Riot API**, region **vn2**. Xác thực bằng API key, không dùng mật khẩu game.
- **Sửa roster trên web** (Riot ID + tên đội), lưu vào `data/roster.json`, không đụng Excel gốc.
- Gộp `N Tuấn 4 Tuất` → một đội "Tuấn 4 Tuất".
- Hiện **hết** thành viên (không cố định 5).
- Nút "Mở LMSS+" mỗi người để soi thủ công.

## 9. Ngoài phạm vi (YAGNI)

- Không có bảng chi tiết từng trận (người dùng đã bỏ chọn).
- Không tính ARAM/chế độ khác.
- Không scrape lmssplus.org (chỉ link ra).
- Không export file (đã chọn web app; có thể thêm sau).
- Không multi-user/deploy — chạy local một máy.
- Không tự động lấy API key qua đăng nhập (không khả thi + không xử lý mật khẩu người dùng).

## 10. Rủi ro đã biết

1. **Máy công ty chặn Riot API** — người dùng phải chạy trên 4G/VPN/mạng nhà. Cache bền giảm nhẹ: fetch một lần, xem nhiều lần offline.
2. **Dev key hết hạn 24h** — khuyến nghị xin Personal key. Banner báo rõ khi 401.
3. **Người thiếu tag** (All Star Cadets + vài người) — Riot API không tra được cho tới khi bổ sung tag qua ô sửa trên web.
4. **Routing vn2 cho match-v5** cần verify thực tế ở bước đầu implementation.
