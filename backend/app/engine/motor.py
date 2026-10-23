"""
Motor universal de evaluaciones psicométricas.

Implementa el pipeline descrito en la sección 4 de los requisitos:

    RESPUESTAS -> ALGORITMO -> FACTORES -> ESCALAS -> RESULTADO

Este motor es el ÚNICO componente de cálculo del sistema: no existe
un motor por evaluación (nada de `TermanEngine`, `WonderlicEngine`,
etc.). Cualquier prueba se procesa igual, siguiendo la configuración
que trae su `Algoritmo` (Fase 5) — el motor nunca contiene claves,
baremos ni fórmulas psicométricas reales.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone

from sqlalchemy.orm import Session, selectinload

from app.core.exceptions.base import ConflictError, NotFoundError, ValidationError
from app.engine.estrategias import RespuestaCalculable, ejecutar_estrategia
from app.models.aplicacion import (
    Asignacion,
    Resultado,
    ResultadoEscala,
    ResultadoFactor,
    Respuesta,
    SesionPrueba,
)
from app.models.catalogo_prueba import Algoritmo, Escala, Factor
from app.models.catalogos import EstatusPrueba


class MotorEvaluacion:
    """Calcula (o recalcula) el resultado de una sesión de prueba ya
    completada, siguiendo el algoritmo configurado para esa prueba."""

    def __init__(self, db: Session):
        self.db = db

    # -- carga de datos -----------------------------------------------

    def _cargar_sesion(self, sesion_prueba_id: int) -> SesionPrueba:
        stmt = (
            self.db.query(SesionPrueba)
            .options(
                selectinload(SesionPrueba.respuestas).selectinload(Respuesta.opcion),
                selectinload(SesionPrueba.respuestas).selectinload(Respuesta.pregunta),
                selectinload(SesionPrueba.asignacion).selectinload(Asignacion.prueba),
                selectinload(SesionPrueba.estatus),
            )
            .filter(SesionPrueba.id == sesion_prueba_id)
        )
        sesion = stmt.first()
        if sesion is None:
            raise NotFoundError("Sesión de prueba no encontrada.")
        return sesion

    def _obtener_algoritmo_activo(self, prueba_id: int) -> Algoritmo:
        algoritmo = (
            self.db.query(Algoritmo)
            .options(selectinload(Algoritmo.factores).selectinload(Factor.escalas))
            .filter(Algoritmo.prueba_id == prueba_id, Algoritmo.activo.is_(True))
            .first()
        )
        if algoritmo is None:
            raise ValidationError(
                "Esta evaluación no tiene un algoritmo activo configurado; "
                "no se puede calcular un resultado todavía."
            )
        return algoritmo

    def _estatus_por_codigo(self, codigo: str) -> EstatusPrueba:
        estatus = self.db.query(EstatusPrueba).filter(EstatusPrueba.codigo == codigo).first()
        if estatus is None:
            raise ValidationError(
                f"El catálogo estatus_prueba no tiene el código '{codigo}'. "
                "Ejecuta scripts/seed_catalogos.py."
            )
        return estatus

    # -- preparación de respuestas --------------------------------------

    def _respuestas_a_calculables(
        self, respuestas: list[Respuesta], factor_codigo: str
    ) -> list[RespuestaCalculable]:
        resultado: list[RespuestaCalculable] = []
        for r in respuestas:
            config_pregunta = r.pregunta.configuracion if r.pregunta else None
            config_pregunta = config_pregunta or {}
            if config_pregunta.get("factor_codigo") != factor_codigo:
                continue

            valor_numerico: float | None = None
            valor_texto: str | None = None
            crudo = r.opcion.valor if r.opcion is not None else r.valor
            if crudo is not None:
                try:
                    valor_numerico = float(crudo)
                    if not math.isfinite(valor_numerico):
                        # "nan"/"inf" se parsean como float, pero no son
                        # puntajes válidos: se tratan como texto.
                        valor_numerico = None
                        valor_texto = str(crudo)
                except (TypeError, ValueError):
                    valor_texto = str(crudo)
            resultado.append(
                RespuestaCalculable(
                    pregunta_id=r.pregunta_id,
                    valor_numerico=valor_numerico,
                    valor_texto=valor_texto,
                    configuracion_pregunta=config_pregunta,
                )
            )
        return resultado

    def _interpretar_con_escalas(self, factor: Factor, puntuacion: float) -> tuple[Escala | None, str | None]:
        for escala in factor.escalas:
            dentro_min = escala.valor_min is None or puntuacion >= escala.valor_min
            dentro_max = escala.valor_max is None or puntuacion <= escala.valor_max
            if dentro_min and dentro_max:
                return escala, escala.descripcion
        return None, None

    # -- orquestación principal -----------------------------------------

    def calcular(self, sesion_prueba_id: int, forzar_recalculo: bool = False) -> Resultado:
        """Calcula el resultado de una sesión. Requiere que la sesión
        esté en estatus COMPLETADA (o ya CALIFICADA, si se pide
        recalcular). Al terminar, dej a la sesión en CALIFICADA."""
        sesion = self._cargar_sesion(sesion_prueba_id)

        codigo_estatus_actual = sesion.estatus.codigo if sesion.estatus else None
        if codigo_estatus_actual not in ("COMPLETADA", "CALIFICADA"):
            raise ConflictError(
                "Solo se puede calcular el resultado de una sesión COMPLETADA "
                f"(estatus actual: {codigo_estatus_actual})."
            )
        if codigo_estatus_actual == "CALIFICADA" and not forzar_recalculo:
            raise ConflictError(
                "Esta sesión ya fue calificada. Usa forzar_recalculo=True para recalcular."
            )

        prueba = sesion.asignacion.prueba
        algoritmo = self._obtener_algoritmo_activo(prueba.id)

        # Si ya existe un resultado (recalculo), se reemplaza por completo.
        resultado_existente = (
            self.db.query(Resultado)
            .filter(Resultado.sesion_prueba_id == sesion.id)
            .first()
        )
        if resultado_existente is not None:
            self.db.delete(resultado_existente)
            self.db.flush()

        resultado = Resultado(
            sesion_prueba_id=sesion.id,
            calculado_en=datetime.now(timezone.utc),
            datos_calculo={"tipo_calculo_algoritmo": algoritmo.tipo_calculo},
        )

        puntuaciones_por_factor: list[float] = []

        for factor in sorted(algoritmo.factores, key=lambda f: f.orden):
            configuracion_factor = factor.configuracion or {}
            tipo_calculo = configuracion_factor.get("tipo_calculo", algoritmo.tipo_calculo)

            respuestas_calculables = self._respuestas_a_calculables(
                sesion.respuestas, factor.codigo
            )
            puntuacion, interpretacion_regla = ejecutar_estrategia(
                tipo_calculo, respuestas_calculables, configuracion_factor
            )
            puntuaciones_por_factor.append(puntuacion)

            escala, interpretacion_escala = self._interpretar_con_escalas(factor, puntuacion)
            interpretacion = interpretacion_escala or interpretacion_regla

            resultado_factor = ResultadoFactor(
                factor_id=factor.id,
                puntuacion=puntuacion,
                interpretacion=interpretacion,
            )
            resultado.resultado_factores.append(resultado_factor)

            if escala is not None:
                resultado.resultado_escalas.append(
                    ResultadoEscala(
                        escala_id=escala.id,
                        valor=puntuacion,
                        interpretacion=interpretacion,
                    )
                )

        resultado.puntuacion_global = (
            sum(puntuaciones_por_factor) if puntuaciones_por_factor else None
        )

        self.db.add(resultado)

        sesion.estatus_prueba_id = self._estatus_por_codigo("CALIFICADA").id
        if sesion.asignacion is not None:
            sesion.asignacion.estatus_prueba_id = self._estatus_por_codigo("CALIFICADA").id

        self.db.commit()
        self.db.refresh(resultado)
        return resultado

    def obtener_resultado(self, sesion_prueba_id: int) -> Resultado:
        resultado = (
            self.db.query(Resultado)
            .options(
                selectinload(Resultado.resultado_factores).selectinload(ResultadoFactor.factor),
                selectinload(Resultado.resultado_escalas).selectinload(ResultadoEscala.escala),
            )
            .filter(Resultado.sesion_prueba_id == sesion_prueba_id)
            .first()
        )
        if resultado is None:
            raise NotFoundError("Todavía no hay un resultado calculado para esta sesión.")
        return resultado
