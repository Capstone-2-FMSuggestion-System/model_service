import logging
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import sys
import json
from dotenv import load_dotenv
from typing import Dict, Any, List, Optional
import redis
import pymysql
import asyncio
import time
import threading
import uuid
from datetime import datetime

# Add the parent directory to sys.path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.prompt import create_chat_chain, create_meal_suggestion_chain
from src.product_matching import ProductMatcher
from app.models import (HealthInfo, MealPreferences, MealSuggestionRequest, 
                      QueryRequest, NewSessionRequest)
from app.database import get_mysql_connection, get_redis_client

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Nutrition Advisor & Menu Suggestion System",
    description="API for nutrition counseling and meal suggestions using Mistral LLM with Ollama",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize global variables
chat_chain = None
meal_suggestion_chain = None
product_matcher = None
redis_client = None
mysql_conn = None

# Sync variables
sync_interval = int(os.getenv("SYNC_INTERVAL", "300"))
sync_thread = None
stop_sync_thread = False

# Sync function for Redis to MySQL
def sync_to_mysql():
    # Implement sync function as shown in the artifacts earlier
    pass

@app.on_event("startup")
async def startup_event():
    """Initialize resources on startup"""
    global chat_chain, meal_suggestion_chain, product_matcher, redis_client, mysql_conn, sync_thread
    try:
        # Initialize Redis
        redis_client = get_redis_client()
        
        # Initialize MySQL
        mysql_conn = get_mysql_connection()
        
        # Initialize Mistral chains
        if chat_chain is None:
            logger.info("Initializing chat chain...")
            chat_chain = create_chat_chain()
            logger.info("Chat chain initialized successfully")
        
        if meal_suggestion_chain is None:
            logger.info("Initializing meal suggestion chain...")
            meal_suggestion_chain = create_meal_suggestion_chain()
            logger.info("Meal suggestion chain initialized successfully")
        
        # Initialize Product Matcher
        product_matcher = ProductMatcher()
        
        # Start sync thread
        sync_thread = threading.Thread(target=sync_to_mysql, daemon=True)
        sync_thread.start()
        logger.info("Data sync thread started")
    except Exception as e:
        logger.error(f"Error initializing resources: {str(e)}")

# Implement endpoints like /new_session, /nutrition/advice, /nutrition/meal-suggestion etc.
# as shown in the artifacts earlier

@app.post("/new_session")
async def new_session(request: NewSessionRequest):
    """Create a new chat session"""
    session_id = str(uuid.uuid4())  # Tạo session_id mới bằng UUID
    try:
        with mysql_conn.cursor() as cursor:
            user_id_value = request.user_id if request.user_id is not None else None
            cursor.execute(
                "INSERT INTO chat_sessions (session_id, user_id, question_count) VALUES (%s, %s, %s)", 
                (session_id, user_id_value, 0)
            )
            mysql_conn.commit()
        # Khởi tạo trong Redis
        redis_client.set(f"session:{session_id}:count", 0, ex=86400)  # TTL 24 giờ
        logger.info(f"New session created: {session_id}")
        return {"session_id": session_id, "message": "New session created successfully"}
    except Exception as e:
        logger.error(f"Error creating new session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating new session: {str(e)}")

