# src/api/v1/get_users_by_org.py
from fastapi import APIRouter, HTTPException, Depends
from src.core.token import jwt_token_validator
from src.session import db_manager
from sqlalchemy import select
from src.schemas import UserResponse, GetUsersByOrgResponse
from src.models.user_models import User, Role, Permission
from src.core.logger import logger

router = APIRouter()

@router.get("/{organization_id}/users", response_model=GetUsersByOrgResponse)
async def get_users_by_organization(
    organization_id: int,
    user: dict = Depends(jwt_token_validator)
):
    """
    Получение списка пользователей организации.
    Доступно только авторизованным пользователям.
    Пользователь должен принадлежать к этой организации.
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
                    User.is_active == True
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
                        access_level=access_level,
                        permissions=list(set(permissions))  # Убираем дубликаты
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