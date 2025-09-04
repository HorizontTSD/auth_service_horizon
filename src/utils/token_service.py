# src/utils/token_service.py
import logging
from datetime import datetime, timedelta
from fastapi import HTTPException, status
from sqlalchemy import select, update

# Импортируем нужные функции из jwt_utils
from src.utils.jwt_utils import (
    create_access_token,
    create_refresh_token,
    decode_jwt_token,
    # revoke_existing_tokens, # Если revoke_existing_tokens перенесена в jwt_utils, импортируем оттуда
)
from src.models.user_models import RefreshToken, User
from src.session import db_manager
from src.core.configuration.config import settings

logger = logging.getLogger(__name__)


# --- Работа с refresh токенами в БД ---

async def get_refresh_token_from_db(jti: str, user_id: int):
    """Получает refresh токен из БД по jti и user_id."""
    try:
        async with db_manager.get_db_session() as session:
            result = await session.execute(
                select(RefreshToken).where(
                    RefreshToken.jti == jti, RefreshToken.user_id == user_id
                )
            )
            return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Database error fetching refresh token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error",
        )


async def revoke_refresh_token_in_db(jti: str):
    """Помечает refresh токен как отозванный в БД."""
    try:
        async with db_manager.get_db_session() as session:
            await session.execute(
                update(RefreshToken).where(RefreshToken.jti == jti).values(revoked=True)
            )
            await session.commit()
            logger.debug(f"Revoked refresh token jti={jti}")
    except Exception as e:
        logger.error(f"Database error revoking refresh token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error",
        )


async def save_refresh_token_to_db(user_id: int, token: str, jti: str):
    """Сохраняет новый refresh токен в БД."""
    try:
        expires_at = datetime.utcnow() + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
        new_db_token = RefreshToken(
            user_id=user_id,
            token=token,
            jti=jti,
            expires_at=expires_at,
            revoked=False,
        )
        async with db_manager.get_db_session() as session:
            session.add(new_db_token)
            await session.commit()
            logger.debug(f"Saved new refresh token for user_id={user_id}, jti={jti}")
    except Exception as e:
        logger.error(f"Database error saving refresh token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error",
        )


# --- Высокоуровневые функции ---

async def rotate_refresh_token(old_refresh_token: str) -> tuple[str, str]:
    """
    Высокоуровневая функция для ротации refresh токена.
    1. Декодирует старый токен.
    2. Проверяет его в БД.
    3. Отзывает старый.
    4. Создает и сохраняет новый.
    5. Создает новый access токен.
    :return: (new_access_token, new_refresh_token)
    """
    payload = decode_jwt_token(old_refresh_token, expected_type="refresh")
    jti = payload.get("jti")
    user_id_str = payload.get("sub")

    if not jti or not user_id_str:
        logger.warning("Missing jti or sub in refresh token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    try:
        user_id = int(user_id_str)
    except (ValueError, TypeError):
        logger.warning(f"Invalid user_id in refresh token: {user_id_str}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    db_token = await get_refresh_token_from_db(jti, user_id)
    if not db_token:
        logger.warning(f"Refresh token with jti={jti} not found in DB")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    if db_token.revoked:
        logger.warning(f"Refresh token with jti={jti} is revoked")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token revoked"
        )

    if db_token.expires_at < datetime.utcnow():
        logger.warning(f"Refresh token with jti={jti} is expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired"
        )

    await revoke_refresh_token_in_db(jti)
    new_refresh_token_str, new_jti = await create_refresh_token(user_id=user_id)
    await save_refresh_token_to_db(user_id=user_id, token=new_refresh_token_str, jti=new_jti)

    try:
        async with db_manager.get_db_session() as session:
            user_result = await session.execute(select(User).where(User.id == user_id))
            user_obj = user_result.scalar_one_or_none()
            if not user_obj:
                logger.error(f"User with id={user_id} not found during token rotation")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="User data error",
                )

            await session.refresh(user_obj, ["roles"])  
            new_access_token_str = await create_access_token(user_id=user_id)

            return new_access_token_str, new_refresh_token_str

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating new access token during rotation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error generating new tokens",
        )

async def revoke_one_token(session, refresh_token: str):
    """Отзывает один валидный токен"""
    try:
        await validate_token(session, refresh_token)
    except HTTPException:
        raise

    stmt = (
        update(RefreshToken)
        .where(RefreshToken.token == refresh_token)
        .values(revoked=True)
    )
    await session.execute(stmt)


async def validate_token(session, refresh_token: str):
    """Проверяет токен на валидность"""
    stmt = select(RefreshToken).where(RefreshToken.token == refresh_token)
    result = await session.execute(stmt)
    token = result.scalar_one_or_none()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Невалидный токен'
        )
    
    if token.revoked:
        raise HTTPException(
            status_code=status.HTTP_200_OK,
            detail='Токен уже инвалидирован'
        )
    
    if token.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_200_OK,
            detail='У токена закончился срок действия'
        )
