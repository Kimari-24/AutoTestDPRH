"""
Modelos de Candidato (evaluado) y su acceso temporal.

`Candidato` guarda los datos de la persona evaluada. `UsuarioTemporal`
guarda las credenciales efímeras que el administrador genera para que
el candidato pueda entrar al portal (ver sección 8 de los
requisitos: usuario/contraseña temporal, expiración, intentos,
revocación). Se modelan por separado porque un candidato podría, en
el futuro, tener más de un acceso temporal a lo largo del tiempo.
"""

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.aplicacion import Asignacion
    from app.models.catalogos import Escolaridad, EstatusCandidato, Sexo
    from app.models.empresa import Empresa


class Candidato(TimestampMixin, Base):
    __tablename__ = "candidatos"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    apellidos: Mapped[str] = mapped_column(String(150), nullable=False)
    correo: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    puesto: Mapped[str | None] = mapped_column(String(150), nullable=True)
    fecha_nacimiento: Mapped[date | None] = mapped_column(Date, nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    empresa_id: Mapped[int | None] = mapped_column(ForeignKey("empresas.id"), nullable=True)
    sexo_id: Mapped[int | None] = mapped_column(ForeignKey("sexo.id"), nullable=True)
    escolaridad_id: Mapped[int | None] = mapped_column(
        ForeignKey("escolaridad.id"), nullable=True
    )
    estatus_candidato_id: Mapped[int | None] = mapped_column(
        ForeignKey("estatus_candidato.id"), nullable=True
    )

    empresa: Mapped["Empresa | None"] = relationship(back_populates="candidatos")
    sexo: Mapped["Sexo | None"] = relationship()
    escolaridad: Mapped["Escolaridad | None"] = relationship()
    estatus: Mapped["EstatusCandidato | None"] = relationship()

    accesos_temporales: Mapped[list["UsuarioTemporal"]] = relationship(
        back_populates="candidato", cascade="all, delete-orphan"
    )
    asignaciones: Mapped[list["Asignacion"]] = relationship(back_populates="candidato")


class UsuarioTemporal(Base):
    """Credenciales temporales de acceso de un evaluado (portal de evaluados)."""

    __tablename__ = "usuarios_temporales"

    id: Mapped[int] = mapped_column(primary_key=True)
    candidato_id: Mapped[int] = mapped_column(ForeignKey("candidatos.id"), nullable=False)

    usuario: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expira_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    intentos_fallidos: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ultimo_acceso: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    sesion_activa: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    revocado: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    revocado_en: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    candidato: Mapped["Candidato"] = relationship(back_populates="accesos_temporales")
