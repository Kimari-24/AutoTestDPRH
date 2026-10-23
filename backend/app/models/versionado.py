"""
Versionado de evaluaciones.

`VersionPrueba` es la versión "viva" que agrupa el conjunto de
preguntas vigente de una prueba (una prueba puede tener varias
versiones a lo largo del tiempo, pero normalmente solo una activa).

`VersionPregunta` y `VersionAlgoritmo` son bitácoras de cambios:
guardan una fotografía (`snapshot`) del contenido anterior cada vez
que se edita una pregunta o un algoritmo, para mantener trazabilidad
sin perder historial.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.catalogo_prueba import Pregunta, Prueba


class VersionPrueba(Base):
    __tablename__ = "version_prueba"

    id: Mapped[int] = mapped_column(primary_key=True)
    prueba_id: Mapped[int] = mapped_column(ForeignKey("pruebas.id"), nullable=False)
    numero_version: Mapped[int] = mapped_column(Integer, nullable=False)
    activa: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notas: Mapped[str | None] = mapped_column(String(500), nullable=True)
    publicada_en: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    prueba: Mapped["Prueba"] = relationship(back_populates="versiones")
    preguntas: Mapped[list["Pregunta"]] = relationship(
        back_populates="version_prueba", cascade="all, delete-orphan"
    )


class VersionPregunta(Base):
    """Snapshot histórico del contenido de una pregunta antes de una edición."""

    __tablename__ = "version_pregunta"

    id: Mapped[int] = mapped_column(primary_key=True)
    pregunta_id: Mapped[int] = mapped_column(ForeignKey("preguntas.id"), nullable=False)
    numero_version: Mapped[int] = mapped_column(Integer, nullable=False)
    contenido: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class VersionAlgoritmo(Base):
    """Snapshot histórico de la configuración de un algoritmo antes de una edición."""

    __tablename__ = "version_algoritmo"

    id: Mapped[int] = mapped_column(primary_key=True)
    algoritmo_id: Mapped[int] = mapped_column(ForeignKey("algoritmos.id"), nullable=False)
    numero_version: Mapped[int] = mapped_column(Integer, nullable=False)
    configuracion: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
