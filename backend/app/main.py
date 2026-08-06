import asyncpg
from fastapi import FastAPI

from app.config import settings

app = FastAPI(title="ORU Scheduling Engine")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/health/db")
async def health_db() -> dict:
    # statement_cache_size=0: required for pgbouncer transaction-mode pooling
    # (Supabase's Connection pooling URI), which doesn't support prepared statements.
    conn = await asyncpg.connect(settings.database_url, statement_cache_size=0)
    try:
        result = await conn.fetchval("SELECT 1")
    finally:
        await conn.close()
    return {"status": "ok", "result": result}
