# Hệ thống tư vấn Family Menu Suggestion

Hệ thống chatbot cung cấp tư vấn dinh dưỡng và gợi ý thực đơn dựa trên RAG (Retrieval-Augmented Generation) sử dụng Google Gemini và Pinecone.

## Cài đặt

1. Clone repository
2. Cài đặt thư viện cần thiết:
```bash
pip install -r requirements.txt
```
3. Tạo file `.env` từ file `.env.example` và cấu hình các thông tin API key cần thiết.

## Khởi tạo Vector Index

Để tăng tốc độ khởi động của ứng dụng, bạn nên tạo vector index trước:

```bash
python run.py --create-index
```

Nếu muốn tạo lại index hoàn toàn (xóa index cũ và tạo lại):

```bash
python run.py --create-index --force-create
```

Hoặc có thể chạy trực tiếp file store_index.py để cập nhật index:

```bash
python store_index.py
```

## Chạy ứng dụng

Sau khi đã tạo vector index, bạn có thể chạy ứng dụng FastAPI:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

Ứng dụng sẽ khởi động nhanh hơn vì không phải tạo lại vector index từ đầu.

## Cấu trúc dự án

- `app/`: Chứa ứng dụng FastAPI
- `src/`: Chứa các module chức năng
  - `helper.py`: Các hàm tiện ích
  - `prompt.py`: Xây dựng RAG chain
- `Data/`: Chứa dữ liệu PDF về dinh dưỡng
- `store_index.py`: Các hàm quản lý vector index và tạo index
- `run.py`: Script để chạy ứng dụng hoặc tạo index

## API Endpoints

- `GET /`: Trang chủ
- `GET /health`: Kiểm tra trạng thái
- `POST /new_session`: Tạo phiên chat mới
- `POST /query`: Gửi câu hỏi và nhận câu trả lời

## Lưu ý

- Index Pinecone được tạo một lần và sử dụng lại cho các lần chạy sau
- Hệ thống sử dụng Redis để lưu lịch sử chat
- Dữ liệu được lưu trong MySQL để phân tích sau này 