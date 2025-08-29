from datetime import datetime, timedelta
from logging import getLogger

import jwt
from fastapi import HTTPException, status
from passlib.context import CryptContext
from sqlalchemy import or_, select
from sqlalchemy.exc import DatabaseError, SQLAlchemyError

from src.models.user_models import RefreshToken, User
from src.schemas import AuthResponse
from src.session import db_manager
from src.utils.refresh_access_tokens import create_access_token, create_refresh_token, revoke_existing_tokens

logger = getLogger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def auth(login: str, password: str) -> AuthResponse:
    try:
        async with db_manager.get_db_session() as session:
            query = select(User).where(
                or_(User.email == login, User.nickname == login, User.login == login)
            )

            result = await session.execute(query)
            user = result.scalar_one_or_none()

            if not user or not pwd_context.verify(password, user.password):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail='Неверные учётные данные'
                )
            
            if not user.is_active or user.is_blocked or user.is_deleted:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail='Пользователь заблокирован, удалён или неактивен'
                )
            
            await revoke_existing_tokens(session, user.id) # отзываем существующие refresh_token для этого пользователя
            
            access_token = await create_access_token(user.id)
            refresh_token = await create_refresh_token(user.id)

            db_refresh_token = RefreshToken(
                user_id=user.id,
                token=refresh_token,
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
                    "role": user.role,
                    "permissions": user.permissions
                }
            }
    
    except HTTPException:
        raise
    
    except DatabaseError:
        # логируется в src/session.py
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
    
    except jwt.PyJWTError as e:
        logger.error(f"Ошибка создания токенов: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Ошибка создания токенов'
        )
    
    except Exception as e:
        logger.error(f"Внутренняя ошибка сервера: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Внутренняя ошибка сервера'
        )