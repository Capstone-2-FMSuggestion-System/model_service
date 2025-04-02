# Kiến Trúc và Quy Trình Hoạt Động của Chatbot Service

## 1. Tổng Quan Hệ Thống

Chatbot Service là một hệ thống trí tuệ nhân tạo sử dụng kết hợp nhiều công nghệ:
- Google Gemini: Mô hình ngôn ngữ lớn cho việc xử lý và sinh văn bản
- Pinecone: Vector database cho việc lưu trữ và tìm kiếm ngữ nghĩa
- HuggingFace Embeddings: Chuyển đổi văn bản thành vector số học
- RAG (Retrieval Augmented Generation): Phương pháp kết hợp tìm kiếm và sinh văn bản

## 2. Các Thành Phần Chính

### 2.1 Xử Lý Dữ Liệu (Data Processing)
- Đọc dữ liệu từ các file PDF trong thư mục Data
- Chia nhỏ văn bản thành các đoạn có độ dài 500 ký tự, overlap 20 ký tự
- Chuyển đổi văn bản thành vector embedding sử dụng mô hình đa ngôn ngữ

### 2.2 Vector Database (Pinecone)
- Lưu trữ các vector embedding của văn bản
- Cho phép tìm kiếm semantic similarity
- Sử dụng cosine similarity để so sánh các vector

### 2.3 Language Model (Google Gemini)
- Xử lý ngôn ngữ tự nhiên
- Sinh văn bản phản hồi
- Tích hợp thông tin từ cơ sở dữ liệu

## 3. Quy Trình Hoạt Động

### 3.1 Khởi Tạo Hệ Thống
1. Load các biến môi trường (API keys, cấu hình)
2. Khởi tạo kết nối Pinecone
3. Load và xử lý dữ liệu từ các file PDF
4. Tạo và lưu trữ embeddings trong Pinecone

### 3.2 Xử Lý Câu Hỏi Người Dùng
1. Người dùng nhập câu hỏi
2. Hệ thống chuyển đổi câu hỏi thành vector embedding
3. Tìm kiếm các đoạn văn bản liên quan trong Pinecone
4. Kết hợp thông tin tìm được với câu hỏi

### 3.3 Sinh Câu Trả Lời
1. Gửi context và câu hỏi đến Google Gemini
2. Gemini xử lý và sinh câu trả lời
3. Định dạng và trả về kết quả cho người dùng

## 4. Các Mô Hình Sử Dụng

### 4.1 Embedding Model
- Tên: sentence-transformers/paraphrase-multilingual-mpnet-base-v2
- Đặc điểm: Hỗ trợ đa ngôn ngữ, tối ưu cho tiếng Việt
- Kích thước vector: 768 chiều

### 4.2 Language Model
- Tên: Google Gemini
- Version: gemini-2.0-flash-lite
- Cấu hình:
  - Temperature: 0.7
  - Max output tokens: 200

## 5. Luồng Dữ Liệu

## 8. Chi Tiết Các Function Chính

### 8.1 Xử Lý Dữ Liệu (helper.py)

#### `load_pdf_file(data_path)`
- Input: Đường dẫn thư mục chứa file PDF
- Chức năng: Đọc tất cả file PDF trong thư mục
- Output: Danh sách các document đã được load

#### `text_split(extracted_data)`
- Input: Dữ liệu văn bản từ PDF
- Chức năng: Chia nhỏ văn bản thành các đoạn 500 ký tự
- Output: Danh sách các text chunk

#### `download_hugging_face_embeddings()`
- Chức năng: Tải và khởi tạo mô hình embedding đa ngôn ngữ
- Output: Model embedding đã được cấu hình

#### `initialize_pinecone(index_name="chatbot")`
- Input: Tên index (mặc định: "chatbot")
- Chức năng: Khởi tạo và kiểm tra kết nối Pinecone
- Output: Client Pinecone và tên index

#### `load_documents_to_pinecone()`
- Chức năng: Quy trình đầy đủ từ đọc PDF đến lưu vào Pinecone
- Output: Đối tượng docsearch để truy vấn

### 8.2 Xử Lý Ngôn Ngữ (prompt.py)

#### `GeminiLLM Class`
- Chức năng: Wrapper cho Google Gemini API
- Các method chính:
  - `_call()`: Gọi API để sinh văn bản
  - `_acall()`: Phiên bản bất đồng bộ của _call

#### `create_retrieval_chain()`
- Chức năng: Tạo chuỗi xử lý RAG
- Output: Chain để xử lý câu hỏi và sinh câu trả lời

### 8.3 API Endpoints (main.py)

#### `chat_endpoint`
- Input: Câu hỏi của người dùng
- Chức năng: 
  1. Nhận câu hỏi
  2. Tìm kiếm context liên quan
  3. Gửi đến Gemini để xử lý
  4. Trả về câu trả lời
- Output: JSON response chứa câu trả lời

#### `translate_with_gemini()`
- Input: Văn bản cần dịch
- Chức năng: Dịch văn bản giữa các ngôn ngữ
- Output: Văn bản đã được dịch

### 8.4 Luồng Xử Lý Dữ Liệu

1. **Khởi tạo:**
```plaintext
load_documents_to_pinecone()
  ↓
load_pdf_file()
  ↓
text_split()
  ↓
download_hugging_face_embeddings()
  ↓
initialize_pinecone()
```