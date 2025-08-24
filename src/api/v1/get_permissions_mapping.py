from fastapi import APIRouter, HTTPException
from src.services.permissions_mapper import fetch_permissions_mapping
from src.core.logger import logger

router = APIRouter()

@router.get("/")
async def func_get_permissions_mapping():
    """
        Эндпоинт для получения данных для выпадающего списка разрешений.

        Description:
        - Предназначен для фронтэнда для получения значений для выпадающего списка.
        - Возвращает `permission_list` — плоский список всех кодов разрешений, чтобы заполнить выпадающий список.
        - Возвращает `permission_mapping` — словарь, где ключ — код разрешения, а значение — его ID, чтобы фронт мог маппить выбранное значение на ID.

        Returns:
        - **JSON**:
          - `permission_list`: список всех кодов разрешений для выпадающего списка.
          - `permission_mapping`: словарь вида {код разрешения: id} для маппинга на ID.

        Example Response:
        ```json
        {
            "permission_list": ["user.create", "forecast.edit", "organization.view"],
            "permission_mapping": {
                "user.create": 1,
                "forecast.edit": 2,
                "organization.view": 3
            }
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
