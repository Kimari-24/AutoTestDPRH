"""Repositorio de acceso a datos para `Empresa`."""

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.empresa import Empresa


class EmpresaRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, empresa_id: int) -> Empresa | None:
        return self.db.get(Empresa, empresa_id)

    def list(
        self,
        skip: int = 0,
        limit: int = 50,
        buscar: str | None = None,
        solo_activas: bool = False,
    ) -> list[Empresa]:
        stmt = select(Empresa)
        if buscar:
            patron = f"%{buscar.lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(Empresa.nombre_comercial).like(patron),
                    func.lower(Empresa.razon_social).like(patron),
                )
            )
        if solo_activas:
            stmt = stmt.where(Empresa.activo.is_(True))
        stmt = stmt.order_by(Empresa.nombre_comercial).offset(skip).limit(limit)
        return list(self.db.execute(stmt).scalars().all())

    def count(self, solo_activas: bool = False) -> int:
        stmt = select(func.count()).select_from(Empresa)
        if solo_activas:
            stmt = stmt.where(Empresa.activo.is_(True))
        return self.db.execute(stmt).scalar_one()

    def create(self, empresa: Empresa) -> Empresa:
        self.db.add(empresa)
        self.db.flush()
        return empresa

    def save(self) -> None:
        self.db.flush()
