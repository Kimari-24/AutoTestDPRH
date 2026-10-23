"""
Configuración de conexión a la base de datos PostgreSQL mediante SQLAlchemy.

Expone:
- `engine`: el motor de conexión de SQLAlchemy.
- `SessionLocal`: fábrica de sesiones.
- `get_db`: dependencia de FastAPI para inyectar una sesión por request.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config.settings import get_settings

settings = get_settings()

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    future=True,
)


class Base(DeclarativeBase):
    """Clase base declarativa de la que heredarán todos los modelos ORM."""

    pass


def get_db() -> Generator:
    """Dependencia de FastAPI: entrega una sesión de BD y la cierra al terminar."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
