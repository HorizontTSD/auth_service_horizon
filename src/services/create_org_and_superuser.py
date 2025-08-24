from fastapi import HTTPException
from src.db_clients.clients import get_db_connection
from src.db_clients.config import TablesConfig

tables = TablesConfig()

async def create_org_and_superuser(
        organization_name: str,
        organization_email: str,
        superuser_login: str,
        superuser_first_name: str,
        superuser_last_name: str,
        superuser_email: str,
        superuser_password: str,
        verify_superuser_email: bool = False,
        verify_organization_email: bool = True
) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()

        if verify_organization_email:
            cur.execute(f"SELECT EXISTS(SELECT 1 FROM {tables.ORGANIZATIONS} WHERE email=%s)", (organization_email,))
            if cur.fetchone()[0]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Организация с email {organization_email} уже существует"
                )

        if verify_superuser_email:
            cur.execute(f"SELECT EXISTS(SELECT 1 FROM {tables.USERS} WHERE email=%s)", (superuser_email,))
            if cur.fetchone()[0]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Суперюзер с email {superuser_email} уже существует"
                )

        try:
            # Создание организации
            cur.execute(
                f"""
                INSERT INTO {tables.ORGANIZATIONS} (name, email, owner_id)
                VALUES (%s, %s, NULL)
                RETURNING id
                """,
                (organization_name, organization_email)
            )
            org_id = cur.fetchone()[0]

            # Создание суперюзера
            cur.execute(
                f"""
                INSERT INTO {tables.USERS} 
                (organization_id, login, first_name, last_name, email, password)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (org_id, superuser_login, superuser_first_name, superuser_last_name, superuser_email, superuser_password)
            )
            superuser_id = cur.fetchone()[0]

            # Обновление владельца организации
            cur.execute(
                f"UPDATE {tables.ORGANIZATIONS} SET owner_id=%s WHERE id=%s",
                (superuser_id, org_id)
            )

            # Присвоение суперюзеру роли superuser (id=1)
            superuser_role_id = 1
            cur.execute(
                f"INSERT INTO {tables.USER_ROLES} (user_id, role_id) VALUES (%s, %s)",
                (superuser_id, superuser_role_id)
            )

            conn.commit()
        except Exception:
            conn.rollback()
            raise

        return {
            "status": "success",
            "organization_id": org_id,
            "superuser_id": superuser_id,
            "message": "Организация и суперюзер успешно зарегистрированы"
        }
    finally:
        conn.close()
