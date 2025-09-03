# src/utils/jwt_utils.py
import logging
from datetime import datetime, timedelta
import secrets
import uuid
import jwt
from jwt import ExpiredSignatureError, InvalidTokenError

from src.core.configuration.config import settings
from src.models.user_models import RefreshToken
from sqlalchemy import select, update
from src.session import db_manager
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

# --- Функции для создания токенов ---

async def create_access_token(user_id: int, organization_id: int, roles: list[str] = None) -> str:
    """Создает JWT access токен."""
    expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {
        "sub": str(user_id),
        "organization_id": organization_id,
        "exp": datetime.utcnow() + expires_delta,
        "type": "access"
    }
    if roles:
        to_encode["roles"] = roles
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    logger.debug(f"Created access token for user_id={user_id}")
    return encoded_jwt

async def create_refresh_token(user_id: int) -> tuple[str, str]:
    """Создает JWT refresh токен и возвращает (token, jti)."""
    expires_delta = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    jti = uuid.uuid4().hex 
    to_encode = {
        "sub": str(user_id),
        "jti": jti,
        "exp": datetime.utcnow() + expires_delta,
        "type": "refresh"
    }
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    logger.debug(f"Created refresh token for user_id={user_id}, jti={jti}")
    return encoded_jwt, jti

# --- Функции для декодирования и валидации токенов ---

def decode_jwt_token(token: str, expected_type: str = None) -> dict:
    """
    Декодирует и проверяет базовую валидность JWT токена.
    :param token: Сам JWT токен.
    :param expected_type: Ожидаемый тип токена ('access', 'refresh'). Если None, не проверяется.
    :return: Payload токена.
    :raises HTTPException: Если токен недействителен.
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        
        if expected_type and payload.get("type") != expected_type:
             logger.warning(f"Invalid token type: expected '{expected_type}', got '{payload.get('type')}'")
             raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

        logger.debug(f"Decoded JWT token for sub={payload.get('sub')}, type={payload.get('type')}")
        return payload

    except ExpiredSignatureError:
        logger.warning("JWT token expired")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except InvalidTokenError as e:
        logger.warning(f"Invalid JWT token: {e}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except Exception as e: 
        logger.error(f"Unexpected error during JWT decoding: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal token validation error")


# --- Функции для работы с refresh токенами в БД ---

async def get_refresh_token_from_db(jti: str, user_id: int):
    """Получает refresh токен из БД по jti и user_id."""
    try:
        async with db_manager.get_db_session() as session:
            result = await session.execute(
                select(RefreshToken).where(
                    RefreshToken.jti == jti,
                    RefreshToken.user_id == user_id
                )
            )
            return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Database error fetching refresh token: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error")

async def revoke_refresh_token_in_db(jti: str):
    """Помечает refresh токен как отозванный в БД."""
    try:
        async with db_manager.get_db_session() as session:
            await session.execute(
                update(RefreshToken)
                .where(RefreshToken.jti == jti)
                .values(revoked=True)
            )
            await session.commit()
            logger.debug(f"Revoked refresh token jti={jti}")
    except Exception as e:
        logger.error(f"Database error revoking refresh token: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error")

async def save_refresh_token_to_db(user_id: int, token: str, jti: str):
    """Сохраняет новый refresh токен в БД."""
    try:
        expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        new_db_token = RefreshToken(
            user_id=user_id,
            token=token,
            jti=jti,
            expires_at=expires_at,
            revoked=False
        )
        async with db_manager.get_db_session() as session:
            session.add(new_db_token)
            await session.commit()
            logger.debug(f"Saved new refresh token for user_id={user_id}, jti={jti}")
    except Exception as e:
        logger.error(f"Database error saving refresh token: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error")

# --- Функции высокого уровня для сервисов ---

async def rotate_refresh_token(old_refresh_token: str) -> tuple[str, str]:
    """
    Высокоуровневая функция для ротации refresh токена.
    1. Декодирует старый токен.
    2. Проверяет его в БД (существование, отзыв, срок).
    3. Отзывает старый.
    4. Создает и сохраняет новый.
    5. Создает новый access токен.
    :param old_refresh_token: Старый refresh токен.
    :return: (new_access_token, new_refresh_token)
    """
    # 1. Декодируем и валидируем старый refresh токен
    payload = decode_jwt_token(old_refresh_token, expected_type="refresh")
    jti = payload.get("jti")
    user_id_str = payload.get("sub")

    if not jti or not user_id_str:
        logger.warning("Missing jti or sub in refresh token")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    try:
        user_id = int(user_id_str)
    except (ValueError, TypeError):
        logger.warning(f"Invalid user_id in refresh token: {user_id_str}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    # 2. Проверяем refresh токен в БД
    db_token = await get_refresh_token_from_db(jti, user_id)
    if not db_token:
        logger.warning(f"Refresh token with jti={jti} not found in DB")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    if db_token.revoked:
        logger.warning(f"Refresh token with jti={jti} is revoked")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token revoked")

    if db_token.expires_at < datetime.utcnow():
        logger.warning(f"Refresh token with jti={jti} is expired")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired")

    # 3. Отзываем старый токен
    await revoke_refresh_token_in_db(jti)

    # 4. Генерируем новый refresh токен
    new_refresh_token_str, new_jti = await create_refresh_token(user_id=user_id)

    # 5. Сохраняем новый refresh токен в БД
    await save_refresh_token_to_db(user_id=user_id, token=new_refresh_token_str, jti=new_jti)

    from src.models.user_models import User, Role 
    try:
        async with db_manager.get_db_session() as session:
            user_result = await session.execute(select(User).where(User.id == user_id))
            user_obj = user_result.scalar_one_or_none()
            if not user_obj:
                 logger.error(f"User with id={user_id} not found during token rotation")
                 raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="User data error")

            await session.refresh(user_obj, ["roles"]) 
            roles_names = [role.name for role in user_obj.roles]

            new_access_token_str = await create_access_token(
                user_id=user_id,
                organization_id=user_obj.organization_id,
                roles=roles_names
            )

            return new_access_token_str, new_refresh_token_str

    except HTTPException:
        raise 
    except Exception as e:
        logger.error(f"Error creating new access token during rotation: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error generating new tokens")


