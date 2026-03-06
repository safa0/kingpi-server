import time

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from kingpi.dependencies import get_redis_client, get_session_factory

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok"}


async def _check_db(
    session_factory: async_sessionmaker[AsyncSession],
) -> dict:
    start = time.monotonic()
    try:
        async with session_factory() as session:
            await session.execute(text("SELECT 1"))
        elapsed = (time.monotonic() - start) * 1000
        return {"status": "up", "response_time_ms": round(elapsed, 2)}
    except Exception:
        elapsed = (time.monotonic() - start) * 1000
        return {"status": "down", "response_time_ms": round(elapsed, 2)}


async def _check_redis(redis_client: aioredis.Redis) -> dict:
    start = time.monotonic()
    try:
        await redis_client.ping()
        elapsed = (time.monotonic() - start) * 1000
        return {"status": "up", "response_time_ms": round(elapsed, 2)}
    except Exception:
        elapsed = (time.monotonic() - start) * 1000
        return {"status": "down", "response_time_ms": round(elapsed, 2)}


@router.get("/health/ready")
async def health_ready(
    session_factory: async_sessionmaker[AsyncSession] = Depends(get_session_factory),
    redis_client: aioredis.Redis = Depends(get_redis_client),
):
    db_check = await _check_db(session_factory)
    redis_check = await _check_redis(redis_client)

    db_up = db_check["status"] == "up"
    redis_up = redis_check["status"] == "up"

    if db_up and redis_up:
        status = "healthy"
    elif db_up and not redis_up:
        status = "degraded"
    else:
        status = "unhealthy"

    status_code = 200 if status in ("healthy", "degraded") else 503

    return JSONResponse(
        status_code=status_code,
        content={
            "status": status,
            "dependencies": {
                "database": db_check,
                "redis": redis_check,
            },
        },
    )
