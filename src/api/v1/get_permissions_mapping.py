from fastapi import APIRouter, HTTPException
from src.services.permissions_mapper import fetch_permissions_mapping
from src.schemas import PermissionsResponse
from src.core.logger import logger

router = APIRouter()


@router.get("/", response_model=PermissionsResponse)
async def func_get_permissions_mapping():
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
