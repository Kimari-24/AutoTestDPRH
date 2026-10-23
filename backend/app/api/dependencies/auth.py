"""
Dependencias de FastAPI relacionadas con autenticación y autorización.

- `get_current_usuario`: extrae y valida el JWT del header
  Authorization, y devuelve el `Usuario` autenticado.
- `require_roles`: fábrica de dependencias para proteger un endpoint
  a uno o varios roles (RBAC). Un endpoint sin esta dependencia solo
  exige estar autenticado, no un rol específico.

Los EVALUADOS no usan estas dependencias: su autenticación (acceso
temporal) se implementa por separado en la Fase 7, ya que no usan
`Usuario` ni JWT de la misma forma.
"""

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.exceptions.base import ForbiddenError
from app.db.session import get_db
from app.models.seguridad import Usuario
from app.services.auth_service import AuthService

# tokenUrl es solo informativo (para la UI de /docs); el login real
# de AutoTest DPRH se hace con JSON en POST /api/auth/login, no con
# un formulario OAuth2 clásico.
_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=True)


def get_current_usuario(
    token: str = Depends(_oauth2_scheme),
    db: Session = Depends(get_db),
) -> Usuario:
    """Devuelve el usuario administrativo autenticado a partir del access token."""
    auth_service = AuthService(db)
    return auth_service.get_usuario_desde_access_token(token)


def require_roles(*roles_permitidos: str):
    """Dependencia que exige que el usuario autenticado tenga al menos
    uno de los roles indicados.

    Uso:
        @router.get("/", dependencies=[Depends(require_roles("ADMINISTRADOR"))])
    """

    def _dependency(usuario: Usuario = Depends(get_current_usuario)) -> Usuario:
        codigos_usuario = {asignacion.rol.codigo for asignacion in usuario.roles}
        if not codigos_usuario.intersection(roles_permitidos):
            raise ForbiddenError(
                "No tienes permiso para realizar esta acción."
            )
        return usuario

    return _dependency
