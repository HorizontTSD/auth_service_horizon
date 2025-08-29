from logging import getLogger
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import DatabaseError, SQLAlchemyError

from src.models.user_models import Permission
from src.session import db_manager

logger = getLogger(__name__)

async def fetch_permissions_mapping():
    try:
        async with db_manager.get_db_session() as session:
            query = select(Permission.code)
            result = await session.execute(query)
            rows = result.scalars().all()
            return {"permissions": rows}

    except DatabaseError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ошибка подключения к базе данных"
        )

    except SQLAlchemyError as e:
        logger.error(f"Ошибка выполнения запроса к базе данных: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка выполнения запроса к базе данных"
        )

    except Exception as e:
        logger.error(f"Внутренняя ошибка сервера: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Внутренняя ошибка сервера"
        )