"""Servicio para que el ADMINISTRADOR asigne evaluaciones a un
evaluado (sección 14: "Asignar evaluaciones")."""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.exceptions.base import ConflictError, NotFoundError, ValidationError
from app.models.aplicacion import Asignacion
from app.repositories.asignacion_repository import AsignacionRepository
from app.repositories.auditoria_repository import BitacoraRepository
from app.repositories.candidato_repository import CandidatoRepository
from app.repositories.prueba_repository import PruebaRepository, VersionPruebaRepository


class AsignacionService:
    def __init__(self, db: Session):
        self.db = db
        self.asignaciones = AsignacionRepository(db)
        self.candidatos = CandidatoRepository(db)
        self.pruebas = PruebaRepository(db)
        self.versiones = VersionPruebaRepository(db)
        self.bitacora = BitacoraRepository(db)

    def _estatus_pendiente_id(self) -> int:
        from app.models.catalogos import EstatusPrueba

        estatus = self.db.query(EstatusPrueba).filter(EstatusPrueba.codigo == "PENDIENTE").first()
        if estatus is None:
            from app.core.exceptions.base import ValidationError

            raise ValidationError("Falta el estatus_prueba 'PENDIENTE'. Ejecuta scripts/seed_catalogos.py.")
        return estatus.id

    def listar_por_candidato(self, candidato_id: int) -> list[Asignacion]:
        if self.candidatos.get_by_id(candidato_id) is None:
            raise NotFoundError("Evaluado no encontrado.")
        return self.asignaciones.list_por_candidato(candidato_id)

    def asignar(
        self,
        candidato_id: int,
        prueba_id: int,
        fecha_limite: datetime | None,
        asignado_por_usuario_id: int | None = None,
    ) -> Asignacion:
        candidato = self.candidatos.get_by_id(candidato_id)
        if candidato is None:
            raise NotFoundError("Evaluado no encontrado.")
        prueba = self.pruebas.get_by_id(prueba_id)
        if prueba is None:
            raise NotFoundError("Evaluación no encontrada.")

        # BUG-10 de QA: no se asignan evaluaciones a un evaluado
        # desactivado, ni evaluaciones desactivadas.
        if not candidato.activo:
            raise ConflictError("No se puede asignar una evaluación a un evaluado desactivado.")
        if not prueba.activa:
            raise ConflictError("No se puede asignar una evaluación desactivada.")

        # BUG-11 de QA: una evaluación sin versión vigente no se puede
        # aplicar; es mejor avisar al asignar que fallar ante el evaluado.
        version_activa = self.versiones.get_version_activa(prueba_id)
        if version_activa is None:
            raise ValidationError(
                "La evaluación no tiene una versión vigente. Crea una versión y agrega "
                "preguntas antes de asignarla."
            )

        asignacion = Asignacion(
            candidato_id=candidato_id,
            prueba_id=prueba_id,
            version_prueba_id=version_activa.id,
            asignado_por_usuario_id=asignado_por_usuario_id,
            estatus_prueba_id=self._estatus_pendiente_id(),
            fecha_asignacion=datetime.now(timezone.utc),
            fecha_limite=fecha_limite,
        )
        self.asignaciones.create(asignacion)
        self.bitacora.registrar(
            usuario_id=asignado_por_usuario_id,
            accion="ASIGNAR",
            entidad="asignaciones",
            entidad_id=asignacion.id,
        )
        self.db.commit()
        return self.asignaciones.get_by_id(asignacion.id)
