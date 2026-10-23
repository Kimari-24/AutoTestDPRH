from app.schemas.candidato import CandidatoOut
from pydantic import BaseModel


class DashboardResumen(BaseModel):
    """Datos que muestra el dashboard administrativo al cargar (sección 15)."""

    total_evaluados: int
    total_evaluaciones_disponibles: int
    total_resultados: int
    evaluaciones_pendientes: int
    evaluaciones_en_proceso: int
    evaluaciones_completadas: int
    evaluados_recientes: list[CandidatoOut]
