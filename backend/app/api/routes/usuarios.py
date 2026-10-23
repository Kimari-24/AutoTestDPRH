"""
Endpoints de gestión de usuarios administrativos.

Todo este módulo está restringido al rol ADMINISTRADOR: es quien,
según los requisitos, "administra usuarios administrativos".
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_usuario, require_roles
from app.db.session import get_db
from app.models.seguridad import Usuario
from app.schemas.usuario import CambiarPasswordRequest, UsuarioCreate, UsuarioOut, UsuarioUpdate
from app.services.usuario_service import UsuarioService

router = APIRouter(
    prefix="/usuarios",
    tags=["Usuarios administrativos"],
    dependencies=[Depends(require_roles("ADMINISTRADOR"))],
)


def _to_out(usuario: Usuario) -> UsuarioOut:
    return UsuarioOut(
        id=usuario.id,
        nombre=usuario.nombre,
        apellidos=usuario.apellidos,
        correo=usuario.correo,
        activo=usuario.activo,
        roles=[asignacion.rol.codigo for asignacion in usuario.roles],
        creado_en=usuario.creado_en,
    )


@router.get("", response_model=list[UsuarioOut])
def listar_usuarios(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Lista los usuarios administrativos del sistema."""
    service = UsuarioService(db)
    return [_to_out(u) for u in service.listar(skip=skip, limit=limit)]


@router.get("/{usuario_id}", response_model=UsuarioOut)
def obtener_usuario(usuario_id: int, db: Session = Depends(get_db)):
    """Obtiene un usuario administrativo por su id."""
    service = UsuarioService(db)
    return _to_out(service.obtener(usuario_id))


@router.post("", response_model=UsuarioOut, status_code=201)
def crear_usuario(
    data: UsuarioCreate,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(get_current_usuario),
):
    """Crea un nuevo usuario administrativo."""
    service = UsuarioService(db)
    return _to_out(service.crear(data, creado_por_usuario_id=usuario_actual.id))


@router.put("/{usuario_id}", response_model=UsuarioOut)
def actualizar_usuario(
    usuario_id: int,
    data: UsuarioUpdate,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(get_current_usuario),
):
    """Actualiza los datos o roles de un usuario administrativo."""
    service = UsuarioService(db)
    return _to_out(
        service.actualizar(usuario_id, data, actualizado_por_usuario_id=usuario_actual.id)
    )


@router.delete("/{usuario_id}", response_model=UsuarioOut)
def desactivar_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(get_current_usuario),
):
    """Desactiva (baja lógica) a un usuario administrativo. Nunca se elimina físicamente."""
    service = UsuarioService(db)
    return _to_out(
        service.desactivar(usuario_id, desactivado_por_usuario_id=usuario_actual.id)
    )


@router.put("/me/password", status_code=204)
def cambiar_mi_password(
    data: CambiarPasswordRequest,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(get_current_usuario),
):
    """El propio usuario cambia su contraseña (requiere la contraseña actual)."""
    service = UsuarioService(db)
    service.cambiar_password(usuario_actual.id, data)
