# src/schemas.py
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Literal


# ========================
# Общие модели
# ========================

class PermissionsResponse(BaseModel):
    permissions: List[str]


# ========================
# Регистрация организации и суперпользователя
# ========================

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


# ========================
# Обновление токенов (refresh)
# ========================

class RefreshRequest(BaseModel):
    refresh_token: str


class RefreshResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["Bearer"]
    expires_in: int
    refresh_expires_in: int


# ========================
# Регистрация пользователя в организации
# ========================

class RegisterUserRequest(BaseModel):
    login: str
    password: str
    email: EmailStr
    first_name: str
    last_name: str
    role: str
    permissions: Optional[List[str]] = None


class RegisterUserResponse(BaseModel):
    success: bool
    user_id: int
    message: str


# ========================
# Получение пользователей по организации
# ========================

class UserResponse(BaseModel):
    login: str
    first_name: str
    last_name: str
    email: str
    access_level: str
    permissions: List[str]


class GetUsersByOrgResponse(BaseModel):
    users: List[UserResponse]