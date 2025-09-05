# src/api/v1/register_user.py
from fastapi import APIRouter, HTTPException, Depends, Body, status
from src.core.token import jwt_token_validator
from src.schemas import RegisterUserRequest, RegisterUserResponse
from src.services.user_service import create_user_in_organization

router = APIRouter()

@router.post("/user", response_model=RegisterUserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    payload: RegisterUserRequest = Body(
        ...,
        example={
            "login": "new_user",
            "password": "secure_password123",
            "email": "newuser@example.com",
            "first_name": "Иван",
            "last_name": "Петров",
            "role": "user"
        }
    ),
    user_data: dict = Depends(jwt_token_validator)
):
    """
    Эндпоинт для регистрации нового пользователя в организации.

    Description:
    - Создаёт нового пользователя, связанного с организацией из токена авторизации.
    - Назначает пользователю указанную роль.
    - Требует действующий JWT access_token с ролью 'superuser'.

    Raises:
    - **HTTPException 400**: Если указанная роль не существует.
    - **HTTPException 401**: Если access_token отсутствует, истёк или недействителен.
    - **HTTPException 403**: Если у пользователя нет роли 'superuser'.
    - **HTTPException 409**: Если логин или email нового пользователя уже существуют.
    - **HTTPException 500**: Если произошла ошибка при работе с базой данных (обрабатывается глобально).
    """
    current_user_org_id = user_data.get("organization_id")
    current_user_roles = user_data.get("roles", [])

    # 1. Проверка прав
    if "superuser" not in current_user_roles:
        raise HTTPException(status_code=403, detail="Недостаточно прав для создания пользователя")

    # 2. Вызов сервисной функции для создания пользователя
    return await create_user_in_organization(current_user_org_id, payload)
