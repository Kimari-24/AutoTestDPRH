"""
Endpoints de resultados: invocan al motor universal de evaluaciones
(app/engine/) sobre una sesión de prueba ya completada, y permiten
consultar el resultado calculado.

La creación de sesiones y respuestas (el portal del evaluado) se
construye en la Fase 7; este módulo opera sobre sesiones que ya
existan con estatus COMPLETADA.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies.auth import require_roles
from app.db.session import get_db
from app.engine.motor import MotorEvaluacion
from app.models.aplicacion import Resultado
from app.schemas.resultado import (
    CalcularResultadoRequest,
    ResultadoEscalaOut,
    ResultadoFactorOut,
    ResultadoOut,
)

router = APIRouter(
    prefix="/resultados",
    tags=["Resultados"],
    dependencies=[Depends(require_roles("ADMINISTRADOR"))],
)


def _resultado_out(resultado: Resultado) -> ResultadoOut:
    return ResultadoOut(
        id=resultado.id,
        sesion_prueba_id=resultado.sesion_prueba_id,
        puntuacion_global=resultado.puntuacion_global,
        puntuacion_normalizada=resultado.puntuacion_normalizada,
        interpretacion_global=resultado.interpretacion_global,
        calculado_en=resultado.calculado_en,
        factores=[
            ResultadoFactorOut(
                factor_id=rf.factor_id,
                factor_codigo=rf.factor.codigo,
                factor_nombre=rf.factor.nombre,
                puntuacion=rf.puntuacion,
                interpretacion=rf.interpretacion,
            )
            for rf in resultado.resultado_factores
        ],
        escalas=[
            ResultadoEscalaOut(
                escala_id=re.escala_id,
                escala_codigo=re.escala.codigo,
                escala_nombre=re.escala.nombre,
                valor=re.valor,
                interpretacion=re.interpretacion,
            )
            for re in resultado.resultado_escalas
        ],
    )


@router.post("/sesiones/{sesion_prueba_id}/calcular", response_model=ResultadoOut, status_code=201)
def calcular_resultado(
    sesion_prueba_id: int,
    data: CalcularResultadoRequest,
    db: Session = Depends(get_db),
):
    """Ejecuta el motor universal sobre una sesión COMPLETADA y guarda su resultado."""
    motor = MotorEvaluacion(db)
    resultado = motor.calcular(sesion_prueba_id, forzar_recalculo=data.forzar_recalculo)
    return _resultado_out(resultado)


@router.get("/sesiones/{sesion_prueba_id}", response_model=ResultadoOut)
def obtener_resultado(sesion_prueba_id: int, db: Session = Depends(get_db)):
    """Consulta el resultado ya calculado de una sesión."""
    motor = MotorEvaluacion(db)
    resultado = motor.obtener_resultado(sesion_prueba_id)
    return _resultado_out(resultado)
