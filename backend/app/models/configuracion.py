"""Configuración general y parámetros ajustables del sistema."""

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.mixins import TimestampMixin


class Configuracion(TimestampMixin, Base):
    """Configuración clave-valor de alcance general (p. ej. nombre de
    la empresa DPRH en reportes, textos institucionales, etc.)."""

    __tablename__ = "configuracion"

    id: Mapped[int] = mapped_column(primary_key=True)
    clave: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    valor: Mapped[str | None] = mapped_column(Text, nullable=True)
    descripcion: Mapped[str | None] = mapped_column(String(255), nullable=True)


class Parametro(TimestampMixin, Base):
    """Parámetros técnicos/operativos ajustables (p. ej. intentos máximos
    de login, minutos de expiración de accesos temporales, etc.)."""

    __tablename__ = "parametros"

    id: Mapped[int] = mapped_column(primary_key=True)
    clave: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    valor: Mapped[str | None] = mapped_column(Text, nullable=True)
    tipo_dato: Mapped[str] = mapped_column(String(20), default="string", nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(255), nullable=True)
