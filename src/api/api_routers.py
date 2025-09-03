# src/api/api_routers.py
from fastapi import APIRouter

api_router = APIRouter()

# 1. Проверка подключения
from src.api.v1.get_tables_info import router as get_tables_info_router
api_router.include_router(get_tables_info_router, prefix="/tables-info", tags=["Check Test Connection"])

# 2. Получение маппинга прав
from src.api.v1.get_permissions_mapping import router as func_get_permissions_mapping
api_router.include_router(func_get_permissions_mapping, prefix="/permissions_mapping", tags=["Permissions Mapping"])

# 3. Роли пользователей
from src.api.v1.roles import router as roles_router
api_router.include_router(roles_router, prefix="/roles", tags=["Users roles"])

# 4. Регистрация организации и суперпользователя
from src.api.v1.registration import router as register_organization_and_superuser
api_router.include_router(register_organization_and_superuser, prefix="/register", tags=["Register Organization and Superuser"])

# 5. Получение пользователей по организации
from src.api.v1.get_users_by_org import router as get_users_by_org_router
api_router.include_router(get_users_by_org_router, prefix="/organizations", tags=["Users"])

# 6. Авторизация (логин)
from src.api.v1.authorization import router as auth_user_router
api_router.include_router(auth_user_router, prefix="/auth", tags=["Auth users"])

# 7. Обновление токенов (refresh)
from src.api.v1.auth_refresh import router as auth_refresh_router
api_router.include_router(auth_refresh_router, prefix="/auth", tags=["Auth"])

from src.api.v1.register_user import router as register_user_router
api_router.include_router(register_user_router, prefix="/register", tags=["Register Users"])