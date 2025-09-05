# src/api/v1/get_users_by_org.py
from fastapi import APIRouter, HTTPException, Depends
from src.core.token import jwt_token_validator
from src.schemas import UserResponse, GetUsersByOrgResponse
from src.core.logger import logger
from src.services.user_service import fetch_users_with_roles_and_permissions

router = APIRouter()


@router.get(
    "/{organization_id}/users",
    response_model=GetUsersByOrgResponse,
    summary="Get organization's users",
    description="Возвращает список активных пользователей указанной организации с их ролями и разрешениями."
)
async def get_users_by_organization(
        organization_id: int,
        user: dict = Depends(jwt_token_validator)
):
    """
    Эндпоинт для получения списка пользователей организации.

    Description:
    - Возвращает список активных пользователей указанной организации
    - Для каждого пользователя показывает его роли и разрешения
    - Поддерживает иерархию ролей через таблицу user_roles
    - Фильтрует удаленных и неактивных пользователей

    Parameters:
    - **organization_id** (integer, path): ID организации для получения списка пользователей

    Raises:
    - **HTTPException 401**: Если пользователь не авторизован (нет валидного токена)
    - **HTTPException 403**: Если пользователь не имеет доступа к организации
    - **HTTPException 404**: Если организация с указанным ID не найдена
    - **HTTPException 500**: Если произошла ошибка при работе с базой данных
    """
    current_user_org_id = user["organization_id"]

    if current_user_org_id != organization_id:
        raise HTTPException(status_code=403, detail="Доступ к этой организации запрещён")
    try:
        return await fetch_users_with_roles_and_permissions(organization_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при получении пользователей организации {organization_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Не удалось получить список пользователей")
