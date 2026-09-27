# NextDNS Railway Config Builder

Ứng dụng Flask có giao diện HTML để:

- Nhập NextDNS API key và chọn profile.
- Thêm nhiều miền vào denylist/allowlist.
- Tải file `.mobileconfig` mẫu hoặc dùng `ANTIBANDA.mobileconfig` mặc định.
- Nhập tên, mô tả và NextDNS ID.
- Thay ID sau `.antiban.` và trong `https://dns.nextdns.io/ID`.
- Tải file cấu hình đã tạo xuống.

## Chạy local

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Mở `http://127.0.0.1:8080`.

## Deploy Railway

1. Tạo repository Git và đưa toàn bộ nội dung thư mục này lên repository.
2. Trong Railway chọn **New Project → Deploy from GitHub Repo**.
3. Railway tự nhận `requirements.txt`, `Procfile`/`railway.json` và cấp biến `PORT`.
4. Mở domain Railway được cấp.

Không cần tạo biến môi trường cho API key. API key được nhập qua HTTPS và chỉ dùng trong request; ứng dụng không lưu vào database/file. Railway vẫn nên bật HTTPS mặc định và không nên dùng domain công khai nếu chưa có lớp bảo vệ người dùng riêng.

## Lưu ý bảo mật

- Không commit API key vào repository.
- Nên dùng API key riêng cho mục đích này và thu hồi nếu bị lộ.
- Railway filesystem không được dùng để lưu cấu hình cá nhân lâu dài; file tạo ra chỉ được trả về trình duyệt.
