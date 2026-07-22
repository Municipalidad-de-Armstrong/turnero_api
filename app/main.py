from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.core.config import settings
from app.core.database import Base, async_session_maker, engine
from app.models.role import Role
import app.models  # noqa: F401
from app.api.v1 import admin_usurpations, auth, health, users


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_maker() as session:
        roles_data = [
            (1, "ciudadano", "Ciudadano solicitante de turnos"),
            (2, "administrativo", "Personal administrativo de atención"),
            (3, "administrador", "Administrador general del sistema"),
        ]
        for role_id, role_name, role_desc in roles_data:
            stmt = select(Role).where(Role.id == role_id)
            res = await session.execute(stmt)
            if not res.scalar_one_or_none():
                session.add(Role(id=role_id, nombre=role_name, descripcion=role_desc))
        await session.commit()

    yield


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

app.include_router(health.router, prefix=settings.API_V1_STR)
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(admin_usurpations.router, prefix=settings.API_V1_STR)
app.include_router(users.router, prefix=settings.API_V1_STR)


@app.get("/")
def root():
    return {"message": "Welcome to Turnero Municipalidad de Armstrong API"}
