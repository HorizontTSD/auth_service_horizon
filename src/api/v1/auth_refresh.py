# src/api/v1/auth_refresh.py
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, Body
import jwt
import secrets
from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError

from src.schemas import RefreshRequest, RefreshResponse
from src.core.logger import logger
from src.session import db_manager
from src.core.configuration.config import settings
from src.models.user_models import RefreshToken as DBRefreshToken
from src.utils.refresh_access_tokens import create_access_token, create_refresh_token

router = APIRouter(tags=["Auth"])


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
    """
    Эндпоинт для обновления JWT токенов по refresh-токену.

    Description:
    - Реализует безопасную ротацию токенов с защитой от повторного использования
    - Проверяет валидность и срок действия refresh-токена
    - Отзывает использованный токен и выдает новую пару токенов
    - Возвращает обновленные access и refresh токены

    Parameters:
    - **refresh_token** (string): Валидный refresh-токен пользователя

    Returns:
    - **JSON**:
      - `access_token`: Новый JWT access-токен
      - `refresh_token`: Новый JWT refresh-токен  
      - `token_type`: Тип токена (Bearer)
      - `expires_in`: Время жизни access-токена в секундах (15 минут)
      - `refresh_expires_in`: Время жизни refresh-токена в секундах (30 дней)

    Example Request:
    ```json
    {
      "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    }
    ```

    Example Response:
    ```json
    {
      "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "token_type": "Bearer",
      "expires_in": 900,
      "refresh_expires_in": 2592000
    }
    ```

    Raises:
    - **HTTPException 401**: Если refresh-токен недействителен, истек или отозван
    - **HTTPException 500**: Если произошла ошибка при работе с базой данных
    """
    refresh_token = request.refresh_token

    try:
        # 1. Декодируем refresh-токен
        try:
            payload = jwt.decode(
                refresh_token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )
        except jwt.ExpiredSignatureError:
            logger.warning("Refresh token expired")
            raise HTTPException(status_code=401, detail="Refresh token expired")
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid refresh token: {e}")
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        jti = payload.get("jti")
        user_id = payload.get("sub")
        token_type = payload.get("type")

        if not jti or not user_id:
            logger.warning("Missing jti or sub in refresh token")
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        if token_type != "refresh":
            logger.warning("Token type is not refresh")
            raise HTTPException(status_code=401, detail="Invalid token type")

        async with db_manager.get_db_session() as session:
            # 2. Проверяем существование refresh-токена в БД
            result = await session.execute(
                select(DBRefreshToken).where(
                    DBRefreshToken.jti == jti,
                    DBRefreshToken.user_id == int(user_id)
                )
            )
            db_token = result.scalar_one_or_none()

            if not db_token:
                logger.warning(f"Refresh token with jti={jti} not found in DB")
                raise HTTPException(status_code=401, detail="Invalid refresh token")

            if db_token.revoked:
                logger.warning(f"Refresh token with jti={jti} is revoked")
                raise HTTPException(status_code=401, detail="Refresh token revoked")

            if db_token.expires_at < datetime.utcnow():
                logger.warning(f"Refresh token with jti={jti} is expired")
                raise HTTPException(status_code=401, detail="Refresh token expired")

            # 3. Отзываем старый токен
            await session.execute(
                update(DBRefreshToken)
                .where(DBRefreshToken.jti == jti)
                .values(revoked=True)
            )
            await session.commit()

            # 4. Генерируем новый refresh и access
            new_refresh_token, new_jti = await create_refresh_token(user_id=int(user_id))
            new_access_token = await create_access_token(user_id=int(user_id))

            # 5. Сохраняем новый refresh в БД
            new_db_token = DBRefreshToken(
                user_id=int(user_id),
                token=new_refresh_token,
                jti=new_jti,
                expires_at=datetime.utcnow() + timedelta(days=30),
                revoked=False
            )
            session.add(new_db_token)
            await session.commit()

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
    except SQLAlchemyError as e:
        logger.error(f"Database error during token refresh: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
    except Exception as e:
        logger.error(f"Unexpected error during token refresh: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")