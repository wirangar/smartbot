import logging
from contextlib import contextmanager
from typing import Optional
import psycopg2
import redis
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import logger, DATABASE_URL, REDIS_URL

def get_redis_client() -> Optional[redis.Redis]:
    """ایجاد یا بازگشت کلاینت Redis با مدیریت خطا."""
    try:
        client = redis.from_url(REDIS_URL, decode_responses=True)
        client.ping()
        logger.info("Successfully connected to Redis.")
        return client
    except redis.exceptions.ConnectionError as e:
        logger.error(f"Could not connect to Redis: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error while connecting to Redis: {e}")
        return None

redis_client = None

@contextmanager
def get_db_cursor(commit: bool = True):
 """
 Context manager برای مدیریت اتصال و تراکنش‌های PostgreSQL.
 """
 if not DATABASE_URL:
 logger.critical("DATABASE_URL is not set. Cannot connect to PostgreSQL.")
 raise ValueError("DATABASE_URL is missing.")

 conn = None
 cursor = None
 try:
 conn = psycopg2.connect(DATABASE_URL)
 cursor = conn.cursor()
 logger.debug("Database connection established.")
 yield cursor
 if commit:
 conn.commit()
 logger.debug("Database transaction committed.")
 except psycopg2.DatabaseError as e:
 logger.error(f"Database error: {e}")
 if conn:
 conn.rollback()
 logger.debug("Database transaction rolled back.")
 raise
 except Exception as e:
 logger.error(f"Unexpected error in database connection: {e}")
 raise
 finally:
 if cursor:
 cursor.close()
 if conn:
 conn.close()
 logger.debug("Database connection closed.")

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def setup_database():
 """ایجاد جداول موردنیاز در پایگاه داده اگر وجود نداشته باشند."""
 users_table_sql = """
 CREATE TABLE IF NOT EXISTS users (
 telegram_id BIGINT PRIMARY KEY,
 first_name VARCHAR(255) NOT NULL,
 last_name VARCHAR(255) NOT NULL,
 age INTEGER CHECK (age >= 10 AND age <= 90),
 email VARCHAR(255) NOT NULL,
 language VARCHAR(5) DEFAULT 'en',
 score INTEGER DEFAULT 0,
 registration_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
 );
 CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);
 """
 isee_table_sql = """
 CREATE TABLE IF NOT EXISTS isee_calculations (
 id SERIAL PRIMARY KEY,
 user_id BIGINT REFERENCES users(telegram_id) ON DELETE CASCADE,
 isee_value FLOAT NOT NULL,
 calculation_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
 );
 CREATE INDEX IF NOT EXISTS idx_isee_user_id ON isee_calculations(user_id);
 """
 sessions_table_sql = """
 CREATE TABLE IF NOT EXISTS sessions (
 id SERIAL PRIMARY KEY,
 session_id VARCHAR(255) UNIQUE,
 user_id BIGINT REFERENCES users(telegram_id) ON DELETE CASCADE,
 data JSONB NOT NULL,
 created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
 );
 CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
 """
 try:
 with get_db_cursor() as cursor:
 cursor.execute(users_table_sql)
 cursor.execute(isee_table_sql)
 cursor.execute(sessions_table_sql)
 logger.info("Database tables and indexes checked/created successfully.")
 except Exception as e:
 logger.error(f"Failed to set up database tables: {e}")
 raise

def initialize_connections():
 """مقداردهی اولیه اتصال‌های پایگاه داده و Redis."""
 global redis_client
 try:
 setup_database()
 redis_client = get_redis_client()
 if redis_client is None:
 logger.warning("Redis client not initialized. Some features may not work.")
 except Exception as e:
 logger.critical(f"Failed to initialize connections: {e}")
 raise
