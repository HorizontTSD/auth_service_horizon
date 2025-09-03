# src/services/token_refresh_service.py
import logging
from typing import Tuple

from src.utils import jwt_utils, token_service
from src.core.configuration.config import settings
from datetime import datetime

from src.session import db_manager
from src.models.user_models import User, Role
from sqlalchemy import select
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

# --- Метод для полной ротации  ---
async def refresh_tokens_logic(refresh_token_str: str) -> Tuple[str, str, int, int]:
    """
    Сервисная логика для обновления пары access/refresh токенов (полная ротация).
    Отзывает старый refresh токен и выдает новую пару.
    
    Args:
        refresh_token_str: Строка refresh токена JWT.
        
    Returns:
        Кортеж (new_access_token, new_refresh_token, expires_in, refresh_expires_in)
        
    Raises:
        HTTPException: При проблемах с токеном (401) или БД (500).
    """
    try:
        new_access_token, new_refresh_token = await token_service.rotate_refresh_token(refresh_token_str)

        expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        refresh_expires_in = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
        
        logger.info("Tokens successfully refreshed (full rotation) in service layer")
        return new_access_token, new_refresh_token, expires_in, refresh_expires_in

    except Exception as e:
        logger.error(f"Error in full token refresh service logic: {e}", exc_info=True)
        raise 


# --- Метод для обновления только access токена ---
async def rotate_access_token_only_logic(refresh_token_str: str) -> Tuple[str, int]:
    """
    Сервисная логика для обновления ТОЛЬКО access токена.
    Проверяет валидность refresh токена, но НЕ отзывает его и НЕ создает новый refresh токен.
    Используется для "тихого" обновления access токена.
    
    Args:
        refresh_token_str: Строка действующего refresh токена JWT.
        
    Returns:
        Кортеж (new_access_token, expires_in)
        
    Raises:
        HTTPException: При проблемах с токеном (401) или БД (500).
    """
    try:
        # 1. Декодируем и валидируем refresh токен 
        payload = jwt_utils.decode_jwt_token(refresh_token_str, expected_type="refresh")
        
        user_id_str = payload.get("sub")
        jti = payload.get("jti") 

        if not user_id_str:
            logger.warning("Missing 'sub' in refresh token for access-only rotation")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

        try:
            user_id = int(user_id_str)
        except (ValueError, TypeError):
            logger.warning(f"Invalid user_id '{user_id_str}' in refresh token")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

        # 2. Проверяем refresh токен в БД
        db_token = await token_service.get_refresh_token_from_db(jti, user_id)
        if not db_token:
            logger.warning(f"Refresh token with jti={jti} not found in DB for access-only rotation")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

        if db_token.revoked:
            logger.warning(f"Refresh token with jti={jti} is revoked for access-only rotation")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token revoked")

        if db_token.expires_at < datetime.utcnow(): 
            logger.warning(f"Refresh token with jti={jti} is expired for access-only rotation")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired")


        # 3. Получаем информацию о пользователе для создания access токена
        async with db_manager.get_db_session() as session:
            user_result = await session.execute(select(User).where(User.id == user_id))
            user_obj = user_result.scalar_one_or_none()
            if not user_obj:
                logger.error(f"User with id={user_id} not found during access-only token rotation")
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="User data error")

            await session.refresh(user_obj, ["roles"])
            roles_names = [role.name for role in user_obj.roles]

            # 4. Создаем новый access токен
            new_access_token = await jwt_utils.create_access_token(user_id=user_id)
            
        expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        
        logger.info(f"Access token successfully rotated (access-only) for user_id={user_id}")
        return new_access_token, expires_in

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in access-only token rotation service logic: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")