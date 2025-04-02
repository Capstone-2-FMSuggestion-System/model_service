# Hệ Thống Gợi Ý Thực Đơn Gia Đình (Family Menu Suggestion System)

## Giới Thiệu Dự Án

Hệ Thống Gợi Ý Thực Đơn Gia Đình là một ứng dụng chatbot dinh dưỡng thông minh được xây dựng bằng tiếng Việt, sử dụng công nghệ RAG (Retrieval Augmented Generation) kết hợp với Google Gemini để cung cấp thông tin dinh dưỡng chính xác và gợi ý thực đơn phù hợp cho người dùng.

Các chức năng chính của hệ thống:
- Tư vấn về dinh dưỡng, thực phẩm và chế độ ăn uống
- Gợi ý thực đơn phù hợp với nhu cầu cá nhân
- Cung cấp thông tin về các vấn đề dinh dưỡng đặc biệt (dị ứng, trẻ em, phụ nữ mang thai)
- Lưu trữ lịch sử trò chuyện để cá nhân hóa trải nghiệm

## Cấu Trúc Dự Án

```
chatbot_service/
│
├── Data/                   # Thư mục chứa các file PDF dữ liệu dinh dưỡng
│   ├── Medical_book.pdf
│   ├── Dinh dưỡng hợp lý và sức khỏe.pdf
│   ├── dinh-duong-va-suc-khoe.pdf
│
├── app/                    # Thư mục chứa logic chính của API
│   ├── __init__.py         # File đánh dấu package
│   ├── main.py             # File chạy API FastAPI
│
├── src/                    # Thư mục chứa mã nguồn chính
│   ├── __init__.py         # File đánh dấu package
│   ├── helper.py           # Các hàm hỗ trợ (xử lý PDF, Pinecone)
│   ├── prompt.py           # Xử lý prompt và RAG chain
│   ├── store_index.py      # Quản lý lưu trữ và cập nhật index
│
├── research/               # Thư mục chứa các notebook nghiên cứu
│   ├── google_ai_chatbot.ipynb
│   ├── logs.ipynb
│
├── requirements.txt        # Danh sách thư viện cần cài đặt
├── .env                    # File chứa các biến môi trường
├── Dockerfile              # File cấu hình Docker
├── docker-compose.yml      # File cấu hình Docker Compose
├── db_init.sql             # Script khởi tạo cơ sở dữ liệu
├── run.py                  # Script chạy ứng dụng
└── README.md               # Tài liệu hướng dẫn
```

## Hướng Dẫn Cài Đặt

### Yêu Cầu Hệ Thống

- Python 3.9 trở lên
- MySQL 8.0 trở lên
- Redis (cho cache)
- Tài khoản Pinecone (cho vector database)
- Tài khoản Google AI (cho Gemini API)

### Cài Đặt Thư Viện

1. Clone repository về máy:

```bash
git clone <repository-url>
cd Capstone-2-Family-Menu-Suggestion-System/model_service/chatbot_service
```

2. Cài đặt các thư viện cần thiết:

```bash
pip install -r requirements.txt
```

### Cấu Hình Môi Trường

1. Tạo file `.env` trong thư mục gốc của dự án với nội dung sau:

```
# Database Configuration
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=your_username
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=family_menu_system

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Pinecone Configuration
PINECONE_API_KEY=your_pinecone_api_key

# Google AI Configuration
GOOGLE_API_KEY=your_google_api_key
GEMINI_API_KEY=your_gemini_api_key
```

2. Khởi tạo cơ sở dữ liệu MySQL:

```bash
mysql -u your_username -p < db_init.sql
```

### Chạy Ứng Dụng

#### Chạy Trực Tiếp

```bash
python run.py
```

Ứng dụng sẽ chạy tại địa chỉ: http://localhost:8000

#### Chạy Với Docker

##### Chuẩn Bị Môi Trường Docker

