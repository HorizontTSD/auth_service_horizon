# src/api/api_routers.py
from fastapi import APIRouter

api_router = APIRouter()

from src.api.v1.get_tables_info import router as get_tables_info_router
from src.api.v1.get_users_by_org import router as get_users_by_org_router

api_router.include_router(get_tables_info_router, prefix="/tables-info", tags=["Check Test Connection"])
api_router.include_router(get_users_by_org_router, tags=["Users"]) 