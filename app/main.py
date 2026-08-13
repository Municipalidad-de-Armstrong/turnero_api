import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1 import (
    admin_config,
    admin_operation,
    admin_users,
    admin_usurpations,
    agenda,
    areas,
    auth,
    health,
    notifications,
    tramites,
    turnos,
    users,
)
from app.core.config import settings
from app.core.database import async_session_maker
from app.core.redis import close_redis_client, get_redis_client, redis_kind
from app.core.seed import seed_initial_data

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(os.path.join("uploads", "tramites"), exist_ok=True)

    # Inicializa el cliente Redis según entorno:
    # - producción: Redis real obligatorio. Si no responde, aborta el arranque
    #   (fail-fast) para no servir tráfico sin servicio de sesiones.
    # - desarrollo: usa Redis real si está; si no, mock en memoria.
    try:
        client = await get_redis_client()
        # PING real para validar conectividad. En prod el cliente es perezoso,
        # así que sin esto arrancaría aunque Redis no exista. El mock en dev
        # implementa ping() y devuelve True.
        await client.ping()
    except Exception:
        if settings.is_production:
            logger.critical(
                "No se pudo conectar a Redis en producción. Abortando arranque."
            )
            raise
        logger.warning("Redis no disponible en desarrollo: modo degradado.", exc_info=True)

    if settings.is_production and redis_kind() != "real":
        # Salvaguarda: get_redis_client() no debería devolver mock en prod, pero
        # reforzamos el contrato por si cambia la lógica de selección.
        raise RuntimeError(
            "En producción Redis es obligatorio y no se puede usar el mock en memoria."
        )

    if settings.is_development and redis_kind() == "memory":
        logger.warning(
            "Arrancando en DEV con mock Redis en memoria: logout/blacklist/reset "
            "NO persisten entre reinicios."
        )

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
app.include_router(admin_config.router, prefix=settings.API_V1_STR)
app.include_router(admin_users.router, prefix=settings.API_V1_STR)
app.include_router(admin_usurpations.router, prefix=settings.API_V1_STR)
app.include_router(admin_operation.router, prefix=settings.API_V1_STR)
app.include_router(users.router, prefix=settings.API_V1_STR)
app.include_router(areas.router, prefix=settings.API_V1_STR)
app.include_router(tramites.router, prefix=settings.API_V1_STR)
app.include_router(agenda.router, prefix=settings.API_V1_STR)
app.include_router(turnos.router, prefix=f"{settings.API_V1_STR}/turnos", tags=["turnos"])
app.include_router(notifications.router, prefix=settings.API_V1_STR)



@app.get("/")
def root():
    return {"message": "Welcome to Turnero Municipalidad de Armstrong API"}
