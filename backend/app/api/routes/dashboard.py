"""Endpoint del dashboard administrativo (sección 15 de los requisitos)."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies.auth import require_roles
from app.db.session import get_db
from app.schemas.dashboard import DashboardResumen
from app.services.dashboard_service import DashboardService

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"],
    dependencies=[Depends(require_roles("ADMINISTRADOR"))],
)


@router.get("/resumen", response_model=DashboardResumen)
def obtener_resumen(db: Session = Depends(get_db)):
    """Tarjetas estadísticas y evaluados recientes del dashboard."""
    service = DashboardService(db)
    return service.obtener_resumen()
