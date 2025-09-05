from fastapi import APIRouter, Depends
from src.core.token import jwt_token_validator
from src.schemas import AccessTokenResponse

router = APIRouter()

@router.get("/access_token", summary="Проверка access_token", response_model=AccessTokenResponse)
async def check_access_token(user_info=Depends(jwt_token_validator)):
    return AccessTokenResponse(
        user_id=user_info.get('sub'),
        org_id=user_info.get('organization_id'),
        roles=user_info.get('roles'),
        permissions=user_info.get('permissions')
    )
