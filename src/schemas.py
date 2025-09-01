# src/schemas.py
from typing import List, Optional

from pydantic import BaseModel, EmailStr


class PermissionsResponse(BaseModel):
    permissions: List[str]


class RegistrationRequest(BaseModel):
    organization_name: str
    organization_email: EmailStr
    superuser_login: str
    superuser_first_name: str
    superuser_last_name: str
    superuser_email: EmailStr
    superuser_password: str
    verify_superuser_email: Optional[bool] = False
    verify_organization_email: Optional[bool] = False


class RegistrationResponse(BaseModel):
    organization_id: int
    superuser_id: int
    message: str = "Организация и суперюзер успешно зарегистрированы"


class AuthRequest(BaseModel):
    login: str | EmailStr
    password: str


class UserAuthResponse(BaseModel):
    id: int
    organization_id: int
    roles: list[str]
    permissions: list[str]


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    refresh_expires_in: int
    user: UserAuthResponse


class RolesResponse(BaseModel):
    roles: list[str]

