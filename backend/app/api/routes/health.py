"""
Endpoint de verificación de salud del sistema.

Se usa en la Fase 1 para confirmar que el backend está arriba y,
opcionalmente, que la conexión a la base de datos funciona.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config.settings import get_settings
from app.db.session import get_db

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("")
def health_check():
    """Verifica que la API esté funcionando."""
    settings = get_settings()
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/db")
def health_check_db(db: Session = Depends(get_db)):
    """Verifica que la conexión con PostgreSQL esté disponible."""
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}
