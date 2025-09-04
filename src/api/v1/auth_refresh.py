# src/api/v1/auth_refresh.py
from fastapi import APIRouter, HTTPException, Depends, Body

from src.schemas import RefreshRequest, RefreshResponse
from src.core.logger import logger
from src.services import token_refresh_service
from src.core.configuration.config import settings

router = APIRouter()

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
async def refresh_tokens(
    request: RefreshRequest = Body(
        ...,
        example={
            "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        }
    )
):
    """
    Эндпоинт для обновления JWT токенов по refresh-токену.

    Description:
    - Реализует безопасную ротацию токенов с защитой от повторного использования
    - Проверяет валидность и срок действия refresh-токена
    - Отзывает использованный токен и выдает новую пару токенов
    - Возвращает обновленные access и refresh токены

    Raises:
    - **HTTPException 401**: Если refresh-токен недействителен, истек или отозван
    - **HTTPException 500**: Если произошла ошибка при работе с базой данных или в сервисе
    """
    refresh_token_str = request.refresh_token

    new_access_token, new_refresh_token, expires_in, refresh_expires_in = \
        await token_refresh_service.refresh_tokens_logic(refresh_token_str)

    logger.info("Successfully refreshed tokens via service")

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "Bearer",
        "expires_in": expires_in,
        "refresh_expires_in": refresh_expires_in,
    }