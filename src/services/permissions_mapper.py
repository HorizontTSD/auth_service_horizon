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
            cursor.execute(f"SELECT id, code, description FROM {tables.PERMISSIONS}")
            rows = cursor.fetchall()
            permission_list = [row[1] for row in rows]
            permission_mapping = {row[1]: row[0] for row in rows}
            return {
                "permission_list": permission_list,
                "permission_mapping": permission_mapping
            }
        finally:
            try:
                conn.close()
            except Exception:
                pass

    return await asyncio.to_thread(sync_fetch)