@app.post("/nutrition/advice")
async def nutrition_advice(request: QueryRequest):
    """Process a nutrition query using Mistral LLM"""
    global nutrition_chain
    
    # Validate session or create new one
    session_id = await validate_or_create_session(request.session_id, request.user_id)
    
    # Get and increment question count
    question_count = int(redis_client.get(f"session:{session_id}:count") or 0)
    
    if question_count >= 30:
        raise HTTPException(status_code=429, detail="Giới hạn 30 câu hỏi mỗi phiên đã đạt. Vui lòng bắt đầu phiên mới.")
    
    # Increment question count immediately
    redis_client.incr(f"session:{session_id}:count")
    
    question = request.question
    logger.info(f"Received nutrition query: {question}")
    
    # Start processing timer
    start_time = time.time()
    
    try:
        # Initialize nutrition chain if not done during startup
        if nutrition_chain is None:
            logger.info("Khởi tạo nutrition chain on first request...")
            nutrition_chain = create_nutrition_chain()
            logger.info("Nutrition chain đã khởi tạo thành công on first request")
        
        # Get chat history from Redis
        chat_history = redis_client.lrange(f"session:{session_id}:history", 0, -1)
        chat_history_str = "\n".join([msg.decode('utf-8') for msg in chat_history]) if chat_history else ""
        
        # Format health info
        health_info_str = ""
        if request.health_info:
            health_info_str = json.dumps(request.health_info.dict(), ensure_ascii=False)
        
        # Add artificial delay for better user experience
        if question.lower() != "xin chào" and not question.lower().startswith("hello"):
            await asyncio.sleep(1)  # Delay 1 second
        
        # Process the query with history if available
        response = nutrition_chain.invoke({
            "input": question,
            "history": chat_history_str,
            "health_info": health_info_str
        })
        
        if isinstance(response, dict) and "answer" in response:
            answer = response["answer"]
        else:
            answer = str(response)
        
        # Save question and answer to Redis
        redis_client.lpush(f"session:{session_id}:history", f"User: {question}\nAI: {answer}")
        redis_client.ltrim(f"session:{session_id}:history", 0, 9)  # Limit history to last 10 messages
        
        # Save message info to Redis for later sync
        chat_msg_key = f"session:{session_id}:msg:{int(time.time())}"
        message_data = {
            "question": question,
            "answer": answer,
            "timestamp": datetime.now().isoformat()
        }
        
        # Add user_id to data if available
        if request.user_id is not None:
            message_data["user_id"] = request.user_id
        
        redis_client.hmset(chat_msg_key, message_data)
        redis_client.expire(chat_msg_key, 86400)  # TTL 24 hours
        
        # Cache messages to sync
        redis_client.sadd(f"session:{session_id}:pending_msgs", chat_msg_key)
        redis_client.expire(f"session:{session_id}:pending_msgs", 86400)
        
        # Calculate processing time
        processing_time = time.time() - start_time
        logger.info(f"Query processed in {processing_time:.2f} seconds")
        
        return {
            "answer": answer,
            "processing_time": processing_time
        }
    
    except Exception as e:
        logger.error(f"Error processing nutrition query: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while processing your request: {str(e)}"
        )

@app.post("/nutrition/meal-suggestion")
async def meal_suggestion(request: MealSuggestionRequest):
    """Get meal suggestions based on health information and preferences"""
    global meal_suggestion_chain, product_matcher
    
    # Validate session or create new one
    session_id = await validate_or_create_session(request.session_id, request.user_id)
    
    logger.info(f"Received meal suggestion request for session {session_id}")
    
    # Start processing timer
    start_time = time.time()
    
    try:
        # Initialize meal suggestion chain if not done during startup
        if meal_suggestion_chain is None:
            logger.info("Khởi tạo meal suggestion chain on first request...")
            meal_suggestion_chain = create_meal_suggestion_chain()
            logger.info("Meal suggestion chain đã khởi tạo thành công on first request")
        
        # Initialize product matcher if not done during startup
        if product_matcher is None:
            logger.info("Khởi tạo product matcher on first request...")
            product_matcher = ProductMatcher()
            logger.info("Product matcher đã khởi tạo thành công on first request")
        
        # Format health info
        health_info_str = json.dumps(request.health_info.dict(), ensure_ascii=False)
        
        # Format preferences
        preferences_str = json.dumps(request.preferences.dict(), ensure_ascii=False)
        
        # Create a query prompt
        query_prompt = f"Gợi ý món ăn phù hợp cho người có thông tin sức khỏe như đã cung cấp. Size gia đình: {request.family_size} người."
        
        # Process the query
        response = meal_suggestion_chain.invoke({
            "input": query_prompt,
            "health_info": health_info_str,
            "preferences": preferences_str
        })
        
        # Parse the response to get structured data
        if isinstance(response, str):
            meal_data = parse_json_response(response)
        else:
            meal_data = parse_json_response(str(response))
        
        # Process ingredients to find matching products
        meals = meal_data.get("meals", [])
        processed_meals = product_matcher.bulk_process_meals(meals)
        
        # Save meal suggestion to database
        try:
            with mysql_conn.cursor() as cursor:
                suggestion_data = {
                    "suggestion": processed_meals,
                    "request": {
                        "health_info": request.health_info.dict(),
                        "preferences": request.preferences.dict(),
                        "family_size": request.family_size
                    }
                }
                
                # Insert suggestion data
                cursor.execute(
                    "INSERT INTO meal_suggestions (user_id, session_id, suggestion_data, health_data) VALUES (%s, %s, %s, %s)",
                    (
                        request.user_id,
                        session_id,
                        json.dumps(suggestion_data, ensure_ascii=False),
                        json.dumps(request.health_info.dict(), ensure_ascii=False)
                    )
                )
                mysql_conn.commit()
        except Exception as e:
            logger.error(f"Error saving meal suggestion: {str(e)}")
            # Continue even if saving fails
        
        # Calculate processing time
        processing_time = time.time() - start_time
        logger.info(f"Meal suggestion processed in {processing_time:.2f} seconds")
        
        # Return processed data
        return {
            "analysis": meal_data.get("analysis", ""),
            "suggestions": processed_meals.get("processed_meals", []),
            "advice": meal_data.get("advice", ""),
            "processing_time": processing_time
        }
    
    except Exception as e:
        logger.error(f"Error processing meal suggestion: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while processing your meal suggestion request: {str(e)}"
        )

