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