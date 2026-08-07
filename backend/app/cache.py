"""
Redis caching per CLAUDE.md: cache key shape schedule:{student_id}:{term}
holding serialized solver output for that semester, 1-hour TTL as a
backstop. Invalidated (all keys for a student deleted) on any of the
three mutation points: student_progress change, semester_plans override,
or a full re-solve cascade run.
"""

import json

import redis.asyncio as redis

from app.config import settings

_TTL_SECONDS = 60 * 60

client: redis.Redis | None = None


def init_client() -> None:
    global client
    client = redis.from_url(settings.redis_url, decode_responses=True)


async def close_client() -> None:
    if client is not None:
        await client.aclose()


def _key(student_id: str, term: str) -> str:
    return f"schedule:{student_id}:{term}"


async def get_cached_schedule(student_id: str, term: str) -> list[dict] | None:
    raw = await client.get(_key(student_id, term))
    return json.loads(raw) if raw is not None else None


async def set_cached_schedule(student_id: str, term: str, plan: list[dict]) -> None:
    await client.set(_key(student_id, term), json.dumps(plan), ex=_TTL_SECONDS)


async def invalidate_schedule_cache(student_id: str) -> None:
    pattern = f"schedule:{student_id}:*"
    async for key in client.scan_iter(match=pattern):
        await client.delete(key)
