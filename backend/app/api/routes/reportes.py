"""Endpoint de reportes (sección 21 de los requisitos)."""

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.api.dependencies.auth import require_roles
from app.db.session import get_db
from app.services.reporte_service import ReporteService

router = APIRouter(
    prefix="/reportes",
    tags=["Reportes"],
    dependencies=[Depends(require_roles("ADMINISTRADOR"))],
)


@router.get("/sesiones/{sesion_prueba_id}/pdf")
def descargar_reporte_pdf(sesion_prueba_id: int, db: Session = Depends(get_db)):
    """Descarga el reporte PDF de resultados de una sesión ya calificada."""
    service = ReporteService(db)
    pdf_bytes = service.generar_pdf_resultado(sesion_prueba_id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="reporte_sesion_{sesion_prueba_id}.pdf"'
        },
    )
