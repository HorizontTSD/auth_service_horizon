from fastapi import APIRouter, HTTPException, status, Body
from src.schemas import RegistrationRequest, RegistrationResponse
from src.core.logger import logger
from src.services.create_org_and_superuser import create_org_and_superuser


router = APIRouter()

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=RegistrationResponse)
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
        ),
):
    """
    Эндпоинт для регистрации организации и суперюзера.

    Description:
    - Создает запись в таблице organizations.
    - Создает запись в таблице users, связанного с организацией.
    - Возвращает успешный ответ о регистрации.
    """
    try:
        response = await create_org_and_superuser(payload)
        return response

    except HTTPException as http_exc:
        raise http_exc

    except Exception as e:
        logger.error(f"Ошибка при регистрации: {e}")
        raise HTTPException(
            status_code=500,
            detail="Не удалось зарегистрировать организацию и суперюзера"
        )