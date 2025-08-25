import asyncio
from src.db_clients.clients import get_db_connection
from src.db_clients.config import TablesConfig

tables = TablesConfig()

async def fetch_permissions_mapping():
    def sync_fetch():
        try:
            conn = get_db_connection()
        except Exception as e:
            raise ConnectionError(f"Failed to connect to DB: {e}")
        try:
            cursor = conn.cursor()
            cursor.execute(f"SELECT code FROM {tables.PERMISSIONS}")
            rows = cursor.fetchall()
            permission_list = [row[0] for row in rows]
            return {
                "permissions": permission_list
            }
        finally:
            try:
                conn.close()
            except Exception:
                pass

    return await asyncio.to_thread(sync_fetch)
