from fastapi import HTTPException
from src.db_clients.clients import get_db_connection
from src.db_clients.config import TablesConfig, RolesConfig
from src.schemas import RegistrationRequest
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

tables = TablesConfig()
roles = RolesConfig()


async def create_org_and_superuser(payload: RegistrationRequest) -> dict:
    organization_name=payload.organization_name
    organization_email=payload.organization_email
    superuser_login=payload.superuser_login
    superuser_first_name=payload.superuser_first_name
    superuser_last_name=payload.superuser_last_name
    superuser_email=payload.superuser_email
    superuser_password=payload.superuser_password
    verify_superuser_email=payload.verify_superuser_email
    verify_organization_email=payload.verify_organization_email

    conn = get_db_connection()
    try:
        cur = conn.cursor()

        if verify_organization_email:
            cur.execute(f"SELECT EXISTS(SELECT 1 FROM {tables.ORGANIZATIONS} WHERE email=%s)", (organization_email,))
            if cur.fetchone()[0]:
                raise HTTPException(
                    status_code=409,
                    detail=f"Организация с email {organization_email} уже существует"
                )

        if verify_superuser_email:
            cur.execute(f"SELECT EXISTS(SELECT 1 FROM {tables.USERS} WHERE email=%s)", (superuser_email,))
            if cur.fetchone()[0]:
                raise HTTPException(
                    status_code=409,
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

            superuser_hashed_password = pwd_context.hash(superuser_password)

            # Создание суперюзера
            cur.execute(
                f"""
                INSERT INTO {tables.USERS} 
                (organization_id, login, first_name, last_name, email, password)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (org_id, superuser_login, superuser_first_name,
                 superuser_last_name, superuser_email, superuser_hashed_password)
            )
            superuser_id = cur.fetchone()[0]

            # Обновление владельца организации
            cur.execute(
                f"UPDATE {tables.ORGANIZATIONS} SET owner_id=%s WHERE id=%s",
                (superuser_id, org_id)
            )

            # Присвоение суперюзеру роли superuser (id=1)
            cur.execute("SELECT id FROM roles WHERE name=%s", (roles.SUPERUSER,))
            superuser_role_id = cur.fetchone()[0]

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
