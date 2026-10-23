"""
Estrategias de cálculo del motor universal de evaluaciones.

Cada función implementa una ESTRATEGIA GENÉRICA de las enumeradas en
la sección 19 de los requisitos (puntuación directa, por clave,
sumas, promedios, ponderaciones, percentiles, reglas condicionales).

IMPORTANTE: ninguna de estas funciones contiene fórmulas, claves ni
baremos psicométricos reales. Todo el contenido concreto (qué opción
es la "correcta", qué peso tiene cada pregunta, en qué rango cae cada
percentil) se recibe como parámetro (`configuracion`), como datos que
DPRH aporta a través del catálogo de la Fase 5 — nunca hardcodeado
aquí.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.core.exceptions.base import ValidationError


@dataclass
class RespuestaCalculable:
    """Vista simplificada de una respuesta, lista para que una
    estrategia la use, independientemente de si vino de una opción
    seleccionada o de un valor libre."""

    pregunta_id: int
    valor_numerico: float | None
    valor_texto: str | None
    configuracion_pregunta: dict[str, Any]


ESTRATEGIAS_DISPONIBLES = (
    "puntuacion_directa",
    "suma",
    "promedio",
    "ponderacion",
    "por_clave",
    "percentil",
    "regla_condicional",
)


def _valores_numericos(respuestas: list[RespuestaCalculable]) -> list[float]:
    return [r.valor_numerico for r in respuestas if r.valor_numerico is not None]


def calcular_puntuacion_directa(respuestas: list[RespuestaCalculable], configuracion: dict) -> float:
    """Suma directa de los valores numéricos de las respuestas."""
    return sum(_valores_numericos(respuestas))


def calcular_promedio(respuestas: list[RespuestaCalculable], configuracion: dict) -> float:
    """Promedio de los valores numéricos de las respuestas."""
    valores = _valores_numericos(respuestas)
    return sum(valores) / len(valores) if valores else 0.0


def calcular_ponderacion(respuestas: list[RespuestaCalculable], configuracion: dict) -> float:
    """Suma ponderada: cada pregunta aporta su valor × su peso.

    El peso de cada pregunta se toma de
    `pregunta.configuracion["peso"]` (por defecto 1.0) — un dato de
    configuración, no una fórmula fija.
    """
    total = 0.0
    for r in respuestas:
        if r.valor_numerico is None:
            continue
        peso = float(r.configuracion_pregunta.get("peso", 1.0))
        total += r.valor_numerico * peso
    return total


def _coincide_con_clave(r: RespuestaCalculable, clave: Any) -> bool:
    """Compara la respuesta contra la clave configurada.

    Si la respuesta es numérica, la comparación es NUMÉRICA: el motor
    convierte el valor de la opción "1" a 1.0, y comparar `str(1.0)`
    ("1.0") contra la clave "1" nunca coincidía (BUG-01 de QA). Si la
    respuesta es texto, se compara como texto (p. ej. claves "A"/"B").
    """
    if r.valor_numerico is not None:
        try:
            return float(r.valor_numerico) == float(clave)
        except (TypeError, ValueError):
            return False
    if r.valor_texto is not None:
        return r.valor_texto.strip() == str(clave).strip()
    return False


def calcular_por_clave(respuestas: list[RespuestaCalculable], configuracion: dict) -> float:
    """Puntuación por clave: compara la respuesta contra la clave
    configurada en la propia pregunta (`pregunta.configuracion["clave"]`)
    y suma los puntos de esa pregunta si coincide.

    La clave y los puntos por pregunta son datos de configuración
    aportados por DPRH, no una clave real embebida en el motor.
    """
    total = 0.0
    for r in respuestas:
        clave = r.configuracion_pregunta.get("clave")
        if clave is None:
            continue
        puntos = float(r.configuracion_pregunta.get("puntos", 1.0))
        if _coincide_con_clave(r, clave):
            total += puntos
    return total


def _buscar_en_tabla_de_rangos(
    valor: float, tabla: list[dict[str, Any]], campo_resultado: str
) -> Any | None:
    """Busca en una tabla de rangos genérica (lista de
    {"min":.., "max":.., campo_resultado: ..}) el primer rango que
    contiene `valor`. La tabla es un dato de configuración, no una
    tabla de baremos embebida."""
    for fila in tabla:
        minimo = fila.get("min")
        maximo = fila.get("max")
        dentro_min = minimo is None or valor >= minimo
        dentro_max = maximo is None or valor <= maximo
        if dentro_min and dentro_max:
            return fila.get(campo_resultado)
    return None


def calcular_percentil(respuestas: list[RespuestaCalculable], configuracion: dict) -> float:
    """Calcula una puntuación bruta (suma) y la transforma a percentil
    usando `factor.configuracion["tabla_percentiles"]`, una lista de
    rangos {"min":.., "max":.., "percentil":..} aportada por DPRH.

    Si no hay tabla configurada, devuelve la puntuación bruta tal
    cual (no se inventa una curva de percentiles).
    """
    puntuacion_bruta = calcular_puntuacion_directa(respuestas, configuracion)
    tabla = configuracion.get("tabla_percentiles")
    if not tabla:
        return puntuacion_bruta
    percentil = _buscar_en_tabla_de_rangos(puntuacion_bruta, tabla, "percentil")
    return float(percentil) if percentil is not None else puntuacion_bruta


def calcular_regla_condicional(
    respuestas: list[RespuestaCalculable], configuracion: dict
) -> tuple[float, str | None]:
    """Calcula una puntuación bruta y la clasifica según
    `factor.configuracion["reglas"]`, una lista de rangos
    {"min":.., "max":.., "interpretacion":..} aportada por DPRH.

    Devuelve (puntuacion, interpretacion). No aplica ninguna regla
    psicométrica propia: solo evalúa rangos numéricos de configuración.
    """
    puntuacion_bruta = calcular_puntuacion_directa(respuestas, configuracion)
    reglas = configuracion.get("reglas")
    if not reglas:
        return puntuacion_bruta, None
    interpretacion = _buscar_en_tabla_de_rangos(puntuacion_bruta, reglas, "interpretacion")
    return puntuacion_bruta, interpretacion


def ejecutar_estrategia(
    tipo_calculo: str, respuestas: list[RespuestaCalculable], configuracion: dict | None
) -> tuple[float, str | None]:
    """Punto de entrada único: despacha a la estrategia indicada por
    `tipo_calculo` y siempre devuelve (puntuacion, interpretacion),
    dejando `interpretacion` en None para las estrategias que no
    clasifican en rangos."""
    configuracion = configuracion or {}

    if tipo_calculo in ("puntuacion_directa", "suma"):
        return calcular_puntuacion_directa(respuestas, configuracion), None
    if tipo_calculo == "promedio":
        return calcular_promedio(respuestas, configuracion), None
    if tipo_calculo == "ponderacion":
        return calcular_ponderacion(respuestas, configuracion), None
    if tipo_calculo == "por_clave":
        return calcular_por_clave(respuestas, configuracion), None
    if tipo_calculo == "percentil":
        return calcular_percentil(respuestas, configuracion), None
    if tipo_calculo == "regla_condicional":
        return calcular_regla_condicional(respuestas, configuracion)

    raise ValidationError(
        f"tipo_calculo '{tipo_calculo}' no es una estrategia soportada por el motor. "
        f"Estrategias disponibles: {', '.join(ESTRATEGIAS_DISPONIBLES)}."
    )
