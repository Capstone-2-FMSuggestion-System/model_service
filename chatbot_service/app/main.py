import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import sys
import re
from dotenv import load_dotenv
from typing import Dict, Any
import google.generativeai as genai
from datetime import datetime
import redis
import pymysql
import asyncio
import time
import threading
import uuid

# Add the parent directory to sys.path to allow imports from src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.prompt import create_rag_chain

# Ensure environment variables are loaded
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Family Menu Suggestion System",
    description="API for nutrition-based menu suggestions using RAG with Google Gemini",
    version="1.0.0"
)

# Cấu hình CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Cho phép tất cả các nguồn gốc, bạn có thể giới hạn nó sau
    allow_credentials=True,
    allow_methods=["*"],  # Cho phép tất cả các phương thức HTTP
    allow_headers=["*"],  # Cho phép tất cả các header
)

class QueryRequest(BaseModel):
    question: str
    session_id: str | None = None  # Optional session_id, nếu không cung cấp sẽ tạo mới
    user_id: int

class NewSessionRequest(BaseModel):
    pass  # Không cần dữ liệu, chỉ để tạo session mới

# Initialize the RAG chain once at startup
rag_chain = None
redis_client = None
mysql_conn = None

# Các biến cho cơ chế đồng bộ bất đồng bộ
sync_interval = int(os.getenv("SYNC_INTERVAL", "300"))  # 5 phút
sync_thread = None
stop_sync_thread = False

# Configure Gemini API
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))  # Thêm GEMINI_API_KEY vào .env
model = genai.GenerativeModel("gemini-2.0-flash-lite")

# Function to translate text using Gemini API
def translate_with_gemini(text, source_lang="vi", target_lang="en"):
    """Translate text using Gemini API and return only the translated text."""
    prompt = (
        f"Translate this text from {source_lang} to {target_lang} accurately, "
        f"ensuring proper Vietnamese characters if translating to Vietnamese, "
        f"and return only the translated text without additional explanation: '{text}'"
    )
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        logger.error(f"Translation error: {str(e)}")
        return text  # Fallback to original text if translation fails

# Khởi tạo Redis client
redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST"),
    port=int(os.getenv("REDIS_PORT")),
    db=int(os.getenv("REDIS_DB"))
)

# Khởi tạo MySQL connection
def get_mysql_connection():
    return pymysql.connect(
        host=os.getenv("MYSQL_HOST"),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DATABASE"),
        cursorclass=pymysql.cursors.DictCursor
    )

mysql_conn = get_mysql_connection()

# Hàm đồng bộ dữ liệu từ Redis xuống MySQL
def sync_to_mysql():
    global stop_sync_thread
    logger.info("Bắt đầu thread đồng bộ dữ liệu từ Redis tới MySQL")
    
    while not stop_sync_thread:
        try:
            # Lấy danh sách các session cần đồng bộ
            session_keys = redis_client.keys("session:*:count")
            
            if session_keys:
                logger.info(f"Đang đồng bộ {len(session_keys)} session")
                
                # Khởi tạo kết nối MySQL mới cho thread này
                conn = get_mysql_connection()
                
                for key in session_keys:
                    session_id = key.decode('utf-8').split(':')[1]
                    
                    # Lấy số lượng câu hỏi từ Redis
                    redis_count = int(redis_client.get(f"session:{session_id}:count") or 0)
                    
                    try:
                        with conn.cursor() as cursor:
                            # Kiểm tra xem session đã tồn tại trong MySQL chưa
                            cursor.execute("SELECT question_count FROM chat_sessions WHERE session_id = %s", (session_id,))
                            result = cursor.fetchone()
                            
                            if result:
                                # Cập nhật question_count trong MySQL
                                cursor.execute(
                                    "UPDATE chat_sessions SET question_count = %s WHERE session_id = %s",
                                    (redis_count, session_id)
                                )
                            else:
                                # Không thể tìm thấy session trong MySQL (hiếm khi xảy ra)
                                logger.warning(f"Session {session_id} không tồn tại trong MySQL nhưng tồn tại trong Redis")
                            
                        conn.commit()
                    except Exception as e:
                        logger.error(f"Lỗi đồng bộ session {session_id}: {str(e)}")
                
                # Đóng kết nối sau khi hoàn thành
                conn.close()
            
            # Đợi cho đến chu kỳ đồng bộ tiếp theo
            time.sleep(sync_interval)
            
        except Exception as e:
            logger.error(f"Lỗi trong quá trình đồng bộ: {str(e)}")
            time.sleep(30)  # Đợi 30 giây trước khi thử lại

