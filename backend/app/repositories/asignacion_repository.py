"""Repositorio de acceso a datos para `Asignacion`."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.aplicacion import Asignacion, SesionPrueba


class AsignacionRepository:
    def __init__(self, db: Session):
        self.db = db

    def _query_base(self):
        return select(Asignacion).options(
            selectinload(Asignacion.prueba),
            selectinload(Asignacion.estatus),
            selectinload(Asignacion.sesiones),
        )

    def get_by_id(self, asignacion_id: int) -> Asignacion | None:
        stmt = self._query_base().where(Asignacion.id == asignacion_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def list_por_candidato(self, candidato_id: int) -> list[Asignacion]:
        stmt = (
            self._query_base()
            .where(Asignacion.candidato_id == candidato_id)
            .order_by(Asignacion.fecha_asignacion.desc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_sesion_en_proceso(self, asignacion_id: int) -> SesionPrueba | None:
        stmt = (
            select(SesionPrueba)
            .join(SesionPrueba.estatus)
            .where(SesionPrueba.asignacion_id == asignacion_id)
        )
        for sesion in self.db.execute(stmt).scalars().all():
            if sesion.estatus.codigo == "EN_PROCESO":
                return sesion
        return None

    def count_sesiones(self, asignacion_id: int) -> int:
        stmt = select(SesionPrueba).where(SesionPrueba.asignacion_id == asignacion_id)
        return len(list(self.db.execute(stmt).scalars().all()))

    def create(self, asignacion: Asignacion) -> Asignacion:
        self.db.add(asignacion)
        self.db.flush()
        return asignacion

    def save(self) -> None:
        self.db.flush()
