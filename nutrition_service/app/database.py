import os
import pymysql
import redis
from dotenv import load_dotenv
# Kết nối cơ sở dữ liệu:
# Load environment variables
load_dotenv()

def get_mysql_connection():
    """Get MySQL connection."""
    return pymysql.connect(
        host=os.getenv("MYSQL_HOST", "localhost"),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),
        database=os.getenv("MYSQL_DATABASE", "nutrition_advisor"),
        cursorclass=pymysql.cursors.DictCursor
    )

def get_redis_client():
    """Get Redis client."""
    return redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        db=int(os.getenv("REDIS_DB", 0))
    )