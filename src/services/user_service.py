# src/services/user_service.py
import logging
from fastapi import HTTPException, status
from sqlalchemy import select, insert

from src.core.security.password import hash_password
from src.models.user_models import User, Role, UserRoles
from src.schemas import (
    RegisterUserRequest, RegisterUserResponse, UserStatusChangeRequest,
    UserStatusChangeResponse, UserResponse, GetUsersByOrgResponse
)
from src.session import db_manager

logger = logging.getLogger(__name__)

async def create_user_in_organization(
    current_user_org_id: int, 
    payload: RegisterUserRequest
) -> RegisterUserResponse:
    """
    Сервисная функция для создания нового пользователя в указанной организации.

    Args:
        current_user_org_id: ID организации, в которой создается пользователь.
        payload: Данные нового пользователя.

    Returns:
        RegisterUserResponse: Информация о созданном пользователе.

    Raises:
        HTTPException: При ошибках валидации данных, конфликтах или проблемах с БД.
    """
    try:
        async with db_manager.get_db_session() as session:
            result_login = await session.execute(select(User).where(User.login == payload.login))
            if result_login.scalars().first():
                raise HTTPException(status_code=409, detail=f"Пользователь с логином '{payload.login}' уже существует")

            result_email = await session.execute(select(User).where(User.email == payload.email))
            if result_email.scalars().first():
                raise HTTPException(status_code=409, detail=f"Пользователь с email '{payload.email}' уже существует")

            result_role = await session.execute(select(Role).where(Role.name == payload.role))
            role_obj = result_role.scalars().first()
            if not role_obj:
                 raise HTTPException(status_code=400, detail=f"Роль '{payload.role}' не найдена")

            hashed_password = hash_password(payload.password)
            new_user = User(
                organization_id=current_user_org_id,
                login=payload.login,
                first_name=payload.first_name,
                last_name=payload.last_name,
                email=payload.email,
                password=hashed_password,
            )
            session.add(new_user)
            await session.flush()

            await session.execute(
                insert(UserRoles).values(user_id=new_user.id, role_id=role_obj.id)
            )

            await session.commit()

            logger.info(f"Пользователь '{new_user.login}' (ID: {new_user.id}) создан в организации ID {current_user_org_id}")
            return RegisterUserResponse(
                success=True,
                user_id=new_user.id,
                message=f"Пользователь '{new_user.login}' успешно создан"
            )

    except HTTPException:
        raise


async def change_user_status(
        current_user_org_id: int,
        payload: UserStatusChangeRequest,
        action: str,  # 'delete', 'block', 'unblock'
) -> UserStatusChangeResponse:
    """
    Универсальная функция для изменения статуса пользователя в организации.

    Args:
        current_user_org_id: ID организации.
        payload: Данные пользователя (логин).
        action: Действие: 'delete', 'block' или 'unblock'.

    Returns:
        UserStatusChangeResponse: Результат операции.

    Raises:
        HTTPException: Если пользователь не найден или действие недопустимо.
    """
    async with db_manager.get_db_session() as session:
        user = await session.execute(
            select(User).where(
                User.login == payload.login_to_change,
                User.organization_id == current_user_org_id
            )
        )
        user_obj = user.scalars().first()

        if not user_obj:
            raise HTTPException(
                status_code=404,
                detail=f"Пользователь '{payload.login_to_change}' не найден в организации ID {current_user_org_id}"
            )

        if action == "delete":
            user_obj.is_deleted = True
            user_obj.is_block = True
            user_obj.is_active = False
            message = f"Пользователь '{payload.login_to_change}' успешно помечен как удалённый"
        elif action == "block":
            if user_obj.is_deleted:
                raise HTTPException(
                    status_code=400,
                    detail=f"Невозможно заблокировать удалённого пользователя '{payload.login_to_change}'"
                )
            user_obj.is_block = True
            user_obj.is_active = False
            message = f"Пользователь '{payload.login_to_change}' успешно заблокирован"
        elif action == "unblock":
            if user_obj.is_deleted:
                raise HTTPException(
                    status_code=400,
                    detail=f"Невозможно разблокировать удалённого пользователя '{payload.login_to_change}'"
                )
            user_obj.is_block = False
            user_obj.is_active = True
            message = f"Пользователь '{payload.login_to_change}' успешно разблокирован"
        else:
            raise HTTPException(status_code=400, detail=f"Неизвестное действие '{action}'")

        session.add(user_obj)
        await session.commit()

        return UserStatusChangeResponse(
            success=True,
            user_id=user_obj.id,
            message=message
        )


async def fetch_users_with_roles_and_permissions(organization_id: int) -> GetUsersByOrgResponse:
    async with db_manager.get_db_session() as session:
        result = await session.execute(
            select(User.id).where(User.organization_id == organization_id).limit(1)
        )
        if not result.scalar():
            raise HTTPException(
                status_code=404,
                detail=f"Организация с id={organization_id} не найдена"
            )

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
            await session.refresh(u, ["roles"])
            for role in u.roles:
                await session.refresh(role, ["permissions"])

            users_response.append(
                UserResponse(
                    login=u.login,
                    first_name=u.first_name,
                    last_name=u.last_name,
                    email=u.email,
                    access_level=u.roles[0].name if u.roles else "user",
                    permissions=list({perm.code for role in u.roles for perm in role.permissions})
                )
            )

        return GetUsersByOrgResponse(users=users_response)