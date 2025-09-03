# src/services/user_service.py
import logging
from fastapi import HTTPException, status
from sqlalchemy import select

from src.core.security.password import hash_password
from src.models.user_models import User, Role, UserRoles
from src.schemas import RegisterUserRequest, RegisterUserResponse
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

            user_role = UserRoles(user_id=new_user.id, role_id=role_obj.id)
            session.add(user_role)

            await session.commit()

            logger.info(f"Пользователь '{new_user.login}' (ID: {new_user.id}) создан в организации ID {current_user_org_id}")
            return RegisterUserResponse(
                success=True,
                user_id=new_user.id,
                message=f"Пользователь '{new_user.login}' успешно создан"
            )

    except HTTPException:
        raise
