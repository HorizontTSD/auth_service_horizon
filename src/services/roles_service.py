import logging

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import DatabaseError, SQLAlchemyError

from src.models.user_models import Role
from src.session import db_manager

logger = logging.getLogger(__name__)

async def get_all_roles():
    try:
        async with db_manager.get_db_session() as session:
            query = select(Role.name)
            result = await session.execute(query)
            return {'roles': result.scalars().all()}
        
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