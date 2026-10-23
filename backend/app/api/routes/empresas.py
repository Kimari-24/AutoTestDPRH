"""
Endpoints de administración de empresas.

Todo el módulo está restringido al rol ADMINISTRADOR. El rol
funcional EMPRESA (para que una empresa gestione a sus propios
evaluados) no está implementado en esta versión.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_usuario, require_roles
from app.db.session import get_db
from app.models.empresa import Empresa
from app.models.seguridad import Usuario
from app.schemas.empresa import EmpresaCreate, EmpresaOut, EmpresaUpdate
from app.services.empresa_service import EmpresaService

router = APIRouter(
    prefix="/empresas",
    tags=["Empresas"],
    dependencies=[Depends(require_roles("ADMINISTRADOR"))],
)


def _to_out(empresa: Empresa) -> EmpresaOut:
    return EmpresaOut(
        id=empresa.id,
        nombre_comercial=empresa.nombre_comercial,
        razon_social=empresa.razon_social,
        correo_contacto=empresa.correo_contacto,
        telefono_contacto=empresa.telefono_contacto,
        direccion=empresa.direccion,
        activo=empresa.activo,
        creado_en=empresa.creado_en,
        total_candidatos=len(empresa.candidatos),
    )


@router.get("", response_model=list[EmpresaOut])
def listar_empresas(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    buscar: str | None = Query(default=None, description="Filtra por nombre comercial o razón social"),
    solo_activas: bool = False,
    db: Session = Depends(get_db),
):
    """Lista las empresas registradas, con búsqueda y filtro opcionales."""
    service = EmpresaService(db)
    return [
        _to_out(e)
        for e in service.listar(skip=skip, limit=limit, buscar=buscar, solo_activas=solo_activas)
    ]


@router.get("/{empresa_id}", response_model=EmpresaOut)
def obtener_empresa(empresa_id: int, db: Session = Depends(get_db)):
    """Obtiene una empresa por su id."""
    service = EmpresaService(db)
    return _to_out(service.obtener(empresa_id))


@router.post("", response_model=EmpresaOut, status_code=201)
def crear_empresa(
    data: EmpresaCreate,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(get_current_usuario),
):
    """Crea una nueva empresa cliente de DPRH."""
    service = EmpresaService(db)
    return _to_out(service.crear(data, creado_por_usuario_id=usuario_actual.id))


@router.put("/{empresa_id}", response_model=EmpresaOut)
def actualizar_empresa(
    empresa_id: int,
    data: EmpresaUpdate,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(get_current_usuario),
):
    """Actualiza los datos de una empresa."""
    service = EmpresaService(db)
    return _to_out(
        service.actualizar(empresa_id, data, actualizado_por_usuario_id=usuario_actual.id)
    )


@router.delete("/{empresa_id}", response_model=EmpresaOut)
def desactivar_empresa(
    empresa_id: int,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(get_current_usuario),
):
    """Desactiva (baja lógica) una empresa. Nunca se elimina físicamente."""
    service = EmpresaService(db)
    return _to_out(
        service.desactivar(empresa_id, desactivado_por_usuario_id=usuario_actual.id)
    )
