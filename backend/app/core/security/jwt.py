"""
Creación y verificación de JSON Web Tokens (JWT).

Se emiten dos tipos de token:

- `access`: de vida corta, se envía en cada request protegido
  (header `Authorization: Bearer <token>`).
- `refresh`: de vida más larga, solo se usa para obtener un nuevo
  access token sin pedir credenciales de nuevo. Está ligado a una
  fila de `Sesion` (vía `jti`) para poder revocarlo.

Ambos incluyen un `jti` (JWT ID) único que se guarda en la tabla
`sesiones`, de modo que cerrar sesión o revocar un acceso invalida
el token aunque no haya expirado todavía.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from jose import JWTError, jwt

from app.core.config.settings import get_settings

settings = get_settings()

TokenType = Literal["access", "refresh"]


class TokenError(Exception):
    """Se lanza cuando un token es inválido, está mal formado o expiró."""


def _create_token(
    subject: str,
    token_type: TokenType,
    expires_delta: timedelta,
    extra_claims: dict[str, Any] | None = None,
) -> tuple[str, str, datetime]:
    now = datetime.now(timezone.utc)
    expires_at = now + expires_delta
    jti = str(uuid.uuid4())

    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "jti": jti,
        "iat": now,
        "exp": expires_at,
    }
    if extra_claims:
        payload.update(extra_claims)

    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, jti, expires_at


def create_access_token(
    usuario_id: int, roles: list[str], actor: str = "admin"
) -> tuple[str, str, datetime]:
    """Crea un access token. Devuelve (token, jti, fecha_expiracion).

    `actor` distingue el tipo de identidad autenticada ("admin" para
    `Usuario`, "evaluado" para `UsuarioTemporal`) para que un token de
    un tipo nunca pueda usarse para autenticar al otro, aunque el
    `sub` (id numérico) coincida entre ambas tablas.
    """
    return _create_token(
        subject=str(usuario_id),
        token_type="access",
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        extra_claims={"roles": roles, "actor": actor},
    )


def create_refresh_token(usuario_id: int, actor: str = "admin") -> tuple[str, str, datetime]:
    """Crea un refresh token. Devuelve (token, jti, fecha_expiracion)."""
    return _create_token(
        subject=str(usuario_id),
        token_type="refresh",
        expires_delta=timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES),
        extra_claims={"actor": actor},
    )


def marca_de_sesion(momento: datetime) -> int:
    """Convierte el instante del último login de un acceso temporal en
    un entero (microsegundos desde 1970), que viaja dentro del token
    como claim `sid`. Es la "generación" de la sesión: cada login nuevo
    cambia `ultimo_acceso`, e invalida los tokens anteriores."""
    if momento.tzinfo is None:
        momento = momento.replace(tzinfo=timezone.utc)
    return (momento - datetime(1970, 1, 1, tzinfo=timezone.utc)) // timedelta(microseconds=1)


def create_evaluado_access_token(
    usuario_temporal_id: int, expira_en: datetime, sesion_marca: int
) -> tuple[str, str, datetime]:
    """Crea el access token de un evaluado autenticado con acceso
    temporal (`UsuarioTemporal`).

    Su vigencia nunca excede `expira_en` (la fecha de expiración del
    propio acceso temporal, sección 8 de los requisitos), aunque sea
    menor que `EVALUADO_TOKEN_EXPIRE_MINUTES`: un token de evaluado
    jamás debe sobrevivir a la expiración de su acceso.
    """
    limite_por_configuracion = datetime.now(timezone.utc) + timedelta(
        minutes=settings.EVALUADO_TOKEN_EXPIRE_MINUTES
    )
    expiracion_efectiva = min(expira_en, limite_por_configuracion)
    delta = expiracion_efectiva - datetime.now(timezone.utc)
    if delta.total_seconds() <= 0:
        delta = timedelta(seconds=1)

    return _create_token(
        subject=str(usuario_temporal_id),
        token_type="access",
        expires_delta=delta,
        extra_claims={"roles": ["EVALUADO"], "actor": "evaluado", "sid": sesion_marca},
    )


def decode_token(token: str, expected_type: TokenType | None = None) -> dict[str, Any]:
    """Decodifica y valida un JWT. Lanza TokenError si no es válido."""
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
    except JWTError as exc:
        raise TokenError("Token inválido o expirado.") from exc

    if expected_type and payload.get("type") != expected_type:
        raise TokenError(f"Se esperaba un token de tipo '{expected_type}'.")

    return payload
