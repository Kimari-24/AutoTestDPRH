"""
Modelo de Empresa.

Representa a un cliente de DPRH cuyos empleados/candidatos son
evaluados. El rol funcional EMPRESA no está habilitado todavía
(ver README), pero el modelo de datos ya lo contempla: cada
candidato y cada usuario tipo EMPRESA pertenecen a una única
empresa, y el aislamiento entre empresas se hará filtrando por
`empresa_id` en las capas de repositorio/servicio cuando se
implemente ese rol.
"""

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.candidato import Candidato
    from app.models.seguridad import Usuario


class Empresa(TimestampMixin, Base):
    __tablename__ = "empresas"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre_comercial: Mapped[str] = mapped_column(String(200), nullable=False)
    razon_social: Mapped[str | None] = mapped_column(String(200), nullable=True)
    correo_contacto: Mapped[str | None] = mapped_column(String(255), nullable=True)
    telefono_contacto: Mapped[str | None] = mapped_column(String(50), nullable=True)
    direccion: Mapped[str | None] = mapped_column(String(300), nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    candidatos: Mapped[list["Candidato"]] = relationship(back_populates="empresa")
    usuarios: Mapped[list["Usuario"]] = relationship(back_populates="empresa")