@app.get("/chat-history/{session_id}")
async def get_chat_history(session_id: str):
    """Get chat history for a specific session"""
    try:
        # Check if session exists
        with mysql_conn.cursor() as cursor:
            cursor.execute("SELECT * FROM chat_sessions WHERE session_id = %s", (session_id,))
            session = cursor.fetchone()
            if not session:
                raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
            
            # Get chat history from MySQL, ordered by most recent first
            cursor.execute(
                "SELECT question, answer, timestamp FROM chat_messages WHERE session_id = %s ORDER BY timestamp DESC", 
                (session_id,)
            )
            messages = cursor.fetchall()
            
            # If no messages in MySQL, try Redis
            if not messages:
                chat_history = redis_client.lrange(f"session:{session_id}:history", 0, -1)
                
                if chat_history:
                    # Convert format
                    messages = []
                    for msg in chat_history:
                        msg_str = msg.decode('utf-8')
                        # Split into question and answer
                        parts = msg_str.split("\nAI: ")
                        if len(parts) == 2:
                            question = parts[0].replace("User: ", "")
                            answer = parts[1]
                            messages.append({
                                "question": question,
                                "answer": answer,
                                "timestamp": None  # Redis doesn't store timestamp
                            })
            
            # Format messages
            formatted_messages = []
            for msg in messages:
                formatted_msg = {
                    "question": msg["question"],
                    "answer": msg["answer"]
                }
                # Add timestamp if available
                if "timestamp" in msg and msg["timestamp"]:
                    formatted_msg["timestamp"] = msg["timestamp"].isoformat()
                
                formatted_messages.append(formatted_msg)
            
            return {
                "session_id": session_id,
                "messages": formatted_messages,
                "question_count": session["question_count"]
            }
    except Exception as e:
        logger.error(f"Error fetching chat history: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while fetching chat history: {str(e)}"
        )

@app.get("/meal-history/{user_id}")
async def get_meal_history(user_id: int):
    """Get meal suggestion history for a specific user"""
    try:
        with mysql_conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, session_id, suggestion_data, health_data, timestamp FROM meal_suggestions WHERE user_id = %s ORDER BY timestamp DESC", 
                (user_id,)
            )
            suggestions = cursor.fetchall()
            
            formatted_suggestions = []
            for suggestion in suggestions:
                try:
                    suggestion_data = json.loads(suggestion["suggestion_data"])
                    health_data = json.loads(suggestion["health_data"])
                    
                    formatted_suggestion = {
                        "id": suggestion["id"],
                        "session_id": suggestion["session_id"],
                        "timestamp": suggestion["timestamp"].isoformat(),
                        "health_info": health_data,
                        "meals": suggestion_data.get("suggestion", {}).get("processed_meals", [])
                    }
                    
                    formatted_suggestions.append(formatted_suggestion)
                except Exception as e:
                    logger.error(f"Error parsing suggestion data: {str(e)}")
                    continue
            
            return {
                "user_id": user_id,
                "suggestions": formatted_suggestions
            }
    except Exception as e:
        logger.error(f"Error fetching meal history: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while fetching meal history: {str(e)}"
        )

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Nutrition Advisor API", "status": "operational"}

@app.on_event("shutdown")
async def shutdown_event():
    """Close connections on shutdown"""
    global stop_sync_thread
    stop_sync_thread = True
    if sync_thread:
        sync_thread.join(timeout=5)
    if mysql_conn:
        mysql_conn.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)