"""
Repositorio genérico para las tablas de catálogo (sexo, escolaridad,
estatus_candidato, estatus_prueba, tipo_pregunta, tipo_factor,
tipo_escala).

Todas comparten la misma forma (id, codigo, nombre, descripcion,
activo), así que se resuelve con una sola clase parametrizada por el
modelo concreto, en vez de repetir el mismo código siete veces.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.catalogos import CatalogoBase


class CatalogoRepository:
    def __init__(self, db: Session, modelo: type[CatalogoBase]):
        self.db = db
        self.modelo = modelo

    def get_by_id(self, catalogo_id: int) -> CatalogoBase | None:
        return self.db.get(self.modelo, catalogo_id)

    def get_by_codigo(self, codigo: str) -> CatalogoBase | None:
        stmt = select(self.modelo).where(self.modelo.codigo == codigo)
        return self.db.execute(stmt).scalar_one_or_none()

    def list(self, solo_activos: bool = True) -> list[CatalogoBase]:
        stmt = select(self.modelo)
        if solo_activos:
            stmt = stmt.where(self.modelo.activo.is_(True))
        stmt = stmt.order_by(self.modelo.nombre)
        return list(self.db.execute(stmt).scalars().all())
