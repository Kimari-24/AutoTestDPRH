"""
Catálogo de pruebas psicométricas y el modelo de datos del motor
universal de evaluación.

Sigue el flujo conceptual de los requisitos:

    CATEGORIA_PRUEBA -> PRUEBA -> VERSION_PRUEBA -> PREGUNTAS -> OPCIONES
    PRUEBA -> ALGORITMO -> FACTORES -> ESCALAS

Ninguna de estas tablas contiene contenido psicométrico real
(preguntas, claves, baremos o fórmulas de una prueba concreta como
Terman o Cleaver): son la estructura genérica que el motor universal
(Fase 6) usará para ejecutar cualquier evaluación configurada con
datos. Los datos reales los carga el administrador o se importan de
documentación autorizada.
"""

from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.catalogos import TipoEscala, TipoFactor, TipoPregunta
    from app.models.versionado import VersionPrueba


class CategoriaPrueba(Base):
    """Agrupación de pruebas: INTELIGENCIA/RAZONAMIENTO, PERSONALIDAD,
    HABILIDADES/OTROS (los valores concretos se cargan como datos, no
    se fijan en código)."""

    __tablename__ = "categorias_prueba"

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(255), nullable=True)
    orden: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    pruebas: Mapped[list["Prueba"]] = relationship(back_populates="categoria")


class Prueba(TimestampMixin, Base):
    """Una evaluación psicométrica (p. ej. Terman, Cleaver, 16 FP).

    El nombre y demás metadatos son configuración; el contenido
    (preguntas/opciones) vive en `VersionPrueba` para poder mantener
    varias versiones de la misma prueba en el tiempo.
    """

    __tablename__ = "pruebas"

    id: Mapped[int] = mapped_column(primary_key=True)
    categoria_id: Mapped[int] = mapped_column(
        ForeignKey("categorias_prueba.id"), nullable=False
    )
    codigo: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    instrucciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    tiempo_limite_minutos: Mapped[int | None] = mapped_column(Integer, nullable=True)
    intentos_permitidos: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    activa: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    categoria: Mapped["CategoriaPrueba"] = relationship(back_populates="pruebas")
    versiones: Mapped[list["VersionPrueba"]] = relationship(back_populates="prueba")
    algoritmos: Mapped[list["Algoritmo"]] = relationship(back_populates="prueba")


class Algoritmo(TimestampMixin, Base):
    """Configuración de cálculo de una prueba.

    `tipo_calculo` identifica la ESTRATEGIA genérica que el motor debe
    ejecutar (p. ej. "puntuacion_directa", "por_clave", "suma",
    "promedio", "ponderacion", "percentil", "regla_condicional") — no
    la fórmula psicométrica en sí. Los coeficientes/reglas concretos
    se guardan en `configuracion` como datos aportados por DPRH.
    """

    __tablename__ = "algoritmos"

    id: Mapped[int] = mapped_column(primary_key=True)
    prueba_id: Mapped[int] = mapped_column(ForeignKey("pruebas.id"), nullable=False)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    tipo_calculo: Mapped[str] = mapped_column(String(50), nullable=False)
    configuracion: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    prueba: Mapped["Prueba"] = relationship(back_populates="algoritmos")
    factores: Mapped[list["Factor"]] = relationship(
        back_populates="algoritmo", cascade="all, delete-orphan"
    )


class Factor(Base):
    """Factor/dimensión que calcula un algoritmo (p. ej. un rasgo de
    personalidad o una sub-habilidad). El contenido real lo define
    DPRH; aquí solo se modela la estructura."""

    __tablename__ = "factores"

    id: Mapped[int] = mapped_column(primary_key=True)
    algoritmo_id: Mapped[int] = mapped_column(ForeignKey("algoritmos.id"), nullable=False)
    tipo_factor_id: Mapped[int | None] = mapped_column(
        ForeignKey("tipo_factor.id"), nullable=True
    )
    codigo: Mapped[str] = mapped_column(String(50), nullable=False)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    configuracion: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    orden: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    algoritmo: Mapped["Algoritmo"] = relationship(back_populates="factores")
    tipo_factor: Mapped["TipoFactor | None"] = relationship()
    escalas: Mapped[list["Escala"]] = relationship(
        back_populates="factor", cascade="all, delete-orphan"
    )


class Escala(Base):
    """Escala de interpretación de un factor (p. ej. rangos, percentiles).

    Igual que en `Algoritmo`/`Factor`: la estructura es genérica, los
    valores reales (baremos) los aporta DPRH en `configuracion`.
    """

    __tablename__ = "escalas"

    id: Mapped[int] = mapped_column(primary_key=True)
    factor_id: Mapped[int] = mapped_column(ForeignKey("factores.id"), nullable=False)
    tipo_escala_id: Mapped[int | None] = mapped_column(
        ForeignKey("tipo_escala.id"), nullable=True
    )
    codigo: Mapped[str] = mapped_column(String(50), nullable=False)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    valor_min: Mapped[float | None] = mapped_column(nullable=True)
    valor_max: Mapped[float | None] = mapped_column(nullable=True)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    orden: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    factor: Mapped["Factor"] = relationship(back_populates="escalas")
    tipo_escala: Mapped["TipoEscala | None"] = relationship()


class Pregunta(Base):
    """Pregunta perteneciente a una versión concreta de una prueba."""

    __tablename__ = "preguntas"

    id: Mapped[int] = mapped_column(primary_key=True)
    version_prueba_id: Mapped[int] = mapped_column(
        ForeignKey("version_prueba.id"), nullable=False
    )
    tipo_pregunta_id: Mapped[int] = mapped_column(
        ForeignKey("tipo_pregunta.id"), nullable=False
    )
    enunciado: Mapped[str] = mapped_column(Text, nullable=False)
    imagen_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    configuracion: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    orden: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    activa: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    version_prueba: Mapped["VersionPrueba"] = relationship(back_populates="preguntas")
    tipo_pregunta: Mapped["TipoPregunta"] = relationship()
    opciones: Mapped[list["Opcion"]] = relationship(
        back_populates="pregunta", cascade="all, delete-orphan"
    )


class Opcion(Base):
    """Opción de respuesta de una pregunta."""

    __tablename__ = "opciones"

    id: Mapped[int] = mapped_column(primary_key=True)
    pregunta_id: Mapped[int] = mapped_column(ForeignKey("preguntas.id"), nullable=False)
    texto: Mapped[str | None] = mapped_column(Text, nullable=True)
    imagen_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    valor: Mapped[str | None] = mapped_column(String(100), nullable=True)
    orden: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    pregunta: Mapped["Pregunta"] = relationship(back_populates="opciones")
