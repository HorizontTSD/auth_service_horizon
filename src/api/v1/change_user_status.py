from fastapi import APIRouter, HTTPException, Depends, Body, status
from src.core.token import jwt_token_validator
from src.schemas import UserStatusChangeResponse, UserStatusChangeRequest
from src.services.user_service import change_user_status

router = APIRouter()

@router.post("/block", response_model=UserStatusChangeResponse, status_code=status.HTTP_200_OK)
async def block_user(
        payload: UserStatusChangeRequest = Body(
            ...,
            example={
                "login_to_change": "test_user_for_del",
            }
        ),
        user_data: dict = Depends(jwt_token_validator)
):
    """
       Эндпоинт для блокирования пользователя в организации.
   
       Description:
       - Помечает пользователя с указанным логином как заблокированного (is_block=True, is_active=False).
       - Блокировка выполняется в рамках организации, указанной в токене авторизации.
       - Требуется действующий JWT access_token с ролью 'superuser'.
   
       Raises:
       - **HTTPException 401**: Если access_token отсутствует, истёк или недействителен.
       - **HTTPException 403**: Если у пользователя нет роли 'superuser'.
       - **HTTPException 404**: Если пользователь с указанным логином не найден в организации или уже удалён.
       - **HTTPException 400**: Если пользователь удалён и его нельзя заблокировать.
       - **HTTPException 500**: Если произошла ошибка при работе с базой данных (обрабатывается глобально).
       """
    current_user_org_id = user_data.get("organization_id")
    current_user_roles = user_data.get("roles", [])
    action = "block"

    # 1. Проверка прав
    if "superuser" not in current_user_roles:
        raise HTTPException(status_code=403, detail="Недостаточно прав для блокирования пользователя")

    return await change_user_status(
        current_user_org_id=current_user_org_id,
        payload=payload,
        action=action
    )


@router.post("/unblock", response_model=UserStatusChangeResponse, status_code=status.HTTP_200_OK)
async def unblock_user(
        payload: UserStatusChangeRequest = Body(
            ...,
            example={
                "login_to_change": "test_user_for_del",
            }
        ),
        user_data: dict = Depends(jwt_token_validator)
):
    """
    Эндпоинт для разблокирования пользователя в организации.
    
    Description:
    - Помечает пользователя с указанным логином как разблокированного (is_block=False, is_active=True).
    - Разблокировка выполняется в рамках организации, указанной в токене авторизации.
    - Требуется действующий JWT access_token с ролью 'superuser'.
    
    Raises:
    - **HTTPException 401**: Если access_token отсутствует, истёк или недействителен.
    - **HTTPException 403**: Если у пользователя нет роли 'superuser'.
    - **HTTPException 404**: Если пользователь с указанным логином не найден в организации или уже удалён.
    - **HTTPException 400**: Если пользователь удалён и его нельзя разблокировать.
    - **HTTPException 500**: Если произошла ошибка при работе с базой данных (обрабатывается глобально).
    """

    current_user_org_id = user_data.get("organization_id")
    current_user_roles = user_data.get("roles", [])
    action = "unblock"

    # 1. Проверка прав
    if "superuser" not in current_user_roles:
        raise HTTPException(status_code=403, detail="Недостаточно прав для блокирования пользователя")

    return await change_user_status(
        current_user_org_id=current_user_org_id,
        payload=payload,
        action=action
    )


@router.delete("/delete", response_model=UserStatusChangeResponse, status_code=status.HTTP_200_OK)
async def delete_user(
        payload: UserStatusChangeRequest = Body(
            ...,
            example={
                "login_to_change": "test_user_for_del",
            }
        ),
        user_data: dict = Depends(jwt_token_validator)
):
    """
    Эндпоинт для удаления пользователя из организации.

    Description:
    - Помечает пользователя с указанным логином как удалённого (is_deleted=True).
    - Удаление выполняется в рамках организации, указанной в токене авторизации.
    - Требует действующий JWT access_token с ролью 'superuser'.

    Raises:
    - **HTTPException 401**: Если access_token отсутствует, истёк или недействителен.
    - **HTTPException 403**: Если у пользователя нет роли 'superuser'.
    - **HTTPException 404**: Если пользователь с указанным логином не найден в организации.
    - **HTTPException 500**: Если произошла ошибка при работе с базой данных (обрабатывается глобально).
    """
    current_user_org_id = user_data.get("organization_id")
    current_user_roles = user_data.get("roles", [])
    action = "delete"

    # 1. Проверка прав
    if "superuser" not in current_user_roles:
        raise HTTPException(status_code=403, detail="Недостаточно прав для создания пользователя")

    return await change_user_status(
        current_user_org_id=current_user_org_id,
        payload=payload,
        action=action
    )
