"""Repositorio de acceso a datos para `Candidato` (evaluado)."""

from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.aplicacion import Asignacion, SesionPrueba
from app.models.candidato import Candidato


class CandidatoRepository:
    def __init__(self, db: Session):
        self.db = db

    def _query_base(self):
        return select(Candidato).options(
            selectinload(Candidato.empresa),
            selectinload(Candidato.sexo),
            selectinload(Candidato.escolaridad),
            selectinload(Candidato.estatus),
        )

    def get_by_id(self, candidato_id: int) -> Candidato | None:
        stmt = self._query_base().where(Candidato.id == candidato_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_expediente(self, candidato_id: int) -> Candidato | None:
        """Candidato con sus asignaciones (evaluaciones) precargadas."""
        stmt = self._query_base().where(Candidato.id == candidato_id).options(
            selectinload(Candidato.asignaciones).selectinload(Asignacion.prueba),
            selectinload(Candidato.asignaciones).selectinload(Asignacion.estatus),
            selectinload(Candidato.asignaciones)
            .selectinload(Asignacion.sesiones)
            .selectinload(SesionPrueba.resultado),
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_correo(self, correo: str) -> Candidato | None:
        stmt = (
            self._query_base()
            .where(func.lower(Candidato.correo) == correo.strip().lower())
            .order_by(Candidato.id)
        )
        return self.db.execute(stmt).scalars().first()

    def list(
        self,
        skip: int = 0,
        limit: int = 50,
        buscar: str | None = None,
        empresa_id: int | None = None,
        estatus_candidato_id: int | None = None,
        solo_activos: bool = False,
    ) -> list[Candidato]:
        stmt = self._query_base()

        if buscar:
            patron = f"%{buscar.lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(Candidato.nombre).like(patron),
                    func.lower(Candidato.apellidos).like(patron),
                    func.lower(Candidato.correo).like(patron),
                )
            )
        if empresa_id is not None:
            stmt = stmt.where(Candidato.empresa_id == empresa_id)
        if estatus_candidato_id is not None:
            stmt = stmt.where(Candidato.estatus_candidato_id == estatus_candidato_id)
        if solo_activos:
            stmt = stmt.where(Candidato.activo.is_(True))

        stmt = stmt.order_by(Candidato.creado_en.desc()).offset(skip).limit(limit)
        return list(self.db.execute(stmt).scalars().all())

    def count(self, solo_activos: bool = False) -> int:
        stmt = select(func.count()).select_from(Candidato)
        if solo_activos:
            stmt = stmt.where(Candidato.activo.is_(True))
        return self.db.execute(stmt).scalar_one()

    def list_recientes(self, limit: int = 5) -> list[Candidato]:
        stmt = (
            self._query_base()
            .order_by(Candidato.creado_en.desc())
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())

    def create(self, candidato: Candidato) -> Candidato:
        self.db.add(candidato)
        self.db.flush()
        return candidato

    def save(self) -> None:
        self.db.flush()
