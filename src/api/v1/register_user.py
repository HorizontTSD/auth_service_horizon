# src/api/v1/register_user.py

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from src.schemas import RegisterUserRequest, RegisterUserResponse
import hashlib
import secrets
from datetime import datetime

from src.core.logger import logger
from src.core.token import token_validator
from src.db_clients.clients import get_db_connection
from src.core.configuration.config import settings

router = APIRouter(prefix="/users", tags=["Users"])

# === Вспомогательные функции ===
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def is_user_superuser(cursor, user_id: int, organization_id: int) -> bool:
    cursor.execute("""
        SELECT u.role 
        FROM users u
        WHERE u.id = %s AND u.organization_id = %s
    """, (user_id, organization_id))
    result = cursor.fetchone()
    if not result:
        return False
    role = result[0]
    return role == "superuser"


def has_permission(cursor, user_id: int, permission_code: str) -> bool:
    cursor.execute("""
        SELECT 1 FROM user_roles ur
        JOIN role_permissions rp ON ur.role_id = rp.role_id
        JOIN permissions p ON rp.permission_id = p.id
        WHERE ur.user_id = %s AND p.code = %s
    """, (user_id, permission_code))
    return cursor.fetchone() is not None


# === Эндпоинт ===
@router.post(
    "/register",
    response_model=RegisterUserResponse,
    summary="Register new user in organization",
    description="""
    Создаёт нового пользователя в текущей организации.
    Доступно только суперпользователю или пользователю с правом user.create.
    """
)
async def register_user(
    request: RegisterUserRequest,
    access_token: str = Depends(token_validator)
):

    try:
        payload = token_validator.decode(access_token)  
        current_user_id = int(payload["sub"])
        organization_id = int(payload["org_id"]) 
    except:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 1. Проверка, что текущий пользователь — суперпользователь или имеет право user.create
        if not is_user_superuser(cursor, current_user_id, organization_id):
            if not has_permission(cursor, current_user_id, "user.create"):
                raise HTTPException(status_code=403, detail="Insufficient permissions")

        # 2. Проверка, что login и email уникальны в организации
        cursor.execute("""
            SELECT id FROM users 
            WHERE organization_id = %s AND (login = %s OR email = %s)
        """, (organization_id, request.login, request.email))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Login or email already exists")

        # 3. Хешируем пароль
        hashed_password = hash_password(request.password)

        # 4. Создаём пользователя
        cursor.execute("""
            INSERT INTO users (
                organization_id, login, password, email, first_name, last_name,
                role, is_active, is_blocked, is_deleted, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, true, false, false, NOW(), NOW())
            RETURNING id
        """, (
            organization_id,
            request.login,
            hashed_password,
            request.email,
            request.first_name,
            request.last_name,
            request.role,
        ))

        new_user_id = cursor.fetchone()[0]
        conn.commit()

        logger.info(f"User {new_user_id} registered by {current_user_id} in org {organization_id}")

        return RegisterUserResponse(
            success=True,
            user_id=new_user_id,
            message="User successfully registered"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during user registration: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to register user")
    finally:
        if conn:
            try:
                conn.close()
            except Exception as ex:
                logger.error(f"Error closing DB connection: {ex}")