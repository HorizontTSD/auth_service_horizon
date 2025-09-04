from fastapi import APIRouter, Depends
from src.core.token import jwt_token_validator

router = APIRouter()

@router.get("/access_token", summary="Проверка access_token")
async def check_access_token(payload=Depends(jwt_token_validator)):
    return {"valid": True}
