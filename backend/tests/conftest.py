import asyncpg
import pytest_asyncio

from app.config import settings


@pytest_asyncio.fixture
async def db_pool():
    pool = await asyncpg.create_pool(settings.database_url, statement_cache_size=0)
    yield pool
    await pool.close()
