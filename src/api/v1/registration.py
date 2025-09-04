# src/api/v1/registration.py
from fastapi import APIRouter, HTTPException, Body, status
from src.schemas import RegistrationRequest, RegistrationResponse
from src.services.create_org_and_superuser import create_org_and_superuser
from src.core.logger import logger


router = APIRouter()


@router.post(
    "/org_and_superuser",
    status_code=status.HTTP_201_CREATED, 
    response_model=RegistrationResponse,
    summary="Register organization and superuser",
    description="Создает новую организацию и первого суперпользователя для неё. Не требует аутентификации."
)
async def register_organization_and_superuser(
    payload: RegistrationRequest = Body(
        ...,
        example={
            "organization_name": "Название организации",
            "organization_email": "org@example.com",
            "superuser_login": "super_login",
            "superuser_first_name": "Иван",
            "superuser_last_name": "Иванов",
            "superuser_email": "ivanov@example.com",
            "superuser_password": "plain_password",
            "verify_superuser_email": True,
            "verify_organization_email": True
        },
    )
):
    """
    Эндпоинт для регистрации новой организации и её первого суперюзера.

    Description:
    - Создает запись в таблице organizations с указанной информацией.
    - Создает суперпользователя в таблице users, связанного с новой организацией.
    - Назначает новому пользователю роль superuser.
    - Возвращает информацию о созданной организации, пользователе и токены доступа.

    Raises:
    - **HTTPException 409**: Если организация или суперпользователь с такими данными уже существуют.
    - **HTTPException 422**: Если входные данные невалидны.
    - **HTTPException 500**: Если произошла ошибка при работе с базой данных.
    """

    try:
        result = await create_org_and_superuser(payload)
        return result
    except HTTPException:
        raise

