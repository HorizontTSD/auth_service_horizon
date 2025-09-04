# src/services/create_org_and_superuser.py

from logging import getLogger
from fastapi import HTTPException, status
from sqlalchemy import select, update, insert

from src.utils.jwt_utils import create_access_token, create_refresh_token
from src.models.user_models import RefreshToken
from datetime import datetime, timedelta
from src.session import db_manager
from src.models.user_models import Organization, User, Role, UserRoles
from src.schemas import RegistrationRequest
from src.db_clients.config import RolesConfig
from src.core.security.password import hash_password

logger = getLogger(__name__)
roles = RolesConfig()


async def check_login_exists(session, login: str):
    result = await session.execute(select(User).where(User.login == login))
    if result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Суперюзер с логином {login} уже существует"
        )

async def check_org_exists(session, email: str):
    result = await session.execute(select(Organization).where(Organization.email == email))
    if result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Организация с email {email} уже существует"
        )

async def check_user_email_exists(session, email: str):
    result = await session.execute(select(User).where(User.email == email))
    if result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Суперюзер с email {email} уже существует"
        )

async def create_organization(session, name: str, email: str) -> Organization:
    org = Organization(name=name, email=email, owner_id=None)
    session.add(org)
    await session.flush()
    return org

async def create_superuser(session, org_id: int, payload: RegistrationRequest) -> User:
    hashed_pwd = hash_password(payload.superuser_password)
    user = User(
        organization_id=org_id,
        login=payload.superuser_login,
        first_name=payload.superuser_first_name,
        last_name=payload.superuser_last_name,
        email=payload.superuser_email,
        password=hashed_pwd
    )
    session.add(user)
    await session.flush()
    return user

async def assign_owner(session, org_id: int, superuser_id: int):
    await session.execute(
        update(Organization).where(Organization.id == org_id).values(owner_id=superuser_id)
    )

async def assign_superuser_role(session, superuser_id: int):
    role_result = await session.execute(
        select(Role).where(Role.name == roles.SUPERUSER)
    )
    role_obj = role_result.scalars().first()
    if not role_obj:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Роль SUPERUSER не найдена"
        )

    await session.execute(
        insert(UserRoles).values(user_id=superuser_id, role_id=role_obj.id)
    )

async def create_org_and_superuser(payload: RegistrationRequest) -> dict:
    try:
        async with db_manager.get_db_session() as session:
            await check_login_exists(session, payload.superuser_login)
            if payload.verify_organization_email:
                await check_org_exists(session, payload.organization_email)
            if payload.verify_superuser_email:
                await check_user_email_exists(session, payload.superuser_email)

            org = await create_organization(session, payload.organization_name, payload.organization_email)
            superuser = await create_superuser(session, org.id, payload)
            await assign_owner(session, org.id, superuser.id)
            await assign_superuser_role(session, superuser.id)

            access_token = await create_access_token(user_id=superuser.id)

            refresh_token, refresh_jti = await create_refresh_token(superuser.id)

            db_refresh_token = RefreshToken(
                user_id=superuser.id,
                token=refresh_token,
                jti=refresh_jti,
                expires_at=datetime.utcnow() + timedelta(days=30)
            )
            session.add(db_refresh_token)
            await session.commit()

            return {
                "organization_id": org.id,
                "superuser_id": superuser.id,
                "access_token": access_token,
                "refresh_token": refresh_token,
                "message": "Организация и суперюзер успешно зарегистрированы"
            }

    except HTTPException:
        raise