import psycopg2
import redis
import logging
from contextlib import contextmanager

from src.config import DATABASE_URL, REDIS_URL, logger

# --- Redis Connection ---
try:
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    redis_client.ping()
    logger.info("Successfully connected to Redis.")
except redis.exceptions.ConnectionError as e:
    logger.error(f"Could not connect to Redis: {e}")
    redis_client = None

# --- PostgreSQL Connection ---
@contextmanager
def get_db_cursor():
    """Context manager to handle PostgreSQL database connections and transactions."""
    if not DATABASE_URL:
        logger.error("DATABASE_URL is not set. Cannot connect to PostgreSQL.")
        yield None
        return

    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        logger.info("Database connection established.")
        cursor = conn.cursor()
        yield cursor
        conn.commit()
    except psycopg2.DatabaseError as e:
        logger.error(f"Database error: {e}")
        if conn:
            conn.rollback()
        # Re-raise the exception to be handled by the caller
        raise
    finally:
        if conn:
            cursor.close()
            conn.close()
            logger.info("Database connection closed.")

def setup_database():
    """Creates the necessary tables in the database if they don't exist."""
    users_table_sql = """
    CREATE TABLE IF NOT EXISTS users (
        telegram_id BIGINT PRIMARY KEY,
        first_name VARCHAR(255),
        last_name VARCHAR(255),
        age INTEGER,
        email VARCHAR(255),
        language VARCHAR(5) DEFAULT 'fa',
        score INTEGER DEFAULT 0,
        is_subscribed_to_notifications BOOLEAN DEFAULT FALSE,
        registration_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    """
    isee_table_sql = """
    CREATE TABLE IF NOT EXISTS isee_calculations (
        id SERIAL PRIMARY KEY,
        user_id BIGINT REFERENCES users(telegram_id),
        isee_value FLOAT,
        calculation_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    """
    feedback_table_sql = """
    CREATE TABLE IF NOT EXISTS feedback (
        id SERIAL PRIMARY KEY,
        user_id BIGINT REFERENCES users(telegram_id),
        is_helpful BOOLEAN,
        message_text TEXT,
        timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    """
    try:
        with get_db_cursor() as cursor:
            if cursor:
                cursor.execute(users_table_sql)
                cursor.execute(isee_table_sql)
                cursor.execute(feedback_table_sql)
                logger.info("Database tables checked/created successfully.")
    except Exception as e:
        logger.error(f"Failed to set up database tables: {e}")

# --- Helper Functions ---
def get_redis_client():
    """Returns the Redis client instance."""
    return redis_client
