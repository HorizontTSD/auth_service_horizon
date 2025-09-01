from fastapi import APIRouter

from src.schemas import RolesResponse
from src.services.roles_service import get_all_roles

router = APIRouter()

@router.get('/', response_model=RolesResponse)
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