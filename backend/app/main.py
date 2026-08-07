from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app import cache
from app.auth import AuthClaims, get_current_auth_user, get_current_student
from app.config import settings
from app.db import close_pool, get_pool, init_pool
from app.routers.schedule import router as schedule_router


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


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/health/db")
async def health_db() -> dict:
    result = await get_pool().fetchval("SELECT 1")
    return {"status": "ok", "result": result}


def _serialize_student(row: dict) -> dict:
    return {
        "id": str(row["id"]),
        "email": row["email"],
        "first_name": row["first_name"],
        "last_name": row["last_name"],
        "class_standing": row["class_standing"],
        "current_term": row["current_term"],
        "has_completed_tutorial": row["has_completed_tutorial"],
        "onboarding_complete": row["onboarding_completed_at"] is not None,
    }


class CreateStudentRequest(BaseModel):
    first_name: str
    last_name: str


@app.post("/students/me", status_code=201)
async def create_me(
    body: CreateStudentRequest,
    auth: AuthClaims = Depends(get_current_auth_user),
) -> dict:
    # Idempotent: a retried call (double network request, re-triggered
    # verification) returns the existing row instead of erroring, since
    # this is meant to be called exactly once per account in practice.
    row = await get_pool().fetchrow(
        """
        insert into students (id, email, first_name, last_name)
        values ($1, $2, $3, $4)
        on conflict (id) do nothing
        returning *
        """,
        auth.user_id,
        auth.email,
        body.first_name,
        body.last_name,
    )
    if row is None:
        row = await get_pool().fetchrow(
            "select * from students where id = $1", auth.user_id
        )
    return _serialize_student(dict(row))


@app.get("/students/me")
async def get_me(student: dict = Depends(get_current_student)) -> dict:
    return _serialize_student(student)
