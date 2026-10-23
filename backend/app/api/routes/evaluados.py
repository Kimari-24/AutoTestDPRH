"""
Endpoints de administración de evaluados (candidatos).

Este módulo cubre las capacidades del ADMINISTRADOR (listar, buscar,
filtrar, crear, editar, desactivar, ver expediente). La creación de
accesos temporales y la asignación de evaluaciones se agregan en
fases posteriores, cuando existan pruebas cargadas.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_usuario, require_roles
from app.db.session import get_db
from app.models.candidato import Candidato
from app.models.seguridad import Usuario
from app.schemas.acceso_temporal import (
    AccesoTemporalCreadoOut,
    AccesoTemporalOut,
    AsignacionOut,
    AsignarEvaluacionRequest,
    CrearAccesoTemporalRequest,
)
from app.schemas.candidato import (
    CandidatoCreate,
    CandidatoOut,
    CandidatoUpdate,
    CatalogoRef,
    EmpresaRef,
    ExpedienteCandidatoOut,
)
from app.services.acceso_temporal_service import AccesoTemporalService
from app.services.asignacion_service import AsignacionService
from app.services.candidato_service import CandidatoService

router = APIRouter(
    prefix="/evaluados",
    tags=["Evaluados"],
    dependencies=[Depends(require_roles("ADMINISTRADOR"))],
)


def _catalogo_ref(item) -> CatalogoRef | None:
    if item is None:
        return None
    return CatalogoRef(id=item.id, codigo=item.codigo, nombre=item.nombre)


def _to_out(candidato: Candidato) -> CandidatoOut:
    return CandidatoOut(
        id=candidato.id,
        nombre=candidato.nombre,
        apellidos=candidato.apellidos,
        correo=candidato.correo,
        puesto=candidato.puesto,
        fecha_nacimiento=candidato.fecha_nacimiento,
        activo=candidato.activo,
        creado_en=candidato.creado_en,
        empresa=(
            EmpresaRef(id=candidato.empresa.id, nombre_comercial=candidato.empresa.nombre_comercial)
            if candidato.empresa
            else None
        ),
        sexo=_catalogo_ref(candidato.sexo),
        escolaridad=_catalogo_ref(candidato.escolaridad),
        estatus=_catalogo_ref(candidato.estatus),
    )


@router.get("", response_model=list[CandidatoOut])
def listar_evaluados(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    buscar: str | None = Query(default=None, description="Filtra por nombre, apellidos o correo"),
    empresa_id: int | None = None,
    estatus_candidato_id: int | None = None,
    solo_activos: bool = False,
    db: Session = Depends(get_db),
):
    """Lista evaluados, con búsqueda y filtros opcionales."""
    service = CandidatoService(db)
    return [
        _to_out(c)
        for c in service.listar(
            skip=skip,
            limit=limit,
            buscar=buscar,
            empresa_id=empresa_id,
            estatus_candidato_id=estatus_candidato_id,
            solo_activos=solo_activos,
        )
    ]


@router.get("/{candidato_id}", response_model=CandidatoOut)
def obtener_evaluado(candidato_id: int, db: Session = Depends(get_db)):
    """Obtiene un evaluado por su id."""
    service = CandidatoService(db)
    return _to_out(service.obtener(candidato_id))


@router.get("/{candidato_id}/expediente", response_model=ExpedienteCandidatoOut)
def obtener_expediente(candidato_id: int, db: Session = Depends(get_db)):
    """Expediente del evaluado: datos personales + evaluaciones asignadas."""
    service = CandidatoService(db)
    return service.obtener_expediente(candidato_id)


@router.post("", response_model=CandidatoOut, status_code=201)
def crear_evaluado(
    data: CandidatoCreate,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(get_current_usuario),
):
    """Crea un nuevo evaluado."""
    service = CandidatoService(db)
    return _to_out(service.crear(data, creado_por_usuario_id=usuario_actual.id))


@router.put("/{candidato_id}", response_model=CandidatoOut)
def actualizar_evaluado(
    candidato_id: int,
    data: CandidatoUpdate,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(get_current_usuario),
):
    """Actualiza los datos de un evaluado."""
    service = CandidatoService(db)
    return _to_out(
        service.actualizar(candidato_id, data, actualizado_por_usuario_id=usuario_actual.id)
    )


@router.delete("/{candidato_id}", response_model=CandidatoOut)
def desactivar_evaluado(
    candidato_id: int,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(get_current_usuario),
):
    """Desactiva (baja lógica) a un evaluado. Nunca se elimina físicamente."""
    service = CandidatoService(db)
    return _to_out(
        service.desactivar(candidato_id, desactivado_por_usuario_id=usuario_actual.id)
    )


# ---------------------------------------------------------------------------
# Accesos temporales (sección 8) y asignación de evaluaciones (sección 14)
# ---------------------------------------------------------------------------


@router.post(
    "/{candidato_id}/accesos-temporales",
    response_model=AccesoTemporalCreadoOut,
    status_code=201,
)
def crear_acceso_temporal(
    candidato_id: int,
    data: CrearAccesoTemporalRequest,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(get_current_usuario),
):
    """Genera credenciales temporales para que el evaluado entre al portal.

    La contraseña en claro solo se devuelve en esta respuesta — no se
    puede recuperar después.
    """
    service = AccesoTemporalService(db)
    acceso, password_en_claro = service.crear_acceso(
        candidato_id, data.horas_vigencia, creado_por_usuario_id=usuario_actual.id
    )
    return AccesoTemporalCreadoOut(
        id=acceso.id, usuario=acceso.usuario, password_temporal=password_en_claro,
        expira_en=acceso.expira_en,
    )


@router.get("/{candidato_id}/accesos-temporales", response_model=list[AccesoTemporalOut])
def listar_accesos_temporales(candidato_id: int, db: Session = Depends(get_db)):
    """Lista los accesos temporales creados para un evaluado (sin contraseñas)."""
    service = AccesoTemporalService(db)
    return [
        AccesoTemporalOut(
            id=a.id, usuario=a.usuario, creado_en=a.creado_en, expira_en=a.expira_en,
            intentos_fallidos=a.intentos_fallidos, ultimo_acceso=a.ultimo_acceso,
            sesion_activa=a.sesion_activa, revocado=a.revocado,
        )
        for a in service.listar_por_candidato(candidato_id)
    ]


@router.post("/accesos-temporales/{acceso_id}/revocar", response_model=AccesoTemporalOut)
def revocar_acceso_temporal(
    acceso_id: int,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(get_current_usuario),
):
    """Revoca un acceso temporal (deja de poder usarse para iniciar sesión)."""
    service = AccesoTemporalService(db)
    a = service.revocar(acceso_id, usuario_id=usuario_actual.id)
    return AccesoTemporalOut(
        id=a.id, usuario=a.usuario, creado_en=a.creado_en, expira_en=a.expira_en,
        intentos_fallidos=a.intentos_fallidos, ultimo_acceso=a.ultimo_acceso,
        sesion_activa=a.sesion_activa, revocado=a.revocado,
    )


@router.post("/{candidato_id}/asignaciones", response_model=AsignacionOut, status_code=201)
def asignar_evaluacion(
    candidato_id: int,
    data: AsignarEvaluacionRequest,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(get_current_usuario),
):
    """Asigna una evaluación (prueba) a un evaluado."""
    service = AsignacionService(db)
    a = service.asignar(
        candidato_id, data.prueba_id, data.fecha_limite, asignado_por_usuario_id=usuario_actual.id
    )
    return AsignacionOut(
        id=a.id, prueba_id=a.prueba_id, prueba_nombre=a.prueba.nombre, estatus=a.estatus.codigo,
        fecha_asignacion=a.fecha_asignacion, fecha_limite=a.fecha_limite,
    )


@router.get("/{candidato_id}/asignaciones", response_model=list[AsignacionOut])
def listar_asignaciones(candidato_id: int, db: Session = Depends(get_db)):
    """Lista las evaluaciones asignadas a un evaluado."""
    service = AsignacionService(db)
    return [
        AsignacionOut(
            id=a.id, prueba_id=a.prueba_id, prueba_nombre=a.prueba.nombre, estatus=a.estatus.codigo,
            fecha_asignacion=a.fecha_asignacion, fecha_limite=a.fecha_limite,
        )
        for a in service.listar_por_candidato(candidato_id)
    ]
