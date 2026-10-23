"""Repositorios de acceso a datos para el catálogo de pruebas
(categorías, pruebas y sus versiones)."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.catalogo_prueba import CategoriaPrueba, Prueba
from app.models.versionado import VersionPrueba


class CategoriaPruebaRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, categoria_id: int) -> CategoriaPrueba | None:
        return self.db.get(CategoriaPrueba, categoria_id)

    def get_by_codigo(self, codigo: str) -> CategoriaPrueba | None:
        stmt = select(CategoriaPrueba).where(CategoriaPrueba.codigo == codigo)
        return self.db.execute(stmt).scalar_one_or_none()

    def list(self) -> list[CategoriaPrueba]:
        stmt = select(CategoriaPrueba).order_by(CategoriaPrueba.orden, CategoriaPrueba.nombre)
        return list(self.db.execute(stmt).scalars().all())

    def create(self, categoria: CategoriaPrueba) -> CategoriaPrueba:
        self.db.add(categoria)
        self.db.flush()
        return categoria

    def save(self) -> None:
        self.db.flush()


class PruebaRepository:
    def __init__(self, db: Session):
        self.db = db

    def _query_base(self):
        return select(Prueba).options(selectinload(Prueba.categoria))

    def get_by_id(self, prueba_id: int) -> Prueba | None:
        stmt = self._query_base().where(Prueba.id == prueba_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_codigo(self, codigo: str) -> Prueba | None:
        stmt = self._query_base().where(Prueba.codigo == codigo)
        return self.db.execute(stmt).scalar_one_or_none()

    def list(
        self,
        skip: int = 0,
        limit: int = 50,
        categoria_id: int | None = None,
        solo_activas: bool = False,
    ) -> list[Prueba]:
        stmt = self._query_base()
        if categoria_id is not None:
            stmt = stmt.where(Prueba.categoria_id == categoria_id)
        if solo_activas:
            stmt = stmt.where(Prueba.activa.is_(True))
        stmt = stmt.order_by(Prueba.nombre).offset(skip).limit(limit)
        return list(self.db.execute(stmt).scalars().all())

    def count_preguntas_activas(self, prueba_id: int) -> int:
        from app.models.catalogo_prueba import Pregunta

        stmt = (
            select(func.count())
            .select_from(Pregunta)
            .join(VersionPrueba, Pregunta.version_prueba_id == VersionPrueba.id)
            .where(VersionPrueba.prueba_id == prueba_id, Pregunta.activa.is_(True))
        )
        return self.db.execute(stmt).scalar_one()

    def create(self, prueba: Prueba) -> Prueba:
        self.db.add(prueba)
        self.db.flush()
        return prueba

    def save(self) -> None:
        self.db.flush()


class VersionPruebaRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, version_id: int) -> VersionPrueba | None:
        return self.db.get(VersionPrueba, version_id)

    def list_por_prueba(self, prueba_id: int) -> list[VersionPrueba]:
        stmt = (
            select(VersionPrueba)
            .where(VersionPrueba.prueba_id == prueba_id)
            .order_by(VersionPrueba.numero_version.desc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_ultima_version(self, prueba_id: int) -> VersionPrueba | None:
        stmt = (
            select(VersionPrueba)
            .where(VersionPrueba.prueba_id == prueba_id)
            .order_by(VersionPrueba.numero_version.desc())
            .limit(1)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_version_activa(self, prueba_id: int) -> VersionPrueba | None:
        stmt = select(VersionPrueba).where(
            VersionPrueba.prueba_id == prueba_id, VersionPrueba.activa.is_(True)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def desactivar_todas(self, prueba_id: int) -> None:
        for version in self.list_por_prueba(prueba_id):
            version.activa = False
        self.db.flush()

    def create(self, prueba_id: int, notas: str | None = None) -> VersionPrueba:
        ultima = self.get_ultima_version(prueba_id)
        siguiente_numero = (ultima.numero_version + 1) if ultima else 1

        self.desactivar_todas(prueba_id)

        version = VersionPrueba(
            prueba_id=prueba_id,
            numero_version=siguiente_numero,
            activa=True,
            notas=notas,
            creado_en=datetime.now(timezone.utc),
        )
        self.db.add(version)
        self.db.flush()
        return version

    def save(self) -> None:
        self.db.flush()
