from datetime import datetime

from pydantic import BaseModel


class ResultadoFactorOut(BaseModel):
    factor_id: int
    factor_codigo: str
    factor_nombre: str
    puntuacion: float | None
    interpretacion: str | None


class ResultadoEscalaOut(BaseModel):
    escala_id: int
    escala_codigo: str
    escala_nombre: str
    valor: float | None
    interpretacion: str | None


class ResultadoOut(BaseModel):
    id: int
    sesion_prueba_id: int
    puntuacion_global: float | None
    puntuacion_normalizada: float | None
    interpretacion_global: str | None
    calculado_en: datetime
    factores: list[ResultadoFactorOut]
    escalas: list[ResultadoEscalaOut]


class CalcularResultadoRequest(BaseModel):
    forzar_recalculo: bool = False
