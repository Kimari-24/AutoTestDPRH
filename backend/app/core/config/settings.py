"""
Configuración centralizada de la aplicación AutoTest DPRH.

Utiliza pydantic-settings para leer variables de entorno de forma
tipada y validada. Todas las demás capas del backend deben obtener
su configuración desde una instancia de `Settings`, nunca leyendo
`os.environ` directamente.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_RAIZ_BACKEND = Path(__file__).resolve().parents[3]
_RAIZ_PROYECTO = _RAIZ_BACKEND.parent


class Settings(BaseSettings):
    """Variables de configuración de la aplicación."""

    # Se leen DOS posibles archivos .env, sin importar desde qué carpeta
    # se ejecute el comando: el de la raíz del proyecto (el que crea
    # `cp .env.example .env`, también usado por docker-compose) y el de
    # backend/. El de backend/ tiene prioridad si ambos existen. Antes
    # solo se leía ".env" de la carpeta actual, y el README mandaba crear
    # el de la raíz — el backend no lo encontraba (hallazgo de QA).
    model_config = SettingsConfigDict(
        env_file=(str(_RAIZ_PROYECTO / ".env"), str(_RAIZ_BACKEND / ".env")),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Información general ---
    APP_NAME: str = "AutoTest DPRH"
    APP_ENV: str = "development"  # development | staging | production
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True

    # --- API ---
    API_V1_PREFIX: str = "/api"

    # --- Seguridad / JWT ---
    SECRET_KEY: str = "CHANGE_ME_IN_ENV"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7
    # Vigencia máxima del token de un evaluado autenticado con acceso
    # temporal (portal de evaluados, Fase 7). Nunca excede la fecha de
    # expiración propia del acceso temporal (ver jwt.create_evaluado_access_token).
    EVALUADO_TOKEN_EXPIRE_MINUTES: int = 180

    # --- Base de datos ---
    DATABASE_URL: str = (
        "postgresql+psycopg://autotest_user:autotest_pass@localhost:5432/autotest_dprh"
    )

    # --- CORS ---
    # Se define como string (lista separada por comas) para evitar que
    # pydantic-settings intente parsear la variable de entorno como
    # JSON antes de tiempo. Usar `cors_origins_list` para obtener la
    # lista ya procesada.
    BACKEND_CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.BACKEND_CORS_ORIGINS.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Devuelve una instancia cacheada de Settings (patrón singleton)."""
    return Settings()