@app.on_event("startup")
async def startup_event():
    """Initialize resources on startup"""
    global rag_chain, sync_thread
    try:
        if rag_chain is None:
            logger.info("Initializing RAG chain...")
            rag_chain = create_rag_chain()
            logger.info("RAG chain initialized successfully")
        else:
            logger.info("RAG chain already initialized")
        
        # Khởi động thread đồng bộ
        sync_thread = threading.Thread(target=sync_to_mysql, daemon=True)
        sync_thread.start()
        logger.info("Đã khởi động thread đồng bộ dữ liệu")
    except Exception as e:
        logger.error(f"Failed to initialize RAG chain: {str(e)}")
        # Continue startup - we'll initialize on first request if needed

@app.get("/")
async def root():
    """Root endpoint to check if the API is running"""
    return {
        "message": "Welcome to Family Menu Suggestion System API",
        "status": "operational"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

@app.post("/new_session")
async def new_session(request: NewSessionRequest):
    """Create a new chat session"""
    session_id = str(uuid.uuid4())  # Tạo session_id mới bằng UUID
    try:
        with mysql_conn.cursor() as cursor:
            cursor.execute("INSERT INTO chat_sessions (session_id, question_count) VALUES (%s, %s)", (session_id, 0))
            mysql_conn.commit()
        # Khởi tạo trong Redis
        redis_client.set(f"session:{session_id}:count", 0, ex=86400)  # TTL 24 giờ
        logger.info(f"New session created: {session_id}")
        return {"session_id": session_id, "message": "New session created successfully"}
    except Exception as e:
        logger.error(f"Error creating new session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating new session: {str(e)}")

@app.post("/query")
async def query(request: QueryRequest):
    """Process a nutrition or menu query using RAG with Gemini translation"""
    global rag_chain

    # If no session_id provided, create new one
    if request.session_id is None:
        session_id = str(uuid.uuid4())
        with mysql_conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO chat_sessions (session_id, user_id, question_count) VALUES (%s, %s, %s)", 
                (session_id, request.user_id, 0)
            )
            mysql_conn.commit()
        redis_client.set(f"session:{session_id}:count", 0, ex=86400)
        logger.info(f"New session created for user {request.user_id}: {session_id}")
    else:
        session_id = request.session_id
        # Verify session belongs to user
        with mysql_conn.cursor() as cursor:
            cursor.execute(
                "SELECT user_id FROM chat_sessions WHERE session_id = %s",
                (session_id,)
            )
            result = cursor.fetchone()
            if not result or str(result['user_id']) != str(request.user_id):
                raise HTTPException(
                    status_code=403, 
                    detail="Not authorized to access this chat session"
                )

    # Kiểm tra session_id có tồn tại không trong Redis
    if not redis_client.exists(f"session:{session_id}:count"):
        # Thử lấy từ MySQL nếu không có trong Redis
        with mysql_conn.cursor() as cursor:
            cursor.execute("SELECT question_count FROM chat_sessions WHERE session_id = %s", (session_id,))
            result = cursor.fetchone()
            if not result:
                raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
            # Khôi phục dữ liệu từ MySQL vào Redis
            redis_client.set(f"session:{session_id}:count", result['question_count'], ex=86400)
    
    logger.info(f"Session ID: {session_id}")

    # Lấy và tăng số câu hỏi trong Redis
    question_count = int(redis_client.get(f"session:{session_id}:count") or 0)
    
    if question_count >= 30:
        raise HTTPException(status_code=429, detail="Giới hạn 30 câu hỏi mỗi phiên đã đạt. Vui lòng bắt đầu phiên mới.")

    # Tăng số lượng câu hỏi ngay lập tức trong Redis
    redis_client.incr(f"session:{session_id}:count")
    
    question = request.question
    logger.info(f"Received query: {question}")
    
    # Ghi lại thời gian bắt đầu xử lý
    start_time = time.time()

    try:
        # Initialize RAG chain if not done during startup
        if rag_chain is None:
            logger.info("Initializing RAG chain on first request...")
            rag_chain = create_rag_chain()
            logger.info("RAG chain initialized successfully on first request")

        # Lấy lịch sử chat từ Redis
        chat_history = redis_client.lrange(f"session:{session_id}:history", 0, -1)
        chat_history_str = "\n".join([msg.decode('utf-8') for msg in chat_history]) if chat_history else ""

        # Phát hiện ngôn ngữ (giả sử câu hỏi bằng tiếng Việt, có thể thêm logic phát hiện sau)
        detected_lang = "vi"  # Để đơn giản, giả định luôn là tiếng Việt

        # Dịch câu hỏi từ tiếng Việt sang tiếng Anh nếu cần
        if detected_lang == "vi":
            question_en = translate_with_gemini(question, "vi", "en")
            logger.info(f"Translated query to English: {question_en}")
        else:
            question_en = question

        # Thêm bối cảnh từ chat history vào prompt
        full_input = "User: " + question_en

        # Thêm độ trễ nhân tạo để mô phỏng thời gian suy nghĩ
        # Chỉ thêm khi không phải câu hỏi bắt đầu phiên chat mới
        if question.lower() != "xin chào" and not question.lower().startswith("hello"):
            await asyncio.sleep(1)  # Độ trễ 1 giây

        # Process the query with history if available
        if chat_history_str:
            response = rag_chain.invoke({"input": full_input, "history": chat_history_str})
        else:
            response = rag_chain.invoke({"input": full_input})

        if isinstance(response, dict) and "answer" in response:
            answer = response["answer"]
        else:
            answer = str(response)

        # Dịch câu trả lời từ tiếng Anh về tiếng Việt nếu câu hỏi gốc là tiếng Việt
        if detected_lang == "vi":
            answer_vi = translate_with_gemini(answer, "en", "vi")
            logger.info(f"Translated answer to Vietnamese: {answer_vi}")
        else:
            answer_vi = answer

        # Lưu câu hỏi và trả lời vào Redis
        redis_client.lpush(f"session:{session_id}:history", f"User: {question}\nAI: {answer_vi}")
        redis_client.ltrim(f"session:{session_id}:history", 0, 9)  # Giới hạn lịch sử 10 tin nhắn cuối
        
        # Lưu thông tin tin nhắn vào Redis để đồng bộ sau
        chat_msg_key = f"session:{session_id}:msg:{int(time.time())}"
        redis_client.hmset(chat_msg_key, {
            "user_id": request.user_id,
            "question": question,
            "answer": answer_vi,
            "timestamp": datetime.now().isoformat()
        })
        redis_client.expire(chat_msg_key, 86400)  # TTL 24 giờ
        
        # Cache tin nhắn cần đồng bộ
        redis_client.sadd(f"session:{session_id}:pending_msgs", chat_msg_key)
        redis_client.expire(f"session:{session_id}:pending_msgs", 86400)
        
        # Tính thời gian xử lý
        processing_time = time.time() - start_time
        logger.info(f"Query processed in {processing_time:.2f} seconds")
        
        logger.info(f"Successfully processed query: {question[:50]}...")
        return {
            "answer": answer_vi,
            "processing_time": processing_time
        }

    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while processing your request: {str(e)}"
        )

