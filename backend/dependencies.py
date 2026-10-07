# dependencies.py — общие зависимости FastAPI-эндпоинтов.

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import session_factory


# Создаёт отдельную сессию PostgreSQL на время одного HTTP-запроса
# и гарантированно закрывает её после завершения запроса.
async def get_database_session() -> AsyncIterator[AsyncSession]:
    async with session_factory() as database_session:
        yield database_session