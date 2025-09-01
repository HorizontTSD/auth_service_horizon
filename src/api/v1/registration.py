# src/api/v1/registration.py
from fastapi import APIRouter, HTTPException, Depends, Body
from src.core.token import jwt_token_validator
from src.schemas import RegistrationRequest, RegistrationResponse
from src.services.create_org_and_superuser import create_org_and_superuser

router = APIRouter()

@router.post("/", status_code=201, response_model=RegistrationResponse)
async def register_organization_and_superuser(
    payload: RegistrationRequest = Body(...),
    user: dict = Depends(jwt_token_validator)
):
    """
    Регистрация новой организации и суперпользователя.
    Доступно только пользователям с ролью 'superuser'.
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