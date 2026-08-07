from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import cache
from app.config import settings
from app.db import close_pool, get_pool, init_pool
from app.routers.schedule import router as schedule_router
from app.routers.students import router as students_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_pool()
    cache.init_client()
    yield
    await cache.close_client()
    await close_pool()


app = FastAPI(title="ORU Scheduling Engine", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(schedule_router)
app.include_router(students_router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/health/db")
async def health_db() -> dict:
    result = await get_pool().fetchval("SELECT 1")
    return {"status": "ok", "result": result}
