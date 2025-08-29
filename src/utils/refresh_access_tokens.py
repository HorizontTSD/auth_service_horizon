import uuid
from datetime import datetime, timedelta

import jwt
from sqlalchemy import update

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