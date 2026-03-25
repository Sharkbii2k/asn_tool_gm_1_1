# ASN Tool GM 1.1

Bản này là app dùng thật, gồm:
- Front-end UI theo mẫu ASN TOOL GM
- Back-end FastAPI
- Parser PDF thực
- Packing Master lưu riêng
- Result editable trước khi export
- Export Excel thật theo form

## Chạy local
```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

Sau đó mở:
- http://127.0.0.1:8000

## Deploy
Có thể deploy lên:
- Render
- Railway
- VPS
- Docker

## Ghi chú
- UI này nối trực tiếp với API thật.
- Parser hiện tối ưu cho PDF gốc text-selectable.
- Ảnh JPG/PNG hiện đã có nút upload trong UI nhưng cần OCR module riêng nếu muốn xử lý ảnh chính xác như PDF.

## Bản vá 1.1.1
- Sửa export Excel trên iPhone/Safari bằng cơ chế export trực tiếp qua URL.
- Lưu session export tạm trên server để tránh lỗi tải file.


## Bản vá 1.1.2
- Chuẩn hóa Rev về dạng 2 ký tự (`01`, `02`, `03`...).
- Áp chuẩn hóa này cho import Single Packing, Pair Packing và lookup tính toán.
- File Single Packing tạo từ DS XC2 cũng đã sửa Rev đúng định dạng.


## Bản vá Excel clean
- Bỏ toàn bộ các ô/khung thừa bên phải trong sheet LINES.
- Chỉ giữ 1 bảng `Total Cartons` duy nhất ở L1:M5.
- Thêm dòng `TOTAL` vào bảng tổng cartons.


## ASN Tool GM 2.0
- PWA cá nhân chuẩn iPhone
- Icon Home Screen qua `apple-touch-icon` + `manifest.json`
- Packing tách 2 menu con: `Mã đơn` / `Mã đôi`
- Logic packing giữ Rev trong file nhưng ưu tiên tính theo Item; nếu cùng Item nhiều Qty khác nhau sẽ báo `Packing Conflict`
