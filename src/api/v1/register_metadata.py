from fastapi import APIRouter, HTTPException
from src.services.permissions_mapper import fetch_permissions_mapping
from src.services.roles_service import get_all_roles
from src.schemas import PermissionsResponse, RolesResponse
from src.core.logger import logger

router = APIRouter()


@router.get('/roles_list', response_model=RolesResponse)
async def get_roles() -> RolesResponse:
    """
    Эндпоинт для получения данных для выпадающего списка ролей.

    Description:
    - Предназначен для фронтэнда для получения значений для выпадающего списка.
    - Возвращает `roles` — плоский список всех ролей, чтобы заполнить выпадающий список.

    Returns:
    - **JSON**:
        - `roles`: список всех ролей для выпадающего списка.

    Example Response:
    ```json
    {
        "roles": ["user", "admin", ...]
    }
    ```

    Raises:    
    - **HTTPException 500**: При ошибке выполнения SQL запросов
    - **HTTPException 503**: При ошибке подключения к базе данных
    """

    return await get_all_roles()


@router.get("/permissions_list", response_model=PermissionsResponse)
async def get_permissions_list():
    """
        Эндпоинт для получения данных для выпадающего списка разрешений.

        Description:
        - Предназначен для фронтэнда для получения значений для выпадающего списка.
        - Возвращает `permissions` — плоский список всех кодов разрешений, чтобы заполнить выпадающий список.

        Returns:
        - **JSON**:
          - `permissions`: список всех кодов разрешений для выпадающего списка.

        Example Response:
        ```json
        {
            "permissions": ["user.create", "forecast.edit", "organization.view"]
        }
        ```

        Raises:
        - **HTTPException 500**: Если произошла ошибка при подключении к базе или получении разрешений.
        """
    try:
        result = await fetch_permissions_mapping()
        return result
    except Exception as e:
        logger.error(f"Ошибка при получении информации о таблицах: {e}")
        raise HTTPException(
            status_code=500,
            detail="Не удалось получить информацию о таблицах",
            headers={"X-Error": str(e)},
        )
