# src/api/v1/registration.py
from fastapi import APIRouter, HTTPException, Depends, Body
from src.core.token import jwt_token_validator
from src.schemas import RegistrationRequest, RegistrationResponse
from src.services.create_org_and_superuser import create_org_and_superuser
from src.core.logger import logger

router = APIRouter()


@router.post(
    "/",
    status_code=201,
    response_model=RegistrationResponse,
    summary="Register organization and superuser",
    description="Создает новую организацию и суперпользователя для неё. Доступно только суперпользователям.",
    tags=["Register Organization and Superuser"]
)
async def register_organization_and_superuser(
    payload: RegistrationRequest = Body(...),
    user: dict = Depends(jwt_token_validator)
):
    """
    Эндпоинт для регистрации организации и суперюзера.

    Description:
    - Создает запись в таблице organizations с указанной информацией
    - Создает суперпользователя в таблице users, связанного с организацией
    - Назначает суперпользователю роль superuser
    - Возвращает информацию о созданной организации и пользователе с токенами доступа

    Parameters:
    - **organization_name** (string): Название организации
    - **organization_email** (string): Email организации (уникальный)
    - **superuser_login** (string): Логин суперпользователя (уникальный)
    - **superuser_first_name** (string): Имя суперпользователя
    - **superuser_last_name** (string): Фамилия суперпользователя
    - **superuser_email** (string): Email суперпользователя (уникальный)
    - **superuser_password** (string): Пароль суперпользователя (будет хэширован)
    - **verify_superuser_email** (boolean, optional): Проверять уникальность email суперпользователя (по умолчанию false)
    - **verify_organization_email** (boolean, optional): Проверять уникальность email организации (по умолчанию false)

    Returns:
    - **JSON**:
      - `organization_id`: ID созданной организации
      - `superuser_id`: ID созданного суперпользователя
      - `access_token`: JWT access-токен для аутентификации
      - `refresh_token`: JWT refresh-токен для обновления токенов
      - `message`: Сообщение об успешной регистрации

    Example Request:
    ```json
    {
      "organization_name": "Название организации",
      "organization_email": "org@example.com",
      "superuser_login": "super_login",
      "superuser_first_name": "Иван",
      "superuser_last_name": "Иванов",
      "superuser_email": "ivanov@example.com",
      "superuser_password": "plain_password",
      "verify_superuser_email": true,
      "verify_organization_email": true
    }
    ```

    Example Response:
    ```json
    {
      "organization_id": 1,
      "superuser_id": 1,
      "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "message": "Организация и суперюзер успешно зарегистрированы"
    }
    ```

    Raises:
    - **HTTPException 401**: Если пользователь не авторизован (нет валидного токена)
    - **HTTPException 403**: Если у пользователя нет роли 'superuser'
    - **HTTPException 409**: Если организация или суперпользователь с такими данными уже существуют
    - **HTTPException 500**: Если произошла ошибка при работе с базой данных
    """
    # Проверка роли
    if "roles" not in user or "superuser" not in user["roles"]:
        raise HTTPException(
            status_code=403,
            detail="Доступ запрещён: требуется роль 'superuser'"
        )

    try:
        # Вызываем сервис
        result = await create_org_and_superuser(payload)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при регистрации: {e}")
        raise HTTPException(
            status_code=500,
            detail="Не удалось зарегистрировать организацию"
        )