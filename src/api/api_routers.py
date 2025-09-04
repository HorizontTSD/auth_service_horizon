# src/api/api_routers.py
from fastapi import APIRouter

api_router = APIRouter()


# 1. Авторизация (логин/логаут)
from src.api.v1.authorization import router as auth_user_router
api_router.include_router(auth_user_router, prefix="/auth", tags=["Auth users"])

# 2. Обновление токенов (refresh)
from src.api.v1.auth_refresh import router as auth_refresh_router
api_router.include_router(auth_refresh_router, prefix="/auth", tags=["Refresh Token"])

# 3. Регистрация организации и суперпользователя
from src.api.v1.registration import router as register_organization_and_superuser
api_router.include_router(register_organization_and_superuser, prefix="/register", tags=["Register Organization and Superuser"])

# 4. Регистрация пользователя в конкретной организации + метадата для регистрации роли и доступы
from src.api.v1.register_user import router as register_user_router
api_router.include_router(register_user_router, prefix="/register", tags=["Register Users in Org"])

# 5. Получение метадаты для регистрации пользователя в организации
from src.api.v1.register_metadata import router as register_metadata
api_router.include_router(register_metadata, prefix="/register_metadata", tags=["Register Users in Org"])

# 6. Получение списка пользователей по организации
from src.api.v1.get_users_by_org import router as get_users_by_org_router
api_router.include_router(get_users_by_org_router, prefix="/organizations", tags=["List Users in Org"])

# 7. Изменение статуса пользователя у конкретной организации
from src.api.v1.change_user_status import router as change_user_status_router
api_router.include_router(change_user_status_router, prefix="/change_user_status", tags=["Change User Status in Org"])

# 8. Проверка подключения
from src.api.v1.get_tables_info import router as get_tables_info_router
api_router.include_router(get_tables_info_router, prefix="/tables-info", tags=["Check Test Connection"])