1. Đảm bảo bạn đã cài đặt Docker và Docker Compose:
   - Windows: Cài đặt [Docker Desktop](https://www.docker.com/products/docker-desktop)
   - Linux: Cài đặt Docker Engine và Docker Compose

2. Tạo file `.env` trong thư mục gốc với các API key cần thiết:
```
PINECONE_API_KEY=your_pinecone_api_key
GOOGLE_API_KEY=your_google_api_key
```

3. Đảm bảo thư mục `Data` chứa các file PDF cần thiết.

##### Khởi Chạy Ứng Dụng

```bash
# Xây dựng và khởi chạy các container
docker-compose up -d

# Kiểm tra trạng thái các container
docker-compose ps

# Xem logs của ứng dụng
docker-compose logs -f chatbot
```

Ứng dụng sẽ chạy tại địa chỉ: http://localhost:8000

##### Quản Lý Container

```bash
# Dừng ứng dụng
docker-compose down

# Khởi động lại ứng dụng
docker-compose restart

# Xây dựng lại container
docker-compose up -d --build
```

Chi tiết hơn về triển khai Docker có thể xem trong file `DOCKER_GUIDE.md`.

## Hướng Dẫn Sử Dụng

### API Endpoints

1. **Kiểm tra trạng thái API**

```
GET /
```

Response:
```json
{
  "message": "Welcome to Family Menu Suggestion System API",
  "status": "operational"
}
```

2. **Kiểm tra sức khỏe hệ thống**

```
GET /health
```

3. **Tạo phiên trò chuyện mới**

```
POST /sessions/new
```

Response:
```json
{
  "session_id": "unique-session-id"
}
```

4. **Gửi câu hỏi**

```
POST /query
```

Request body:
```json
{
  "question": "Chế độ ăn uống lành mạnh là gì?",
  "session_id": "your-session-id"  // Tùy chọn
}
```

Response:
```json
{
  "answer": "Chế độ ăn uống lành mạnh bao gồm việc ăn đa dạng các loại thực phẩm từ tất cả các nhóm thực phẩm, kiểm soát khẩu phần ăn, và hạn chế thực phẩm chứa nhiều đường, muối và chất béo bão hòa.",
  "session_id": "session-id"
}
```

### Ví Dụ Sử Dụng

#### Ví dụ 1: Hỏi về dinh dưỡng cơ bản

Câu hỏi: "Vitamin C có trong những thực phẩm nào?"

Câu trả lời: "Vitamin C có nhiều trong các loại trái cây họ cam quýt (cam, chanh, bưởi), ớt chuông, kiwi, dâu tây, ổi, đu đủ, và các loại rau lá xanh như bông cải xanh và rau chân vịt."

#### Ví dụ 2: Gợi ý thực đơn

Câu hỏi: "Gợi ý thực đơn cho người bị tiểu đường"

Câu trả lời: "Thực đơn cho người tiểu đường nên ưu tiên thực phẩm có chỉ số đường huyết thấp như rau xanh, protein nạc, ngũ cốc nguyên hạt. Bữa sáng: Yến mạch với quả mọng. Bữa trưa: Salad gà với dầu olive. Bữa tối: Cá hồi nướng với rau luộc và gạo lứt."

## Cấu Hình và Biến Môi Trường

### Biến Môi Trường Bắt Buộc

| Biến | Mô tả | Giá trị mặc định |
|------|-------|----------------|
| MYSQL_HOST | Địa chỉ máy chủ MySQL | localhost |
| MYSQL_PORT | Cổng MySQL | 3306 |
| MYSQL_USER | Tên người dùng MySQL | - |
| MYSQL_PASSWORD | Mật khẩu MySQL | - |
| MYSQL_DATABASE | Tên cơ sở dữ liệu | family_menu_system |
| REDIS_HOST | Địa chỉ máy chủ Redis | localhost |
| REDIS_PORT | Cổng Redis | 6379 |
| REDIS_DB | Số database Redis | 0 |
| PINECONE_API_KEY | API key của Pinecone | - |
| GOOGLE_API_KEY | API key của Google AI | - |
| GEMINI_API_KEY | API key của Gemini | - |

### Cấu Hình Nâng Cao

#### Cấu Hình RAG

Bạn có thể điều chỉnh các tham số RAG trong file `src/prompt.py`:

- `chunk_size`: Kích thước của mỗi đoạn văn bản (mặc định: 500)
- `chunk_overlap`: Độ chồng lấp giữa các đoạn (mặc định: 20)
- `k`: Số lượng đoạn văn bản được truy xuất (mặc định: 3)

#### Cấu Hình Gemini

Bạn có thể điều chỉnh các tham số của Gemini trong file `src/prompt.py`:

- `temperature`: Độ sáng tạo của mô hình (mặc định: 0.7)
- `max_output_tokens`: Số lượng token tối đa trong đầu ra (mặc định: 200)

## Xử Lý Sự Cố

### Lỗi Kết Nối Cơ Sở Dữ Liệu

**Vấn đề**: Không thể kết nối đến cơ sở dữ liệu MySQL.

**Giải pháp**:
1. Kiểm tra thông tin kết nối trong file `.env`
2. Đảm bảo dịch vụ MySQL đang chạy: `sudo service mysql status`
3. Kiểm tra quyền truy cập của người dùng MySQL

### Lỗi Pinecone API

**Vấn đề**: Không thể kết nối đến Pinecone hoặc lỗi API.

**Giải pháp**:
1. Kiểm tra API key trong file `.env`
2. Đảm bảo đã tạo index trên Pinecone với đúng cấu hình
3. Kiểm tra giới hạn API của tài khoản Pinecone

### Lỗi Gemini API

**Vấn đề**: Không thể kết nối đến Gemini hoặc lỗi API.

**Giải pháp**:
1. Kiểm tra API key trong file `.env`
2. Đảm bảo đã kích hoạt Gemini API trong dự án Google Cloud
3. Kiểm tra giới hạn API của tài khoản Google

### Lỗi Không Tìm Thấy Dữ Liệu

**Vấn đề**: Chatbot không trả lời hoặc trả lời không chính xác.

**Giải pháp**:
1. Kiểm tra thư mục `Data` có chứa các file PDF không
2. Đảm bảo đã chạy quá trình indexing dữ liệu vào Pinecone
3. Kiểm tra log để xem lỗi cụ thể

## Thông Tin Hỗ Trợ

### Liên Hệ

Nếu bạn gặp vấn đề hoặc có câu hỏi, vui lòng liên hệ:

- **Email**: vannamdang2003@gmail.com
- **GitHub**: [GitHub Repository](https://github.com/your-username/Capstone-2-Family-Menu-Suggestion-System)

### Tài Liệu Tham Khảo

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [LangChain Documentation](https://python.langchain.com/docs/get_started/introduction)
- [Pinecone Documentation](https://docs.pinecone.io/docs/overview)
- [Google Gemini Documentation](https://ai.google.dev/docs)

### Đóng Góp

Chúng tôi rất hoan nghênh mọi đóng góp để cải thiện dự án. Vui lòng tạo pull request hoặc báo cáo lỗi trên GitHub repository.