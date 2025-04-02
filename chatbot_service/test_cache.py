#!/usr/bin/env python3
"""
Script kiểm tra hệ thống cache và đồng bộ dữ liệu cho chatbot service
"""

import requests
import time
import redis
import pymysql
import os
from dotenv import load_dotenv
import argparse
import uuid
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

# Đảm bảo biến môi trường được tải
load_dotenv()

# Lấy URL API chatbot từ biến môi trường hoặc sử dụng giá trị mặc định
CHATBOT_API_URL = "http://localhost:8001"

# Kết nối với Redis
redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", "6379")),
    db=int(os.getenv("REDIS_DB", "0"))
)

# Hàm kết nối MySQL
def get_mysql_connection():
    return pymysql.connect(
        host=os.getenv("MYSQL_HOST", "localhost"),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),
        database=os.getenv("MYSQL_DATABASE", "family_menu_db"),
        cursorclass=pymysql.cursors.DictCursor
    )

def create_session():
    """Tạo một phiên chat mới và trả về session_id"""
    try:
        response = requests.post(f"{CHATBOT_API_URL}/new_session")
        response.raise_for_status()
        return response.json()["session_id"]
    except Exception as e:
        print(f"Lỗi khi tạo phiên chat mới: {str(e)}")
        # Fallback để tạo session ID nếu API không hoạt động
        return str(uuid.uuid4())

def send_message(session_id, user_id, question):
    """Gửi câu hỏi đến chatbot và trả về phản hồi"""
    try:
        response = requests.post(
            f"{CHATBOT_API_URL}/query",
            json={"question": question, "session_id": session_id, "user_id": user_id}
        )
        response.raise_for_status()
        return response.json()["answer"]
    except Exception as e:
        print(f"Lỗi khi gửi tin nhắn: {str(e)}")
        return f"Lỗi: {str(e)}"

def get_session_stats(session_id):
    """Lấy thống kê về phiên chat từ Redis và MySQL"""
    redis_count = redis_client.get(f"session:{session_id}:count")
    redis_count = int(redis_count) if redis_count else 0
    
    # Lấy tin nhắn từ Redis
    redis_messages = redis_client.lrange(f"session:{session_id}:history", 0, -1)
    redis_messages = [msg.decode('utf-8') for msg in redis_messages] if redis_messages else []
    
    # Lấy tin nhắn đang chờ đồng bộ
    pending_msgs = redis_client.smembers(f"session:{session_id}:pending_msgs")
    pending_count = len(pending_msgs) if pending_msgs else 0
    
    # Lấy dữ liệu từ MySQL
    mysql_count = 0
    mysql_messages = []
    
    try:
        conn = get_mysql_connection()
        
        with conn.cursor() as cursor:
            # Lấy question_count từ bảng chat_sessions
            cursor.execute(
                "SELECT question_count FROM chat_sessions WHERE session_id = %s",
                (session_id,)
            )
            result = cursor.fetchone()
            if result:
                mysql_count = result['question_count']
            
            # Lấy tin nhắn từ bảng chat_messages
            cursor.execute(
                "SELECT question, answer, timestamp FROM chat_messages WHERE session_id = %s ORDER BY timestamp DESC",
                (session_id,)
            )
            mysql_messages = cursor.fetchall()
        
        conn.close()
    except Exception as e:
        print(f"Lỗi khi truy vấn MySQL: {str(e)}")
    
    return {
        "redis_count": redis_count,
        "redis_messages": redis_messages,
        "pending_count": pending_count,
        "mysql_count": mysql_count,
        "mysql_messages": mysql_messages
    }

def force_sync():
    """Kích hoạt đồng bộ dữ liệu ngay lập tức"""
    try:
        response = requests.get(f"{CHATBOT_API_URL}/sync_now")
        response.raise_for_status()
        return response.json()["message"]
    except Exception as e:
        print(f"Lỗi khi kích hoạt đồng bộ: {str(e)}")
        return f"Lỗi: {str(e)}"

def simulate_chat_session(session_id=None, user_id=1, message_count=5, delay=1):
    """Mô phỏng một phiên chat với nhiều tin nhắn"""
    if not session_id:
        session_id = create_session()
        print(f"Đã tạo phiên chat mới với ID: {session_id}")
    
    questions = [
        "Bạn có thể giới thiệu về chế độ ăn uống lành mạnh không?",
        "Tôi muốn giảm cân, nên ăn gì?",
        "Có thực đơn nào phù hợp cho người cao huyết áp?",
        "Tôi nên ăn gì để tăng cơ bắp?",
        "Thực phẩm nào giàu vitamin C?",
        "Có thể gợi ý món ăn cho bữa sáng không?",
        "Làm thế nào để có một chế độ ăn cân bằng?",
        "Trái cây nào tốt cho sức khỏe?",
        "Tôi nên ăn bao nhiêu calo mỗi ngày?",
        "Có món ăn nào dễ làm cho người bận rộn?"
    ]
    
    # Đảm bảo số lượng câu hỏi không vượt quá danh sách có sẵn
    message_count = min(message_count, len(questions))
    
    print(f"\n=== Bắt đầu mô phỏng phiên chat với {message_count} tin nhắn ===")
    print(f"Session ID: {session_id}")
    print(f"User ID: {user_id}")
    
    for i in range(message_count):
        question = questions[i]
        print(f"\nTin nhắn {i+1}/{message_count}")
        print(f"Câu hỏi: {question}")
        
        # Gửi tin nhắn
        answer = send_message(session_id, user_id, question)
        print(f"Trả lời: {answer[:100]}..." if len(answer) > 100 else f"Trả lời: {answer}")
        
        # Lấy thống kê Redis
        redis_count = redis_client.get(f"session:{session_id}:count")
        print(f"Redis question_count: {redis_count.decode('utf-8') if redis_count else 0}")
        
        # Nghỉ giữa các tin nhắn
        if i < message_count - 1:
            time.sleep(delay)
    
    # Lấy thống kê chi tiết sau khi hoàn thành
    stats = get_session_stats(session_id)
    
    print("\n=== Thống kê sau khi hoàn thành phiên chat ===")
    print(f"Redis question_count: {stats['redis_count']}")
    print(f"MySQL question_count: {stats['mysql_count']}")
    print(f"Số tin nhắn đang chờ đồng bộ: {stats['pending_count']}")
    print(f"Số tin nhắn đã lưu trong MySQL: {len(stats['mysql_messages'])}")
    
    return session_id

