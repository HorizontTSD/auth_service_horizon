# src/services/auth_service.py
from datetime import datetime, timedelta
from logging import getLogger

from fastapi import HTTPException, status
from src.core.security.password import verify_password
from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload 

from src.models.user_models import RefreshToken, User, Role, Permission 
from src.schemas import AuthResponse, UserAuthResponse, LogoutResponse
from src.session import db_manager
from src.utils import jwt_utils 
from src.utils.jwt_utils import revoke_existing_tokens
from src.core.configuration.config import settings

logger = getLogger(__name__)

async def auth(login: str, password: str) -> AuthResponse:
    async with db_manager.get_db_session() as session:
        query = (
            select(User)
            .options(
                selectinload(User.roles).selectinload(Role.permissions) 
            )
            .where(
                or_(User.email == login, User.nickname == login, User.login == login)
            )
        )

        result = await session.execute(query)
        user = result.scalar_one_or_none()

        if not user or not verify_password(password, user.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверные учётные данные"
            )

        if not user.is_active or user.is_blocked or user.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Пользователь заблокирован, удалён или неактивен"
            )

        # Отзываем старые refresh-токены
        await revoke_existing_tokens(session, user.id)
        await session.commit()

        # --- Генерируем новые токены ---
        access_token = await jwt_utils.create_access_token(user_id=user.id)
        refresh_token, refresh_jti = await jwt_utils.create_refresh_token(user_id=user.id)

        db_refresh_token = RefreshToken(
            user_id=user.id,
            token=refresh_token,
            jti=refresh_jti,
            expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS), # Используем настройку
        )

        session.add(db_refresh_token)
        await session.commit()

        # --- Подготовка данных пользователя ---
        roles = [role.name for role in user.roles]
        permissions = [permission.code for role in user.roles for permission in role.permissions]

        return AuthResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="Bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60, 
            refresh_expires_in=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
            user=UserAuthResponse(
                id=user.id,
                organization_id=user.organization_id,
                roles=roles,
                permissions=permissions,
            ),
        )


async def logout(refresh_token: str) -> LogoutResponse:
    async with db_manager.get_db_session() as session:
        await jwt_utils.revoke_one_token(session, refresh_token) 
        await session.commit()
        return LogoutResponse( 
            detail='Выход выполнен успешно'
        )