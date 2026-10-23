"""
Portal del evaluado (Fase 7).

Completamente separado del panel administrativo: usa su propio
esquema de autenticación (`UsuarioTemporal`, no `Usuario`+roles) y
solo expone lo que un evaluado puede ver según la sección 2 de los
requisitos — nunca preguntas de otras versiones, claves de
calificación, ni datos de otros evaluados.
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.dependencies.evaluado_auth import get_evaluado_actual
from app.core.security.rate_limit import limitar_tasa
from app.db.session import get_db
from app.models.candidato import UsuarioTemporal
from app.schemas.portal import (
    GuardarRespuestaRequest,
    IniciarSesionOut,
    LoginEvaluadoRequest,
    MiEvaluacionOut,
    PreguntaPortalOut,
    ProgresoSesionOut,
    TokenEvaluadoResponse,
)
from app.services.acceso_temporal_service import AccesoTemporalService
from app.services.portal_evaluado_service import PortalEvaluadoService

router = APIRouter(prefix="/portal", tags=["Portal del evaluado"])

_limite_login_evaluado = limitar_tasa("portal_login", maximo=10, ventana_segundos=60)


@router.post("/login", response_model=TokenEvaluadoResponse, dependencies=[Depends(_limite_login_evaluado)])
def login(data: LoginEvaluadoRequest, request: Request, db: Session = Depends(get_db)):
    """Autentica a un evaluado con sus credenciales temporales."""
    service = AccesoTemporalService(db)
    return service.login(
        usuario=data.usuario,
        password=data.password,
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.post("/logout", status_code=204)
def logout(
    db: Session = Depends(get_db),
    evaluado: UsuarioTemporal = Depends(get_evaluado_actual),
):
    """Cierra la sesión del evaluado (marca el acceso temporal como sin sesión activa)."""
    AccesoTemporalService(db).logout(evaluado.id)


@router.get("/mis-evaluaciones", response_model=list[MiEvaluacionOut])
def mis_evaluaciones(
    db: Session = Depends(get_db),
    evaluado: UsuarioTemporal = Depends(get_evaluado_actual),
):
    """Lista únicamente las evaluaciones asignadas al evaluado autenticado."""
    service = PortalEvaluadoService(db)
    return service.listar_mis_evaluaciones(evaluado.candidato_id)


@router.post("/evaluaciones/{asignacion_id}/iniciar", response_model=IniciarSesionOut)
def iniciar_evaluacion(
    asignacion_id: int,
    db: Session = Depends(get_db),
    evaluado: UsuarioTemporal = Depends(get_evaluado_actual),
):
    """Inicia una evaluación pendiente, o retoma la sesión en proceso si ya existía."""
    service = PortalEvaluadoService(db)
    return service.iniciar_o_continuar(evaluado.candidato_id, asignacion_id)


@router.get("/sesiones/{sesion_id}/preguntas", response_model=list[PreguntaPortalOut])
def obtener_preguntas(
    sesion_id: int,
    db: Session = Depends(get_db),
    evaluado: UsuarioTemporal = Depends(get_evaluado_actual),
):
    """Preguntas de la sesión, sin exponer configuración de calificación."""
    service = PortalEvaluadoService(db)
    return service.obtener_preguntas(evaluado.candidato_id, sesion_id)


@router.put("/sesiones/{sesion_id}/preguntas/{pregunta_id}/respuesta", status_code=204)
def guardar_respuesta(
    sesion_id: int,
    pregunta_id: int,
    data: GuardarRespuestaRequest,
    db: Session = Depends(get_db),
    evaluado: UsuarioTemporal = Depends(get_evaluado_actual),
):
    """Guarda (o actualiza) la respuesta a una pregunta — autoguardado."""
    service = PortalEvaluadoService(db)
    service.guardar_respuesta(evaluado.candidato_id, sesion_id, pregunta_id, data)


@router.get("/sesiones/{sesion_id}/progreso", response_model=ProgresoSesionOut)
def obtener_progreso(
    sesion_id: int,
    db: Session = Depends(get_db),
    evaluado: UsuarioTemporal = Depends(get_evaluado_actual),
):
    """Progreso actual (preguntas respondidas, tiempo restante)."""
    service = PortalEvaluadoService(db)
    return service.obtener_progreso(evaluado.candidato_id, sesion_id)


@router.post("/sesiones/{sesion_id}/finalizar", response_model=ProgresoSesionOut)
def finalizar_evaluacion(
    sesion_id: int,
    db: Session = Depends(get_db),
    evaluado: UsuarioTemporal = Depends(get_evaluado_actual),
):
    """Finaliza la sesión; el motor intenta calificarla automáticamente."""
    service = PortalEvaluadoService(db)
    return service.finalizar(evaluado.candidato_id, sesion_id)
