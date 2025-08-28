# src/api/v1/get_users_by_org.py

from fastapi import APIRouter, HTTPException, Depends
from typing import List
from pydantic import BaseModel
from src.core.logger import logger
from src.core.token import token_validator
from src.db_clients.clients import get_db_connection
from src.schemas import UserResponse, GetUsersByOrgResponse

router = APIRouter()


# === Вспомогательная функция: получение разрешений по роли ===
def get_permissions_by_role(cursor, role_id: int) -> List[str]:
    cursor.execute("""
        SELECT p.code 
        FROM role_permissions rp
        JOIN permissions p ON rp.permission_id = p.id
        WHERE rp.role_id = %s
    """, (role_id,))
    return [row[0] for row in cursor.fetchall()]


# === Основной обработчик ===
@router.get(
    "/{organization_id}/users",
    response_model=GetUsersByOrgResponse,
    summary="Get organization's users",
    description="Возвращает список активных пользователей указанной организации с их ролями и разрешениями.",
    tags=["Users"]
)
async def get_users_by_organization(
    organization_id: int,
    token: str = Depends(token_validator)
):
    """
    Получение списка пользователей по organization_id из URL.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Проверка существования организации
        cursor.execute("SELECT id FROM organizations WHERE id = %s", (organization_id,))
        if not cursor.fetchone():
            raise HTTPException(
                status_code=404,
                detail=f"Организация с id={organization_id} не найдена."
            )

        # Получение пользователей организации (не удалённых, активных)
        cursor.execute("""
            SELECT u.id, u.login, u.first_name, u.last_name, u.email, u.role
            FROM users u
            WHERE u.organization_id = %s 
              AND u.is_deleted = false 
              AND u.is_active = true
            ORDER BY u.created_at
        """, (organization_id,))

        users_data = cursor.fetchall()
        users_response = []

        for user_row in users_data:
            user_id, login, first_name, last_name, email, role = user_row

            # Получение ролей через user_roles
            cursor.execute("""
                SELECT r.id, r.name 
                FROM user_roles ur
                JOIN roles r ON ur.role_id = r.id
                WHERE ur.user_id = %s
            """, (user_id,))
            roles = cursor.fetchall()

            all_permissions = set()
            if roles:
                # Используем роли из user_roles
                access_level = roles[0][1]  # первая роль
                for role_id, _ in roles:
                    perms = get_permissions_by_role(cursor, role_id)
                    all_permissions.update(perms)
            else:
                # Fallback на поле role
                access_level = role if role else "user"
                all_permissions.update(["user.view", "user.list"])

            users_response.append(
                UserResponse(
                    login=login,
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    access_level=access_level,
                    permissions=list(all_permissions)
                )
            )

        return GetUsersByOrgResponse(users=users_response)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при получении пользователей организации {organization_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Не удалось получить список пользователей. Повторите попытку позже."
        )
    finally:
        if conn:
            try:
                conn.close()
            except Exception as ex:
                logger.error(f"Ошибка при закрытии соединения с БД: {ex}")