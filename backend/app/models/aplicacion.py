"""
Modelos del flujo de aplicación de una evaluación.

Cubren el ciclo descrito en los requisitos (sección 6):
Asignación -> Sesión de prueba -> Respuestas -> Resultado
(-> Resultado por factor / por escala).
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.candidato import Candidato
    from app.models.catalogo_prueba import Escala, Factor, Opcion, Pregunta, Prueba
    from app.models.catalogos import EstatusPrueba
    from app.models.versionado import VersionPrueba


class Asignacion(Base):
    """Vincula a un candidato con una prueba que debe resolver."""

    __tablename__ = "asignaciones"

    id: Mapped[int] = mapped_column(primary_key=True)
    candidato_id: Mapped[int] = mapped_column(ForeignKey("candidatos.id"), nullable=False)
    prueba_id: Mapped[int] = mapped_column(ForeignKey("pruebas.id"), nullable=False)
    version_prueba_id: Mapped[int | None] = mapped_column(
        ForeignKey("version_prueba.id"), nullable=True
    )
    asignado_por_usuario_id: Mapped[int | None] = mapped_column(
        ForeignKey("usuarios.id"), nullable=True
    )
    estatus_prueba_id: Mapped[int] = mapped_column(
        ForeignKey("estatus_prueba.id"), nullable=False
    )

    fecha_asignacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    fecha_limite: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    candidato: Mapped["Candidato"] = relationship(back_populates="asignaciones")
    prueba: Mapped["Prueba"] = relationship()
    version_prueba: Mapped["VersionPrueba | None"] = relationship()
    estatus: Mapped["EstatusPrueba"] = relationship()
    sesiones: Mapped[list["SesionPrueba"]] = relationship(back_populates="asignacion")


class SesionPrueba(Base):
    """Una sesión concreta en la que el evaluado responde una prueba
    (puede haber más de una si se permiten reintentos)."""

    __tablename__ = "sesiones_prueba"

    id: Mapped[int] = mapped_column(primary_key=True)
    asignacion_id: Mapped[int] = mapped_column(ForeignKey("asignaciones.id"), nullable=False)
    estatus_prueba_id: Mapped[int] = mapped_column(
        ForeignKey("estatus_prueba.id"), nullable=False
    )

    iniciada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finalizada_en: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ultima_actividad_en: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    tiempo_restante_segundos: Mapped[int | None] = mapped_column(Integer, nullable=True)

    asignacion: Mapped["Asignacion"] = relationship(back_populates="sesiones")
    estatus: Mapped["EstatusPrueba"] = relationship()
    respuestas: Mapped[list["Respuesta"]] = relationship(
        back_populates="sesion_prueba", cascade="all, delete-orphan"
    )
    resultado: Mapped["Resultado | None"] = relationship(
        back_populates="sesion_prueba", cascade="all, delete-orphan", uselist=False
    )


class Respuesta(Base):
    """Respuesta del evaluado a una pregunta dentro de una sesión."""

    __tablename__ = "respuestas"

    id: Mapped[int] = mapped_column(primary_key=True)
    sesion_prueba_id: Mapped[int] = mapped_column(
        ForeignKey("sesiones_prueba.id"), nullable=False
    )
    pregunta_id: Mapped[int] = mapped_column(ForeignKey("preguntas.id"), nullable=False)
    opcion_id: Mapped[int | None] = mapped_column(ForeignKey("opciones.id"), nullable=True)

    # Para preguntas de tipo abierto, escala, asociación u ordenamiento,
    # donde la respuesta no es una única opción seleccionable.
    valor: Mapped[str | None] = mapped_column(Text, nullable=True)

    respondida_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    sesion_prueba: Mapped["SesionPrueba"] = relationship(back_populates="respuestas")
    opcion: Mapped["Opcion | None"] = relationship()
    pregunta: Mapped["Pregunta"] = relationship()


class Resultado(Base):
    """Resultado global calculado por el motor para una sesión de prueba."""

    __tablename__ = "resultados"

    id: Mapped[int] = mapped_column(primary_key=True)
    sesion_prueba_id: Mapped[int] = mapped_column(
        ForeignKey("sesiones_prueba.id"), unique=True, nullable=False
    )

    puntuacion_global: Mapped[float | None] = mapped_column(nullable=True)
    puntuacion_normalizada: Mapped[float | None] = mapped_column(nullable=True)
    interpretacion_global: Mapped[str | None] = mapped_column(Text, nullable=True)
    datos_calculo: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    calculado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    sesion_prueba: Mapped["SesionPrueba"] = relationship(back_populates="resultado")
    resultado_factores: Mapped[list["ResultadoFactor"]] = relationship(
        back_populates="resultado", cascade="all, delete-orphan"
    )
    resultado_escalas: Mapped[list["ResultadoEscala"]] = relationship(
        back_populates="resultado", cascade="all, delete-orphan"
    )


class ResultadoFactor(Base):
    """Puntuación obtenida en un factor específico dentro de un resultado."""

    __tablename__ = "resultado_factores"

    id: Mapped[int] = mapped_column(primary_key=True)
    resultado_id: Mapped[int] = mapped_column(ForeignKey("resultados.id"), nullable=False)
    factor_id: Mapped[int] = mapped_column(ForeignKey("factores.id"), nullable=False)

    puntuacion: Mapped[float | None] = mapped_column(nullable=True)
    puntuacion_normalizada: Mapped[float | None] = mapped_column(nullable=True)
    percentil: Mapped[float | None] = mapped_column(nullable=True)
    interpretacion: Mapped[str | None] = mapped_column(Text, nullable=True)

    resultado: Mapped["Resultado"] = relationship(back_populates="resultado_factores")
    factor: Mapped["Factor"] = relationship()


class ResultadoEscala(Base):
    """Ubicación del resultado dentro de una escala de interpretación."""

    __tablename__ = "resultado_escalas"

    id: Mapped[int] = mapped_column(primary_key=True)
    resultado_id: Mapped[int] = mapped_column(ForeignKey("resultados.id"), nullable=False)
    escala_id: Mapped[int] = mapped_column(ForeignKey("escalas.id"), nullable=False)

    valor: Mapped[float | None] = mapped_column(nullable=True)
    interpretacion: Mapped[str | None] = mapped_column(Text, nullable=True)

    resultado: Mapped["Resultado"] = relationship(back_populates="resultado_escalas")
    escala: Mapped["Escala"] = relationship()
