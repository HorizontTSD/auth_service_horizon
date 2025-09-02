import uuid
from datetime import datetime, timedelta

import jwt
from fastapi import HTTPException, status
from sqlalchemy import select, update

from src.core.configuration.config import settings
from src.models.user_models import RefreshToken


async def create_access_token(user_id: int):
    expires = datetime.now() + timedelta(minutes=15)
    to_encode = {"sub": str(user_id), "exp": expires, "type": "access"}
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

async def create_refresh_token(user_id: int) -> tuple[str, str]:
    """Создает refresh JWT и возвращает кортеж (token, jti)."""
    expires = datetime.utcnow() + timedelta(days=30)
    jti = uuid.uuid4().hex
    to_encode = {"sub": str(user_id), "exp": expires, "type": "refresh", "jti": jti}
    token = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, jti

async def revoke_existing_tokens(session, user_id: int):
    """Отзывает все активные refresh-токены пользователя"""
    stmt = (
        update(RefreshToken)
        .where(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked == False,  # Только неотозванные
            RefreshToken.expires_at > datetime.utcnow()  # Только не истекшие
        )
        .values(revoked=True)
    )
    await session.execute(stmt)

async def revoke_one_token(session, refresh_token):
    """Отзывает один валидный токен"""
    try:
        await validate_token(session, refresh_token)
    except HTTPException:
        raise


    stmt = (
        update(RefreshToken)
        .where(
            RefreshToken.token == refresh_token
        )
        .values(revoked=True)
    )
    await session.execute(stmt)

async def validate_token(session, refresh_token):
    """Проверяет токен на валидность"""
    stmt = (
                select(RefreshToken)
                .where(RefreshToken.token==refresh_token)
            )
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