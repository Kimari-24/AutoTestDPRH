"""
Catálogos auxiliares.

Son tablas de valores controlados (listas desplegables) en lugar de
enums de Python, para que el administrador pueda ampliarlas desde el
sistema sin requerir un despliegue de código (por ejemplo, agregar un
nuevo nivel de escolaridad o un nuevo tipo de pregunta).
"""

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class CatalogoBase(Base):
    """Base abstracta común a todos los catálogos simples."""

    __abstract__ = True

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(255), nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Sexo(CatalogoBase):
    __tablename__ = "sexo"


class Escolaridad(CatalogoBase):
    __tablename__ = "escolaridad"


class EstatusCandidato(CatalogoBase):
    __tablename__ = "estatus_candidato"


class EstatusPrueba(CatalogoBase):
    """Estados del ciclo de vida de una evaluación aplicada.

    Valores esperados (cargados como datos semilla, no fijos en
    código): PENDIENTE, EN_PROCESO, COMPLETADA, CALIFICADA,
    CANCELADA, EXPIRADA.
    """

    __tablename__ = "estatus_prueba"


class TipoPregunta(CatalogoBase):
    """Tipos de pregunta soportados por el motor (opción única,
    opción múltiple, verdadero/falso, escala, asociación,
    ordenamiento, con imagen, basada en texto, estímulo visual).
    """

    __tablename__ = "tipo_pregunta"


class TipoFactor(CatalogoBase):
    __tablename__ = "tipo_factor"


class TipoEscala(CatalogoBase):
    __tablename__ = "tipo_escala"
