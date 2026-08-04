from typing import Any, List, Union, Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Turnero Municipalidad de Armstrong"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"

    # CORS
    BACKEND_CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "https://turnos.armstrong.gob.ar",
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            v_str = v.strip()
            if not v_str:
                return []
            if v_str.startswith("[") and v_str.endswith("]"):
                import json
                try:
                    parsed = json.loads(v_str)
                    if isinstance(parsed, list):
                        return [str(item).strip() for item in parsed]
                except Exception:
                    content = v_str[1:-1].strip()
                    if not content:
                        return []
                    return [item.strip().strip("'\"") for item in content.split(",") if item.strip()]
            return [i.strip().strip("'\"") for i in v_str.split(",") if i.strip()]
        elif isinstance(v, list):
            return [str(item).strip() for item in v]
        raise ValueError(v)

    # Database (PostgreSQL 18)
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "password123"
    POSTGRES_DB: str = "turnero_db"
    POSTGRES_PORT: str = "5432"

    @property
    def sync_database_url(self) -> str:
        return f"postgresql+psycopg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def async_database_url(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # Redis 8
    REDIS_HOST: str = "localhost"
    REDIS_PORT: str = "6379"
    REDIS_URL: Optional[str] = None

    @property
    def redis_url(self) -> str:
        if self.REDIS_URL:
            return self.REDIS_URL
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    # JWT & Auth
    JWT_SECRET: str = "supersecretjwtkeyforlocaldevelopment1234567890!"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    SESSION_COOKIE_NAME: str = "session"
    # Cookie `Secure` flag: False en desarrollo (HTTP local), True en producción (HTTPS).
    # Cumple infraestructura-seguridad.md §3.1 (cookie Secure obligatoria).
    SESSION_COOKIE_SECURE: bool = False
    SESSION_COOKIE_SAMESITE: str = "lax"

    # Password reset tokens (almacenados en Redis con TTL corto)
    PASSWORD_RESET_TOKEN_TTL_MINUTES: int = 15
    # URL pública del frontend, usada para construir el enlace de reseteo en DEV (logs).
    APP_BASE_URL: str = "http://localhost:3000"

    # PII Encryption & Search Hashing
    # Fernet key must be 32 base64-encoded bytes
    PII_SECRET_KEY: str = "d3Z4eF9hYmNfZGVmX2doaV9qa2xfbW5vX3Bxcl9zdHV2d3g="
    DNI_HMAC_SALT: str = "armstrong_fixed_salt_for_dni_search_2026"
    CARNET_HMAC_SALT: str = "armstrong_fixed_salt_for_carnet_search_2026"

    # Archivos estáticos (uploads de formularios PDF/DOCX)
    UPLOAD_DIR: str = "uploads"
    STATIC_URL_PREFIX: str = "/static/uploads"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # ---- Helpers de entorno ----
    # Centraliza la pregunta "¿estamos en prod?" para que el resto del código
    # no repita comparaciones mágicas contra ENVIRONMENT. En producción Redis es
    # obligatorio; en dev se tolera su ausencia con un mock en memoria.
    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower().strip() == "production"

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT.lower().strip() == "development"

    def model_post_init(self, __context: Any) -> None:
        if self.is_production:
            self.SESSION_COOKIE_SECURE = True


settings = Settings()
