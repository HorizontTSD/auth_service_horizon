# src/services/check_test_conn.py
import asyncio
from src.db_clients.clients import get_db_connection
from src.db_clients.config import TablesConfig

tables = TablesConfig()

async def check_tables_info():
    def sync_check():
        result = {}
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    for table_name in tables.__dict__.values():
                        try:
                            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                            count = cursor.fetchone()[0]
                            result[table_name] = f"Connection OK, rows: {count}"
                        except Exception as e:
                            result[table_name] = f"Error accessing table: {e}"
        except Exception as e:
            raise ConnectionError(f"Failed to connect or query DB: {e}")
        return result

    return await asyncio.to_thread(sync_check)