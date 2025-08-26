from fastapi import APIRouter, Depends

from services.auth_service import auth
from src.schemas import AuthRequest, AuthResponse

router = APIRouter()


@router.post('/')
async def auth_user(auth_data: AuthRequest = Depends(AuthRequest)) -> AuthResponse:
        """
        Эндпоинт для авторизации пользователей приложения

        Description:
        - Предназначен для фронтэнда для авторизации и получения refresh и access токенов

        Returns:
        - **JSON**:
            - `access_token`: токен, предназначенный для авторизованного доступа
            - `refresh_token`: токен для обновления access_token
            - `token_type`: тип токена
            - `expires_in`: длительность access_token
            - `refresh_expires_in`: длительность refresh_token
            - `user`: {
                    `id`: id пользователя
                    `organization_id`: id организации пользователя
                    `role`: роль пользователя
                    `permissions`: права пользователя

        Example Response:
        ```json
            {
                "access_token": "jwt",
                "refresh_token": "jwt",
                "token_type": "Bearer",
                "expires_in": 900,
                "refresh_expires_in": 2592000,
                "user": {
                    "id": 123,
                    "organization_id": 1,
                    "role": "admin",
                    "permissions": [...]
            }
        ```

        Raises:
        - **HTTPException 401**: При неверных учётных данных
        - **HTTPException 401**: Если пользователь заблокирован, удалён или неактивен
        - **HTTPException 500**: Если произошла ошибка при подключении к базе или авторизации.
        """
        
        return await auth(login=auth_data.login, password=auth_data.password)