# src/api/v1/get_users_by_org.py
from fastapi import APIRouter, HTTPException, Depends
from src.core.token import jwt_token_validator
from src.session import db_manager
from sqlalchemy import select
from src.schemas import UserResponse, GetUsersByOrgResponse
from src.models.user_models import User, Role, Permission
from src.core.logger import logger

router = APIRouter(tags=["Users"])


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

    try:
        # 1. Проверка: пользователь имеет доступ к этой организации?
        if current_user_org_id != organization_id:
            raise HTTPException(
                status_code=403,
                detail="Доступ к этой организации запрещён"
            )

        async with db_manager.get_db_session() as session:
            # 2. Проверка существования организации
            result = await session.execute(
                select(User.id).where(User.organization_id == organization_id).limit(1)
            )
            if not result.scalar():
                raise HTTPException(
                    status_code=404,
                    detail=f"Организация с id={organization_id} не найдена"
                )

            # 3. Получаем пользователей с ролями и разрешениями
            result = await session.execute(
                select(User)
                .where(
                    User.organization_id == organization_id,
                    User.is_deleted == False,
                    User.is_active == True,
                    User.is_blocked == False
                )
                .order_by(User.created_at)
            )
            users = result.scalars().all()

            users_response = []
            for u in users:
                # Загружаем роли и разрешения через relationship
                await session.refresh(u, ["roles"])
                for role in u.roles:
                    await session.refresh(role, ["permissions"])

                roles_names = [role.name for role in u.roles]
                access_level = roles_names[0] if roles_names else "user"

                permissions = [
                    perm.code
                    for role in u.roles
                    for perm in role.permissions
                ]

                users_response.append(
                    UserResponse(
                        login=u.login,
                        first_name=u.first_name,
                        last_name=u.last_name,
                        email=u.email,
                        access_level=[role.name for role in u.roles][0] if u.roles else "user",
                        permissions=list({perm.code for role in u.roles for perm in role.permissions})
                    )
                )

            return GetUsersByOrgResponse(users=users_response)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при получении пользователей организации {organization_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Не удалось получить список пользователей"
        )