import psycopg2
from contextlib import contextmanager
from src.db_clients.config import DBConfig

config = DBConfig()

@contextmanager
def get_db_connection():
    conn = psycopg2.connect(
        dbname=config.DB_NAME,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        host=config.DB_HOST,
        port=config.DB_PORT,
    )
    try:
        yield conn
    finally:
        conn.close()
