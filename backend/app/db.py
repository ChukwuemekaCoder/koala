import asyncpg

from app.config import settings

pool: asyncpg.Pool | None = None


async def init_pool() -> None:
    global pool
    # statement_cache_size=0: required for pgbouncer transaction-mode pooling
    # (Supabase's Connection pooling URI), which doesn't support prepared statements.
    pool = await asyncpg.create_pool(settings.database_url, statement_cache_size=0)


async def close_pool() -> None:
    if pool is not None:
        await pool.close()


def get_pool() -> asyncpg.Pool:
    assert pool is not None, "DB pool not initialized"
    return pool
