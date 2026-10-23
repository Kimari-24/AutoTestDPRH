"""
Endpoints de autenticación para usuarios administrativos.

No incluye autenticación de evaluados (acceso temporal) — eso se
implementa en la Fase 7 bajo un flujo distinto.
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_usuario
from app.core.security.rate_limit import limitar_tasa
from app.db.session import get_db
from app.models.seguridad import Usuario
from app.schemas.auth import LoginRequest, RefreshRequest, TokenResponse, UsuarioMe
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Autenticación"])

_limite_login = limitar_tasa("auth_login", maximo=10, ventana_segundos=60)


def _roles_de(usuario: Usuario) -> list[str]:
    return [asignacion.rol.codigo for asignacion in usuario.roles]


@router.post("/login", response_model=TokenResponse, dependencies=[Depends(_limite_login)])
def login(data: LoginRequest, request: Request, db: Session = Depends(get_db)):
    """Autentica a un usuario administrativo y devuelve un par de tokens JWT."""
    auth_service = AuthService(db)
    return auth_service.login(
        correo=data.correo,
        password=data.password,
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh(data: RefreshRequest, db: Session = Depends(get_db)):
    """Obtiene un nuevo access token a partir de un refresh token válido."""
    auth_service = AuthService(db)
    return auth_service.refresh(data.refresh_token)


@router.post("/logout", status_code=204)
def logout(data: RefreshRequest, db: Session = Depends(get_db)):
    """Revoca la sesión asociada al refresh token indicado."""
    auth_service = AuthService(db)
    auth_service.logout(data.refresh_token)


@router.get("/me", response_model=UsuarioMe)
def me(usuario: Usuario = Depends(get_current_usuario)):
    """Devuelve los datos del usuario administrativo autenticado."""
    return UsuarioMe(
        id=usuario.id,
        nombre=usuario.nombre,
        apellidos=usuario.apellidos,
        correo=usuario.correo,
        roles=_roles_de(usuario),
        activo=usuario.activo,
    )
