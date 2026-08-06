from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI

from app.auth import get_current_student
from app.config import settings
from app.db import close_pool, get_pool, init_pool


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_pool()
    yield
    await close_pool()


app = FastAPI(title="ORU Scheduling Engine", lifespan=lifespan)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/health/db")
async def health_db() -> dict:
    result = await get_pool().fetchval("SELECT 1")
    return {"status": "ok", "result": result}


@app.get("/students/me")
async def get_me(student: dict = Depends(get_current_student)) -> dict:
    return {
        "id": str(student["id"]),
        "email": student["email"],
        "first_name": student["first_name"],
        "last_name": student["last_name"],
        "class_standing": student["class_standing"],
        "current_term": student["current_term"],
        "has_completed_tutorial": student["has_completed_tutorial"],
    }