@app.get("/sync_now")
async def force_sync():
    """Endpoint để kích hoạt đồng bộ dữ liệu ngay lập tức"""
    try:
        # Lấy danh sách tất cả session có tin nhắn đang chờ đồng bộ
        session_keys = redis_client.keys("session:*:pending_msgs")
        sync_count = 0
        
        if session_keys:
            conn = get_mysql_connection()
            
            for key in session_keys:
                session_id = key.decode('utf-8').split(':')[1]
                pending_msgs = redis_client.smembers(f"session:{session_id}:pending_msgs")
                
                if not pending_msgs:
                    continue
                
                # Cập nhật question_count trong MySQL
                redis_count = int(redis_client.get(f"session:{session_id}:count") or 0)
                with conn.cursor() as cursor:
                    cursor.execute(
                        "UPDATE chat_sessions SET question_count = %s WHERE session_id = %s",
                        (redis_count, session_id)
                    )
                
                # Đồng bộ tất cả tin nhắn đang chờ
                for msg_key in pending_msgs:
                    msg_data = redis_client.hgetall(msg_key.decode('utf-8'))
                    if msg_data:
                        # Chuyển đổi bytes sang str
                        msg = {k.decode('utf-8'): v.decode('utf-8') for k, v in msg_data.items()}
                        
                        try:
                            with conn.cursor() as cursor:
                                cursor.execute(
                                    "INSERT INTO chat_messages (session_id, user_id, question, answer) VALUES (%s, %s, %s, %s)",
                                    (session_id, msg['user_id'], msg['question'], msg['answer'])
                                )
                            # Xóa tin nhắn khỏi danh sách chờ
                            redis_client.srem(f"session:{session_id}:pending_msgs", msg_key)
                            sync_count += 1
                        except Exception as e:
                            logger.error(f"Lỗi đồng bộ tin nhắn {msg_key}: {str(e)}")
            
            conn.commit()
            conn.close()
        
        return {"message": f"Đã đồng bộ thành công {sync_count} tin nhắn"}
    except Exception as e:
        logger.error(f"Lỗi khi đồng bộ dữ liệu: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Lỗi khi đồng bộ dữ liệu: {str(e)}")

@app.on_event("shutdown")
async def shutdown_event():
    """Close connections and stop threads on shutdown"""
    global stop_sync_thread
    
    # Dừng thread đồng bộ
    stop_sync_thread = True
    if sync_thread:
        sync_thread.join(timeout=5)
    
    # Đồng bộ lần cuối trước khi tắt
    try:
        logger.info("Đồng bộ dữ liệu lần cuối trước khi tắt")
        # Gọi hàm đồng bộ một lần nữa
        await force_sync()
    except Exception as e:
        logger.error(f"Lỗi khi đồng bộ dữ liệu lần cuối: {str(e)}")
    
    # Đóng các kết nối
    if mysql_conn:
        mysql_conn.close()
    
    logger.info("Đã đóng tất cả kết nối và dừng các thread")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)