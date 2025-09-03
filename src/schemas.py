# src/schemas.py
from typing import List, Optional

from pydantic import BaseModel, EmailStr

from typing import Optional, List, Dict
from typing import Literal

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
    access_token: str
    refresh_token: str
    message: str = "Организация и суперюзер успешно зарегистрированы"


class UserResponse(BaseModel):
    login: str
    first_name: str
    last_name: str
    email: str
    access_level: str  # например, 'admin'
    permissions: List[str]


class GetUsersByOrgResponse(BaseModel):
    users: List[UserResponse]


class RefreshRequest(BaseModel):
    refresh_token: str


class RefreshResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["Bearer"]
    expires_in: int
    refresh_expires_in: int

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


class RegisterUserRequest(BaseModel):
    """
    Схема для запроса на регистрацию нового пользователя в организации.
    """
    login: str
    password: str
    email: EmailStr
    first_name: str
    last_name: str
    role: str 

class RegisterUserResponse(BaseModel):
    """
    Схема для ответа на запрос регистрации нового пользователя.
    """
    success: bool
    user_id: int
    message: str