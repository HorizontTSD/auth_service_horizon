import asyncio
from src.db_clients.clients import get_db_connection
from src.db_clients.config import TablesConfig

tables = TablesConfig()

async def fetch_permissions_mapping():
    def sync_fetch():
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(f"SELECT code FROM {tables.PERMISSIONS}")
                    rows = cursor.fetchall()
                    return {"permissions": [row[0] for row in rows]}
        except Exception as e:
            raise ConnectionError(f"DB operation failed: {e}")

    return await asyncio.to_thread(sync_fetch)

