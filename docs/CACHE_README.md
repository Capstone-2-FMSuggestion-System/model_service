# Hệ Thống Cache và Đồng Bộ Dữ Liệu cho Chatbot Service

Hệ thống cache và đồng bộ dữ liệu được thiết kế để cải thiện hiệu suất của chatbot service bằng cách:

1. Lưu trữ dữ liệu tạm thời trong Redis để phản hồi nhanh
2. Đồng bộ dữ liệu xuống MySQL một cách bất đồng bộ để đảm bảo tính nhất quán
3. Tự động tăng question_count sau mỗi câu hỏi

## Cấu Trúc Hệ Thống

### Các Thành Phần Chính

1. **Redis Cache**: Lưu trữ tạm thời dữ liệu phiên chat và tin nhắn
2. **MySQL Database**: Lưu trữ dữ liệu phiên chat và tin nhắn lâu dài
3. **Đồng Bộ Bất Đồng Bộ**: Chạy trong background để đồng bộ dữ liệu từ Redis xuống MySQL

### Luồng Xử Lý Dữ Liệu

1. Người dùng gửi câu hỏi
2. Hệ thống cập nhật Redis:
   - Tăng question_count
   - Lưu thông tin tin nhắn
   - Đánh dấu tin nhắn cần đồng bộ
3. Hệ thống trả về câu trả lời ngay cho người dùng
4. Background thread định kỳ đồng bộ dữ liệu xuống MySQL

## Cấu Hình Hệ Thống

Thêm các biến môi trường sau vào file `.env`:

```
# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
SYNC_INTERVAL=300  # Thời gian giữa các lần đồng bộ (giây)
```

## API Endpoints

### 1. Đồng Bộ Dữ Liệu Ngay Lập Tức

Gọi endpoint này để kích hoạt đồng bộ dữ liệu ngay lập tức:

```http
GET /sync_now
```

Phản hồi:
```json
{
  "message": "Đã đồng bộ thành công X tin nhắn"
}
```

## Công Cụ Kiểm Tra

### Script Test

Dự án cung cấp script `test_cache.py` để kiểm tra hệ thống cache và đồng bộ:

```bash
python test_cache.py [options]
```

Các tùy chọn:
- `--session SESSION_ID`: Sử dụng phiên chat có sẵn
- `--user USER_ID`: ID người dùng (mặc định: 1)
- `--messages COUNT`: Số lượng tin nhắn để gửi (mặc định: 5)
- `--delay SECONDS`: Độ trễ giữa các tin nhắn (mặc định: 1)
- `--parallel COUNT`: Kiểm tra nhiều phiên chat song song
- `--sync`: Kích hoạt đồng bộ ngay lập tức
- `--stats SESSION_ID`: Hiển thị thống kê cho session_id

### Ví Dụ Sử Dụng

Kiểm tra một phiên chat đơn:
```bash
python test_cache.py --messages 5 --delay 1
```

Kiểm tra nhiều phiên chat song song:
```bash
python test_cache.py --parallel 3 --messages 4
```

Kích hoạt đồng bộ ngay lập tức:
```bash
python test_cache.py --sync
```

Xem thống kê của một phiên:
```bash
python test_cache.py --stats "session_id_here"
```

## Cấu Trúc Dữ Liệu Redis

Hệ thống sử dụng các khóa Redis sau:

1. `session:{session_id}:count` - Lưu trữ số lượng câu hỏi trong phiên
2. `session:{session_id}:history` - Lưu trữ lịch sử chat gần đây (10 tin nhắn cuối)
3. `session:{session_id}:pending_msgs` - Tập hợp các khóa tin nhắn đang chờ đồng bộ
4. `session:{session_id}:msg:{timestamp}` - Thông tin chi tiết về một tin nhắn

## Lưu Ý Quan Trọng

1. Đảm bảo Redis đang chạy trước khi khởi động ứng dụng
2. Cấu hình `SYNC_INTERVAL` phù hợp với tần suất tương tác của người dùng
3. Khi tắt ứng dụng, hệ thống sẽ tự động đồng bộ dữ liệu một lần cuối cùng 