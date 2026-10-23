"""Repositorios de acceso a datos para preguntas y opciones."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.aplicacion import Respuesta
from app.models.catalogo_prueba import Opcion, Pregunta


class PreguntaRepository:
    def __init__(self, db: Session):
        self.db = db

    def _query_base(self):
        return select(Pregunta).options(
            selectinload(Pregunta.tipo_pregunta),
            selectinload(Pregunta.opciones),
        )

    def get_by_id(self, pregunta_id: int) -> Pregunta | None:
        stmt = self._query_base().where(Pregunta.id == pregunta_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def list_por_version(self, version_prueba_id: int, solo_activas: bool = False) -> list[Pregunta]:
        stmt = self._query_base().where(Pregunta.version_prueba_id == version_prueba_id)
        if solo_activas:
            stmt = stmt.where(Pregunta.activa.is_(True))
        stmt = stmt.order_by(Pregunta.orden)
        return list(self.db.execute(stmt).scalars().all())

    def count_por_version(self, version_prueba_id: int) -> int:
        stmt = (
            select(func.count())
            .select_from(Pregunta)
            .where(Pregunta.version_prueba_id == version_prueba_id)
        )
        return self.db.execute(stmt).scalar_one()

    def create(self, pregunta: Pregunta) -> Pregunta:
        self.db.add(pregunta)
        self.db.flush()
        return pregunta

    def save(self) -> None:
        self.db.flush()


class OpcionRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, opcion_id: int) -> Opcion | None:
        return self.db.get(Opcion, opcion_id)

    def list_por_pregunta(self, pregunta_id: int) -> list[Opcion]:
        stmt = select(Opcion).where(Opcion.pregunta_id == pregunta_id).order_by(Opcion.orden)
        return list(self.db.execute(stmt).scalars().all())

    def tiene_respuestas_asociadas(self, opcion_id: int) -> bool:
        stmt = select(func.count()).select_from(Respuesta).where(Respuesta.opcion_id == opcion_id)
        return self.db.execute(stmt).scalar_one() > 0

    def create(self, opcion: Opcion) -> Opcion:
        self.db.add(opcion)
        self.db.flush()
        return opcion

    def delete(self, opcion: Opcion) -> None:
        self.db.delete(opcion)
        self.db.flush()

    def save(self) -> None:
        self.db.flush()
