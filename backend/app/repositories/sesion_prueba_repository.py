"""Repositorios de acceso a datos para `SesionPrueba` y `Respuesta`."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.aplicacion import Asignacion, Respuesta, SesionPrueba


class SesionPruebaRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, sesion_id: int) -> SesionPrueba | None:
        stmt = (
            select(SesionPrueba)
            .options(
                selectinload(SesionPrueba.estatus),
                selectinload(SesionPrueba.asignacion).selectinload(Asignacion.prueba),
                selectinload(SesionPrueba.asignacion).selectinload(Asignacion.candidato),
                selectinload(SesionPrueba.respuestas),
            )
            .where(SesionPrueba.id == sesion_id)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def create(self, sesion: SesionPrueba) -> SesionPrueba:
        self.db.add(sesion)
        self.db.flush()
        return sesion

    def save(self) -> None:
        self.db.flush()


class RespuestaRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_por_sesion_y_pregunta(self, sesion_id: int, pregunta_id: int) -> Respuesta | None:
        stmt = select(Respuesta).where(
            Respuesta.sesion_prueba_id == sesion_id, Respuesta.pregunta_id == pregunta_id
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def list_por_sesion(self, sesion_id: int) -> list[Respuesta]:
        stmt = select(Respuesta).where(Respuesta.sesion_prueba_id == sesion_id)
        return list(self.db.execute(stmt).scalars().all())

    def create(self, respuesta: Respuesta) -> Respuesta:
        self.db.add(respuesta)
        self.db.flush()
        return respuesta

    def save(self) -> None:
        self.db.flush()
