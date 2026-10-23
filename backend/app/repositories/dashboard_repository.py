"""Repositorio de solo-lectura con los agregados que necesita el
dashboard administrativo (sección 15 de los requisitos)."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.aplicacion import Asignacion, Resultado
from app.models.candidato import Candidato
from app.models.catalogos import EstatusPrueba
from app.models.catalogo_prueba import Prueba


class DashboardRepository:
    def __init__(self, db: Session):
        self.db = db

    def total_evaluados(self) -> int:
        return self.db.execute(select(func.count()).select_from(Candidato)).scalar_one()

    def total_pruebas_disponibles(self) -> int:
        stmt = select(func.count()).select_from(Prueba).where(Prueba.activa.is_(True))
        return self.db.execute(stmt).scalar_one()

    def total_resultados(self) -> int:
        return self.db.execute(select(func.count()).select_from(Resultado)).scalar_one()

    def total_asignaciones_por_estatus(self, codigo_estatus: str) -> int:
        stmt = (
            select(func.count())
            .select_from(Asignacion)
            .join(EstatusPrueba, Asignacion.estatus_prueba_id == EstatusPrueba.id)
            .where(EstatusPrueba.codigo == codigo_estatus)
        )
        return self.db.execute(stmt).scalar_one()
