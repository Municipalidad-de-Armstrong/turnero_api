import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1 import admin_usurpations, areas, auth, health, tramites, users
from app.core.config import settings
from app.core.database import Base, async_session_maker, engine
from app.core.redis import close_redis_client
from app.core.seed import seed_initial_data


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(os.path.join("uploads", "tramites"), exist_ok=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_maker() as session:
        await seed_initial_data(session)

    yield

    # Cierra el pool de Redis compartido al apagar la aplicación.
    await close_redis_client()


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=["*"],
    )

os.makedirs("uploads", exist_ok=True)
app.mount("/static/uploads", StaticFiles(directory="uploads"), name="static_uploads")

app.include_router(health.router, prefix=settings.API_V1_STR)
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(admin_usurpations.router, prefix=settings.API_V1_STR)
app.include_router(users.router, prefix=settings.API_V1_STR)
app.include_router(areas.router, prefix=settings.API_V1_STR)
app.include_router(tramites.router, prefix=settings.API_V1_STR)


@app.get("/")
def root():
    return {"message": "Welcome to Turnero Municipalidad de Armstrong API"}
