"""Servicio que arma el resumen del dashboard administrativo."""

from sqlalchemy.orm import Session

from app.repositories.candidato_repository import CandidatoRepository
from app.repositories.dashboard_repository import DashboardRepository
from app.schemas.candidato import CandidatoOut, CatalogoRef, EmpresaRef
from app.schemas.dashboard import DashboardResumen


class DashboardService:
    def __init__(self, db: Session):
        self.repo = DashboardRepository(db)
        self.candidatos = CandidatoRepository(db)

    def _catalogo_ref(self, item) -> CatalogoRef | None:
        if item is None:
            return None
        return CatalogoRef(id=item.id, codigo=item.codigo, nombre=item.nombre)

    def _candidato_a_out(self, candidato) -> CandidatoOut:
        return CandidatoOut(
            id=candidato.id,
            nombre=candidato.nombre,
            apellidos=candidato.apellidos,
            correo=candidato.correo,
            puesto=candidato.puesto,
            fecha_nacimiento=candidato.fecha_nacimiento,
            activo=candidato.activo,
            creado_en=candidato.creado_en,
            empresa=(
                EmpresaRef(
                    id=candidato.empresa.id,
                    nombre_comercial=candidato.empresa.nombre_comercial,
                )
                if candidato.empresa
                else None
            ),
            sexo=self._catalogo_ref(candidato.sexo),
            escolaridad=self._catalogo_ref(candidato.escolaridad),
            estatus=self._catalogo_ref(candidato.estatus),
        )

    def obtener_resumen(self, limite_recientes: int = 5) -> DashboardResumen:
        return DashboardResumen(
            total_evaluados=self.repo.total_evaluados(),
            total_evaluaciones_disponibles=self.repo.total_pruebas_disponibles(),
            total_resultados=self.repo.total_resultados(),
            evaluaciones_pendientes=self.repo.total_asignaciones_por_estatus("PENDIENTE"),
            evaluaciones_en_proceso=self.repo.total_asignaciones_por_estatus("EN_PROCESO"),
            evaluaciones_completadas=self.repo.total_asignaciones_por_estatus("COMPLETADA"),
            evaluados_recientes=[
                self._candidato_a_out(c)
                for c in self.candidatos.list_recientes(limit=limite_recientes)
            ],
        )
