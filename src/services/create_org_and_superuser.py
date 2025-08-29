from logging import getLogger
from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.exc import DatabaseError, SQLAlchemyError
from passlib.context import CryptContext

from src.session import db_manager
from src.models.user_models import Organization, User, Role, UserRoles
from src.schemas import RegistrationRequest
from src.db_clients.config import RolesConfig

logger = getLogger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
roles = RolesConfig()


async def create_org_and_superuser(payload: RegistrationRequest) -> dict:
    try:
        async with db_manager.get_db_session() as session:

            login_exists = await session.execute(
                select(User).where(User.login == payload.superuser_login)
            )
            if login_exists.scalars().first():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Суперюзер с логином {payload.superuser_login} уже существует"
                )

            if payload.verify_organization_email:
                org_exists = await session.execute(
                    select(Organization).where(Organization.email == payload.organization_email)
                )
                if org_exists.scalars().first():
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Организация с email {payload.organization_email} уже существует"
                    )

            if payload.verify_superuser_email:
                user_exists = await session.execute(
                    select(User).where(User.email == payload.superuser_email)
                )
                if user_exists.scalars().first():
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Суперюзер с email {payload.superuser_email} уже существует"
                    )

            org = Organization(
                name=payload.organization_name,
                email=payload.organization_email,
                owner_id=None
            )
            session.add(org)
            await session.flush()

            hashed_pwd = pwd_context.hash(payload.superuser_password)
            superuser = User(
                organization_id=org.id,
                login=payload.superuser_login,
                first_name=payload.superuser_first_name,
                last_name=payload.superuser_last_name,
                email=payload.superuser_email,
                password=hashed_pwd
            )
            session.add(superuser)
            await session.flush()

            await session.execute(
                update(Organization).where(Organization.id == org.id).values(owner_id=superuser.id)
            )

            role_result = await session.execute(
                select(Role).where(Role.name == roles.SUPERUSER)
            )
            role_obj = role_result.scalars().first()
            if not role_obj:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Роль SUPERUSER не найдена"
                )

            user_role = UserRoles(user_id=superuser.id, role_id=role_obj.id)
            session.add(user_role)

            await session.commit()

            return {
                "status": "success",
                "organization_id": org.id,
                "superuser_id": superuser.id,
                "message": "Организация и суперюзер успешно зарегистрированы"
            }

    except HTTPException:
        raise
    except DatabaseError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ошибка подключения к базе данных"
        )
    except SQLAlchemyError as e:
        logger.error(f"Ошибка выполнения запроса к базе данных: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка выполнения запроса к базе данных"
        )
    except Exception as e:
        logger.error(f"Внутренняя ошибка сервера: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Внутренняя ошибка сервера"
        )