import logging
from fastapi import FastAPI, HTTPException
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
mysql_conn = pymysql.connect(
    host=os.getenv("MYSQL_HOST"),
    user=os.getenv("MYSQL_USER"),
    password=os.getenv("MYSQL_PASSWORD"),
    database=os.getenv("MYSQL_DATABASE"),
    cursorclass=pymysql.cursors.DictCursor
)

@app.on_event("startup")
async def startup_event():
    """Initialize resources on startup"""
    global rag_chain
    try:
        logger.info("Initializing RAG chain...")
        rag_chain = create_rag_chain()
        logger.info("RAG chain initialized successfully")
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

import uuid
@app.post("/new_session")
async def new_session(request: NewSessionRequest):
    """Create a new chat session"""
    session_id = str(uuid.uuid4())  # Tạo session_id mới bằng UUID
    try:
        with mysql_conn.cursor() as cursor:
            cursor.execute("INSERT INTO chat_sessions (session_id) VALUES (%s)", (session_id,))
            mysql_conn.commit()
        redis_client.set(f"session:{session_id}:count", 0, ex=86400)
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
                "INSERT INTO chat_sessions (session_id, user_id) VALUES (%s, %s)", 
                (session_id, request.user_id)
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
            if not result or result[0] != request.user_id:
                raise HTTPException(
                    status_code=403, 
                    detail="Not authorized to access this chat session"
                )

    # Kiểm tra session_id có tồn tại không
    if not redis_client.exists(f"session:{session_id}:count"):
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    
    logger.info(f"Session ID: {session_id}")

    # Kiểm tra số câu hỏi trong phiên từ Redis
    question_count = redis_client.get(f"session:{session_id}:count")
    if question_count is None:
        # Khởi tạo session mới
        with mysql_conn.cursor() as cursor:
            cursor.execute("INSERT INTO chat_sessions (session_id) VALUES (%s)", (session_id,))
            mysql_conn.commit()
        redis_client.set(f"session:{session_id}:count", 0, ex=86400)  # TTL 24 giờ
        question_count = 0
    else:
        question_count = int(question_count)

    if question_count >= 30:
        raise HTTPException(status_code=429, detail="Giới hạn 30 câu hỏi mỗi phiên đã đạt. Vui lòng bắt đầu phiên mới.")

    question = request.question
    logger.info(f"Received query: {question}")

    try:
        # Initialize RAG chain if not done during startup
        if rag_chain is None:
            logger.info("Initializing RAG chain on first request...")
            rag_chain = create_rag_chain()

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
        redis_client.incr(f"session:{session_id}:count")

        # Lưu vào MySQL
        with mysql_conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO chat_messages (session_id, user_id, question, answer) VALUES (%s, %s, %s, %s)",
                (session_id, request.user_id, question, answer_vi)
            )
            mysql_conn.commit()

        logger.info(f"Successfully processed query: {question[:50]}...")
        return {"answer": answer_vi}

    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while processing your request: {str(e)}"
        )

@app.on_event("shutdown")
async def shutdown_event():
    """Close MySQL connection on shutdown"""
    mysql_conn.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)