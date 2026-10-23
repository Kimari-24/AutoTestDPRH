"""Repositorios de acceso a datos para algoritmo, factores y escalas."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.catalogo_prueba import Algoritmo, Escala, Factor


class AlgoritmoRepository:
    def __init__(self, db: Session):
        self.db = db

    def _query_base(self):
        return select(Algoritmo).options(
            selectinload(Algoritmo.factores).selectinload(Factor.escalas)
        )

    def get_by_id(self, algoritmo_id: int) -> Algoritmo | None:
        stmt = self._query_base().where(Algoritmo.id == algoritmo_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def list_por_prueba(self, prueba_id: int) -> list[Algoritmo]:
        stmt = self._query_base().where(Algoritmo.prueba_id == prueba_id)
        return list(self.db.execute(stmt).scalars().all())

    def create(self, algoritmo: Algoritmo) -> Algoritmo:
        self.db.add(algoritmo)
        self.db.flush()
        return algoritmo

    def save(self) -> None:
        self.db.flush()


class FactorRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, factor_id: int) -> Factor | None:
        stmt = (
            select(Factor)
            .options(selectinload(Factor.escalas), selectinload(Factor.tipo_factor))
            .where(Factor.id == factor_id)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def list_por_algoritmo(self, algoritmo_id: int) -> list[Factor]:
        stmt = (
            select(Factor)
            .options(selectinload(Factor.escalas), selectinload(Factor.tipo_factor))
            .where(Factor.algoritmo_id == algoritmo_id)
            .order_by(Factor.orden)
        )
        return list(self.db.execute(stmt).scalars().all())

    def create(self, factor: Factor) -> Factor:
        self.db.add(factor)
        self.db.flush()
        return factor

    def delete(self, factor: Factor) -> None:
        self.db.delete(factor)
        self.db.flush()

    def save(self) -> None:
        self.db.flush()


class EscalaRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, escala_id: int) -> Escala | None:
        return self.db.get(Escala, escala_id)

    def list_por_factor(self, factor_id: int) -> list[Escala]:
        stmt = select(Escala).where(Escala.factor_id == factor_id).order_by(Escala.orden)
        return list(self.db.execute(stmt).scalars().all())

    def create(self, escala: Escala) -> Escala:
        self.db.add(escala)
        self.db.flush()
        return escala

    def delete(self, escala: Escala) -> None:
        self.db.delete(escala)
        self.db.flush()

    def save(self) -> None:
        self.db.flush()
