# src/api/v1/auth_refresh.py

from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, Body
from pydantic import BaseModel
from typing import Literal
import jwt
import secrets
import hashlib

from src.core.logger import logger
from src.db_clients.clients import get_db_connection
from src.core.configuration.config import settings

router = APIRouter(prefix="/auth", tags=["Auth"])

# === Схемы ===
class RefreshRequest(BaseModel):
    refresh_token: str


class RefreshResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["Bearer"]
    expires_in: int
    refresh_expires_in: int


SECRET_KEY = settings.JWT_SECRET_KEY
ALGORITHM = settings.JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS


def create_jwt_token(subject: str, expires_delta: timedelta, additional_payload: dict = None):
    payload = {
        "sub": subject,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + expires_delta,
    }
    if additional_payload:
        payload.update(additional_payload)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_jwt_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


# === Основной эндпоинт ===
@router.post(
    "/refresh",
    response_model=RefreshResponse,
    summary="Refresh access-token",
    description="""
    Обновляет access-token по refresh-token с ротацией:
    - Проверяет подпись и срок действия refresh-токена
    - Проверяет, что refresh-токен не отозван и существует
    - Помечает старый refresh как revoked
    - Генерирует новый refresh и access
    - Возвращает пару токенов
    """,
)
async def refresh_tokens(request: RefreshRequest = Body(...)):
    refresh_token = request.refresh_token

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Декодируем refresh-токен
        try:
            payload = decode_jwt_token(refresh_token)
        except HTTPException as e:
            logger.warning(f"Invalid or expired refresh token: {e.detail}")
            raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

        jti = payload.get("jti")
        user_id = payload.get("sub")

        if not jti or not user_id:
            logger.warning("Missing jti or sub in refresh token")
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        # Проверяем, существует ли refresh_token в БД и не отозван ли
        cursor.execute("""
            SELECT revoked, expires_at 
            FROM refresh_tokens 
            WHERE jti = %s AND user_id = %s
        """, (jti, user_id))

        result = cursor.fetchone()
        if not result:
            logger.warning(f"Refresh token with jti={jti} not found in DB")
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        revoked, expires_at = result
        if revoked:
            logger.warning(f"Refresh token with jti={jti} is revoked")
            raise HTTPException(status_code=401, detail="Refresh token revoked")

        if datetime.strptime(expires_at, "%Y-%m-%d %H:%M:%S") < datetime.utcnow():
            logger.warning(f"Refresh token with jti={jti} is expired")
            raise HTTPException(status_code=401, detail="Refresh token expired")

        # Помечаем старый refresh как отозванный
        cursor.execute("""
            UPDATE refresh_tokens 
            SET revoked = true 
            WHERE jti = %s
        """, (jti,))
        conn.commit()

        # Генерируем новый jti и refresh-токен
        new_jti = secrets.token_urlsafe(32)
        new_refresh_token = create_jwt_token(
            subject=str(user_id),
            expires_delta=timedelta(days=30),
            additional_payload={"jti": new_jti}
        )

        # Сохраняем новый refresh в БД
        cursor.execute("""
            INSERT INTO refresh_tokens (user_id, token, jti, expires_at, revoked, created_at)
            VALUES (%s, %s, %s, %s, false, %s)
        """, (
            user_id,
            new_refresh_token,
            new_jti,
            (datetime.utcnow() + timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S"),
            datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        ))
        conn.commit()

        # Генерируем новый access-токен
        new_access_token = create_jwt_token(
            subject=str(user_id),
            expires_delta=timedelta(minutes=15)
        )

        logger.info(f"Successfully refreshed tokens for user_id={user_id}")

        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "Bearer",
            "expires_in": 900,
            "refresh_expires_in": 2592000
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during token refresh: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if conn:
            try:
                conn.close()
            except Exception as ex:
                logger.error(f"Error closing DB connection: {ex}")