def test_parallel_sessions(user_count=3, messages_per_user=3):
    """Kiểm tra nhiều phiên chat song song"""
    print(f"\n=== Kiểm tra {user_count} phiên chat song song ===")
    
    sessions = []
    
    # Tạo nhiều phiên chat
    with ThreadPoolExecutor(max_workers=user_count) as executor:
        future_to_user = {
            executor.submit(simulate_chat_session, None, user_id+1, messages_per_user, 0.5): user_id+1
            for user_id in range(user_count)
        }
        
        for future in as_completed(future_to_user):
            user_id = future_to_user[future]
            try:
                session_id = future.result()
                sessions.append((user_id, session_id))
                print(f"Người dùng {user_id} đã hoàn thành phiên chat với session_id: {session_id}")
            except Exception as e:
                print(f"Người dùng {user_id} gặp lỗi: {str(e)}")
    
    return sessions

def main():
    parser = argparse.ArgumentParser(description="Kiểm tra hệ thống cache và đồng bộ chatbot")
    parser.add_argument("--session", type=str, help="Session ID hiện có để kiểm tra")
    parser.add_argument("--user", type=int, default=1, help="ID người dùng")
    parser.add_argument("--messages", type=int, default=5, help="Số lượng tin nhắn để gửi")
    parser.add_argument("--delay", type=float, default=1, help="Độ trễ giữa các tin nhắn (giây)")
    parser.add_argument("--parallel", type=int, help="Số phiên chat song song để kiểm tra")
    parser.add_argument("--sync", action="store_true", help="Kích hoạt đồng bộ ngay lập tức")
    parser.add_argument("--stats", type=str, help="Chỉ hiển thị thống kê cho session_id đã cho")
    
    args = parser.parse_args()
    
    if args.stats:
        # Chỉ hiển thị thống kê cho session_id
        stats = get_session_stats(args.stats)
        print(f"\n=== Thống kê cho phiên {args.stats} ===")
        print(f"Redis question_count: {stats['redis_count']}")
        print(f"MySQL question_count: {stats['mysql_count']}")
        print(f"Số tin nhắn đang chờ đồng bộ: {stats['pending_count']}")
        print(f"Số tin nhắn trong MySQL: {len(stats['mysql_messages'])}")
        return
    
    if args.sync:
        # Kích hoạt đồng bộ ngay lập tức
        result = force_sync()
        print(f"\n=== Kích hoạt đồng bộ ===")
        print(result)
        return
    
    if args.parallel:
        # Kiểm tra nhiều phiên chat song song
        sessions = test_parallel_sessions(args.parallel, args.messages)
        
        # Hiển thị thống kê cho tất cả các phiên
        time.sleep(2)  # Chờ để Redis có thể cập nhật
        
        print("\n=== Thống kê cho tất cả các phiên ===")
        for user_id, session_id in sessions:
            stats = get_session_stats(session_id)
            print(f"\nUser {user_id} - Session {session_id}:")
            print(f"Redis question_count: {stats['redis_count']}")
            print(f"MySQL question_count: {stats['mysql_count']}")
            print(f"Số tin nhắn đang chờ đồng bộ: {stats['pending_count']}")
        
        # Kích hoạt đồng bộ và hiển thị lại thống kê
        if args.sync or input("\nKích hoạt đồng bộ ngay? (y/n): ").lower() == 'y':
            result = force_sync()
            print(result)
            
            time.sleep(2)  # Chờ để MySQL có thể cập nhật
            
            print("\n=== Thống kê sau khi đồng bộ ===")
            for user_id, session_id in sessions:
                stats = get_session_stats(session_id)
                print(f"\nUser {user_id} - Session {session_id}:")
                print(f"Redis question_count: {stats['redis_count']}")
                print(f"MySQL question_count: {stats['mysql_count']}")
                print(f"Số tin nhắn đang chờ đồng bộ: {stats['pending_count']}")
                print(f"Số tin nhắn trong MySQL: {len(stats['mysql_messages'])}")
    else:
        # Mô phỏng một phiên chat
        session_id = simulate_chat_session(args.session, args.user, args.messages, args.delay)
        
        # Hỏi người dùng có muốn kích hoạt đồng bộ không
        if args.sync or input("\nKích hoạt đồng bộ ngay? (y/n): ").lower() == 'y':
            result = force_sync()
            print(result)
            
            time.sleep(2)  # Chờ để MySQL có thể cập nhật
            
            # Hiển thị thống kê sau khi đồng bộ
            stats = get_session_stats(session_id)
            print("\n=== Thống kê sau khi đồng bộ ===")
            print(f"Redis question_count: {stats['redis_count']}")
            print(f"MySQL question_count: {stats['mysql_count']}")
            print(f"Số tin nhắn đang chờ đồng bộ: {stats['pending_count']}")
            print(f"Số tin nhắn trong MySQL: {len(stats['mysql_messages'])}")

if __name__ == "__main__":
    main() 