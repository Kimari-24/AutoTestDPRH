"""Repositorio de acceso a datos para `UsuarioTemporal` (credenciales
temporales de acceso del portal del evaluado, sección 8)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.candidato import UsuarioTemporal


class AccesoTemporalRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, acceso_id: int) -> UsuarioTemporal | None:
        return self.db.get(UsuarioTemporal, acceso_id)

    def get_by_usuario(self, usuario: str) -> UsuarioTemporal | None:
        stmt = (
            select(UsuarioTemporal)
            .options(selectinload(UsuarioTemporal.candidato))
            .where(UsuarioTemporal.usuario == usuario)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def list_por_candidato(self, candidato_id: int) -> list[UsuarioTemporal]:
        stmt = (
            select(UsuarioTemporal)
            .where(UsuarioTemporal.candidato_id == candidato_id)
            .order_by(UsuarioTemporal.creado_en.desc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def create(self, acceso: UsuarioTemporal) -> UsuarioTemporal:
        self.db.add(acceso)
        self.db.flush()
        return acceso

    def save(self) -> None:
        self.db.flush()
