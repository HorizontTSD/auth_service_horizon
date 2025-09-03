# src/services/auth_service.py
from datetime import datetime, timedelta
from logging import getLogger

from fastapi import HTTPException, status
from src.core.security.password import verify_password
from sqlalchemy import or_, select, update 
from sqlalchemy.exc import DatabaseError, SQLAlchemyError

from src.models.user_models import RefreshToken, User
from src.schemas import AuthResponse
from src.session import db_manager
from src.utils import jwt_utils 

logger = getLogger(__name__)


async def revoke_existing_tokens(session, user_id: int):
    """Отзывает все активные refresh-токены пользователя"""
    stmt = (
        update(RefreshToken)
        .where(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked == False,
            RefreshToken.expires_at > datetime.utcnow()
        )
        .values(revoked=True)
    )
    result = await session.execute(stmt)
    logger.debug(f"Revoked {result.rowcount} existing refresh tokens for user_id={user_id}") 


async def auth(login: str, password: str) -> AuthResponse:
    try:
        async with db_manager.get_db_session() as session:
            query = select(User).where(
                or_(User.email == login, User.nickname == login, User.login == login)
            )

            result = await session.execute(query)
            user = result.scalar_one_or_none()

            if not user or not verify_password(password, user.password):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail='Неверные учётные данные'
                )

            if not user.is_active or user.is_blocked or user.is_deleted:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail='Пользователь заблокирован, удалён или неактивен'
                )

            await revoke_existing_tokens(session, user.id)
            await session.commit() 

            access_token = await jwt_utils.create_access_token(
                user_id=user.id,
                organization_id=user.organization_id,
                roles=[role.name for role in user.roles]
            )

            refresh_token, refresh_jti = await jwt_utils.create_refresh_token(user_id=user.id)

            db_refresh_token = RefreshToken(
                user_id=user.id,
                token=refresh_token,
                jti=refresh_jti,
                expires_at=datetime.utcnow() + timedelta(days=30) 
            )

            session.add(db_refresh_token)
            await session.commit() 

            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "Bearer",
                "expires_in": 15 * 60, # 15 минут
                "refresh_expires_in": 30 * 24 * 60 * 60, # 30 дней
                "user": {
                    "id": user.id,
                    "organization_id": user.organization_id,
                    "roles": [role.name for role in user.roles],
                    "permissions": [permission.code for role in user.roles for permission in role.permissions]
                }
            }

    except HTTPException as e:
        raise 

    except DatabaseError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail='Ошибка подключения к базе данных'
        )

    except SQLAlchemyError as e:
        logger.error(f"Ошибка выполнения запроса к базе данных: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Ошибка выполнения запроса к базе данных'
        )

    except Exception as e:
        logger.error(f"Внутренняя ошибка сервера: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Внутренняя ошибка сервера'
        )