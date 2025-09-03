# src/api/v1/register_user.py
from fastapi import APIRouter, HTTPException, Depends, Body, status
from src.core.token import jwt_token_validator
from src.schemas import RegisterUserRequest, RegisterUserResponse 
from src.session import db_manager
from src.models.user_models import User, Role, UserRoles 
from src.core.security.password import hash_password
from sqlalchemy import select
from src.core.logger import logger

router = APIRouter(tags=["Register Users"])


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
    - **HTTPException 500**: Если произошла ошибка при работе с базой данных.
    """
    current_user_org_id = user_data.get("organization_id")
    current_user_roles = user_data.get("roles", [])
    
    # 1. Проверка прав
    if "superuser" not in current_user_roles:
        raise HTTPException(status_code=403, detail="Недостаточно прав для создания пользователя")

    try:
        async with db_manager.get_db_session() as session:
            # 2. Проверка уникальности логина/email в пределах организации (или глобально)
            result_login = await session.execute(select(User).where(User.login == payload.login))
            if result_login.scalars().first():
                raise HTTPException(status_code=409, detail=f"Пользователь с логином '{payload.login}' уже существует")

            result_email = await session.execute(select(User).where(User.email == payload.email))
            if result_email.scalars().first():
                raise HTTPException(status_code=409, detail=f"Пользователь с email '{payload.email}' уже существует")

            # 3. Найти роль по имени
            result_role = await session.execute(select(Role).where(Role.name == payload.role))
            role_obj = result_role.scalars().first()
            if not role_obj:
                 raise HTTPException(status_code=400, detail=f"Роль '{payload.role}' не найдена")

            # 4. Создать пользователя
            hashed_password = hash_password(payload.password)
            new_user = User(
                organization_id=current_user_org_id,
                login=payload.login,
                first_name=payload.first_name,
                last_name=payload.last_name,
                email=payload.email,
                password=hashed_password,
                # nickname? другие поля по умолчанию (is_active=True и т.д. должны быть в модели)
            )
            session.add(new_user)
            await session.flush() # Получаем new_user.id

            # 5. Назначить роль через UserRoles
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
        # Пробрасываем HTTPException без изменений
        raise
    except Exception as e:
        logger.error(f"Ошибка при создании пользователя: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")
