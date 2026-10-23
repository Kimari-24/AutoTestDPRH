"""
Dependencia de autenticación del portal del evaluado.

Completamente separada de `api/dependencies/auth.py` (usuarios
administrativos): valida un token cuyo `actor` sea "evaluado" y
recarga el `UsuarioTemporal` en cada request para confirmar que sigue
vigente (no revocado, no expirado, con sesión activa) — un evaluado
nunca debe poder usar un token de administrador ni viceversa.
"""

from fastapi import Depends
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session

from app.core.exceptions.base import UnauthorizedError
from app.core.security.jwt import TokenError, decode_token
from app.db.session import get_db
from app.models.candidato import UsuarioTemporal
from app.services.acceso_temporal_service import AccesoTemporalService

_bearer_scheme = HTTPBearer(auto_error=True)


def get_evaluado_actual(
    credenciales=Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> UsuarioTemporal:
    """Devuelve el `UsuarioTemporal` autenticado a partir del access token."""
    try:
        payload = decode_token(credenciales.credentials, expected_type="access")
    except TokenError as exc:
        raise UnauthorizedError("Credenciales inválidas o expiradas.") from exc

    if payload.get("actor") != "evaluado":
        raise UnauthorizedError("Credenciales inválidas o expiradas.")

    service = AccesoTemporalService(db)
    return service.obtener_evaluado_activo(int(payload["sub"]), payload.get("sid"))
