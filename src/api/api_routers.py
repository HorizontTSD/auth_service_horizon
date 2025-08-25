from fastapi import APIRouter

api_router = APIRouter()

from src.api.v1.get_tables_info import router as get_tables_info
from src.api.v1.registration import router as register_organization_and_superuser


api_router.include_router(get_tables_info, prefix="/tables-info", tags=["Check Test Connection"])
api_router.include_router(
    register_organization_and_superuser, prefix="/register", tags=["Register Organization and Superuser"]

)