from fastapi import APIRouter, Body

from services.auth_service import auth, logout
from src.schemas import AuthRequest, AuthResponse, LogoutRequest, LogoutResponse

router = APIRouter()


@router.post('/login', response_model=AuthResponse)
async def auth_user(
        auth_data: AuthRequest = Body(..., example={
                'login': 'test_user',
                'password': 'qwerty123'
        })
        ) -> AuthResponse:
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
                    `roles`: роли пользователя
                    `permissions`: права пользователя
                }

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
                    "roles": ["admin", ...],
                    "permissions": [...]
            }
        ```

        Raises:
        - **HTTPException 400**: При ошибке валидации входных данных
        - **HTTPException 401**: При неверных учётных данных
        - **HTTPException 401**: Если пользователь заблокирован, удалён или неактивен
        """
        
        return await auth(login=auth_data.login, password=auth_data.password)

@router.post('/logout', response_model=LogoutResponse)
async def logout_user(
            logout_data: LogoutRequest = Body(..., example={
                    'refresh_token': 'eyCshr3bGciOihfd4S1NsaIsInR5da25CLKpikpXVCJ9.eyJzdWIiOi.....'
            })
        ) -> LogoutResponse:
        """
        Эндпоинт для инвалидации refresh-токена пользователя

        Description:
        - Предназначен для фронтэнда для инвалидации refresh-токена пользователя

        Returns:
        - **JSON**:
            - `detail`: детали ответа

        Example Response:
        ```json
            {
                "detail": "Logout successful",
            }
        ```

        Raises:
        - **HTTPException 401**: При невалидном токене
        """
        return await logout(refresh_token=logout_data.refresh_token)