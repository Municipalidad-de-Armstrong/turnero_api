from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import redis.asyncio as aioredis
from app.core.database import get_db
from app.core.config import settings

router = APIRouter()


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check(db: AsyncSession = Depends(get_db)):
    """Health check endpoint to verify database and Redis connectivity."""
    db_status = "offline"
    redis_status = "offline"
    errors = []

    # Verify PostgreSQL connection
    try:
        await db.execute(text("SELECT 1"))
        db_status = "online"
    except Exception as e:
        errors.append(f"Database error: {str(e)}")

    # Verify Redis connection
    try:
        redis_client = aioredis.from_url(settings.redis_url)
        if await redis_client.ping():
            redis_status = "online"
        await redis_client.close()
    except Exception as e:
        errors.append(f"Redis error: {str(e)}")

    if db_status != "online" or redis_status != "online":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "unhealthy",
                "database": db_status,
                "redis": redis_status,
                "errors": errors,
            },
        )

    return {
        "status": "healthy",
        "database": db_status,
        "redis": redis_status,
    }
