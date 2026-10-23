from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from app.engine.estrategias import ESTRATEGIAS_DISPONIBLES
from app.schemas.base import UpdateSinNulos


def _validar_tipo_calculo(valor: str | None) -> str | None:
    """`tipo_calculo` debe ser una estrategia que el motor realmente
    soporta; antes se aceptaba cualquier texto y el error aparecía hasta
    que un evaluado terminaba su prueba (BUG-12 de QA)."""
    if valor is not None and valor not in ESTRATEGIAS_DISPONIBLES:
        raise ValueError(
            f"tipo_calculo '{valor}' no es una estrategia soportada. "
            f"Disponibles: {', '.join(ESTRATEGIAS_DISPONIBLES)}."
        )
    return valor


def _validar_configuracion_factor(configuracion: dict | None) -> dict | None:
    # Un factor puede sobreescribir la estrategia del algoritmo.
    if configuracion and "tipo_calculo" in configuracion:
        _validar_tipo_calculo(configuracion["tipo_calculo"])
    return configuracion


def _validar_rango(valor_min: float | None, valor_max: float | None) -> None:
    if valor_min is not None and valor_max is not None and valor_min > valor_max:
        raise ValueError("valor_min no puede ser mayor que valor_max.")


class TipoFactorRef(BaseModel):
    id: int
    codigo: str
    nombre: str


class TipoEscalaRef(BaseModel):
    id: int
    codigo: str
    nombre: str


class EscalaCreate(BaseModel):
    tipo_escala_codigo: str | None = None
    codigo: str = Field(min_length=1, max_length=50)
    nombre: str = Field(min_length=1, max_length=150)
    valor_min: float | None = None
    valor_max: float | None = None
    descripcion: str | None = None
    orden: int = 0

    @model_validator(mode="after")
    def _rango_valido(self):
        _validar_rango(self.valor_min, self.valor_max)
        return self


class EscalaUpdate(BaseModel):
    tipo_escala_codigo: str | None = None
    codigo: str | None = Field(default=None, min_length=1, max_length=50)
    nombre: str | None = Field(default=None, min_length=1, max_length=150)
    valor_min: float | None = None
    valor_max: float | None = None
    descripcion: str | None = None
    orden: int | None = None

    @model_validator(mode="after")
    def _rango_valido(self):
        _validar_rango(self.valor_min, self.valor_max)
        return self


class EscalaOut(BaseModel):
    id: int
    factor_id: int
    tipo_escala: TipoEscalaRef | None
    codigo: str
    nombre: str
    valor_min: float | None
    valor_max: float | None
    descripcion: str | None
    orden: int


class FactorCreate(BaseModel):
    tipo_factor_codigo: str | None = None
    codigo: str = Field(min_length=1, max_length=50)
    nombre: str = Field(min_length=1, max_length=150)
    descripcion: str | None = None
    configuracion: dict[str, Any] | None = None
    orden: int = 0

    _valida_config = field_validator("configuracion")(_validar_configuracion_factor)


class FactorUpdate(BaseModel):
    tipo_factor_codigo: str | None = None
    codigo: str | None = Field(default=None, min_length=1, max_length=50)
    nombre: str | None = Field(default=None, min_length=1, max_length=150)
    descripcion: str | None = None
    configuracion: dict[str, Any] | None = None
    orden: int | None = None

    _valida_config = field_validator("configuracion")(_validar_configuracion_factor)


class FactorOut(BaseModel):
    id: int
    algoritmo_id: int
    tipo_factor: TipoFactorRef | None
    codigo: str
    nombre: str
    descripcion: str | None
    configuracion: dict[str, Any] | None
    orden: int
    escalas: list[EscalaOut]


class AlgoritmoCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=150)
    tipo_calculo: str = Field(
        min_length=1,
        max_length=50,
        description=(
            "Estrategia genérica que ejecutará el motor "
            "(p. ej. puntuacion_directa, por_clave, suma, promedio, "
            "ponderacion, percentil, regla_condicional) — no una fórmula "
            "psicométrica concreta."
        ),
    )
    configuracion: dict[str, Any] | None = None

    _valida_tipo = field_validator("tipo_calculo")(_validar_tipo_calculo)


class AlgoritmoUpdate(UpdateSinNulos):
    campos_no_nulos = ("nombre", "tipo_calculo", "activo")

    nombre: str | None = Field(default=None, min_length=1, max_length=150)
    tipo_calculo: str | None = Field(default=None, min_length=1, max_length=50)
    configuracion: dict[str, Any] | None = None
    activo: bool | None = None

    _valida_tipo = field_validator("tipo_calculo")(_validar_tipo_calculo)


class AlgoritmoOut(BaseModel):
    id: int
    prueba_id: int
    nombre: str
    tipo_calculo: str
    configuracion: dict[str, Any] | None
    activo: bool
    factores: list[FactorOut]
