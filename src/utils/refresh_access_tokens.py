from datetime import datetime, timedelta

import jwt
from sqlalchemy import update

from src.core.configuration.config import settings
from src.models.user_models import RefreshToken


async def create_access_token(user_id: int):
    expires = datetime.now() + timedelta(minutes=15)
    to_encode = {"sub": str(user_id), "exp": expires, "type": "access"}
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

async def create_refresh_token(user_id: int):
    expires = datetime.utcnow() + timedelta(days=30)
    to_encode = {"sub": str(user_id), "exp": expires, "type": "refresh"}
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

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