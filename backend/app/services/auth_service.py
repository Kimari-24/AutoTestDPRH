"""
Servicio de autenticación.

Orquesta login, renovación y cierre de sesión de usuarios
administrativos. No expone detalles de SQLAlchemy: usa los
repositorios para toda lectura/escritura.
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.exceptions.base import UnauthorizedError
from app.core.security.jwt import TokenError, create_access_token, create_refresh_token, decode_token
from app.core.security.password import verify_password
from app.models.seguridad import Sesion, Usuario
from app.repositories.auditoria_repository import BitacoraRepository, HistorialLoginRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.schemas.auth import TokenResponse


def _roles_de(usuario: Usuario) -> list[str]:
    return [asignacion.rol.codigo for asignacion in usuario.roles]


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.usuarios = UsuarioRepository(db)
        self.historial_login = HistorialLoginRepository(db)
        self.bitacora = BitacoraRepository(db)

    def login(
        self,
        correo: str,
        password: str,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> TokenResponse:
        usuario = self.usuarios.get_by_correo(correo)

        if usuario is None or not verify_password(password, usuario.password_hash):
            self.historial_login.registrar(
                usuario_id=usuario.id if usuario else None,
                usuario_temporal_id=None,
                exitoso=False,
                ip=ip,
                user_agent=user_agent,
            )
            self.db.commit()
            raise UnauthorizedError("Correo o contraseña incorrectos.")

        if not usuario.activo:
            self.historial_login.registrar(
                usuario_id=usuario.id,
                usuario_temporal_id=None,
                exitoso=False,
                ip=ip,
                user_agent=user_agent,
            )
            self.db.commit()
            raise UnauthorizedError("El usuario está desactivado.")

        roles = _roles_de(usuario)
        access_token, access_jti, access_exp = create_access_token(usuario.id, roles, actor="admin")
        refresh_token, refresh_jti, refresh_exp = create_refresh_token(usuario.id, actor="admin")

        sesion = Sesion(
            usuario_id=usuario.id,
            token_jti=refresh_jti,
            ip=ip,
            user_agent=user_agent,
            creado_en=datetime.now(timezone.utc),
            expira_en=refresh_exp,
            activa=True,
        )
        self.db.add(sesion)

        self.historial_login.registrar(
            usuario_id=usuario.id,
            usuario_temporal_id=None,
            exitoso=True,
            ip=ip,
            user_agent=user_agent,
        )
        self.bitacora.registrar(
            usuario_id=usuario.id,
            accion="LOGIN",
            entidad="usuarios",
            entidad_id=usuario.id,
            ip=ip,
        )
        self.db.commit()

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=access_exp,
        )

    def refresh(self, refresh_token: str) -> TokenResponse:
        try:
            payload = decode_token(refresh_token, expected_type="refresh")
        except TokenError as exc:
            raise UnauthorizedError(str(exc)) from exc

        sesion = (
            self.db.query(Sesion)
            .filter(Sesion.token_jti == payload["jti"])
            .one_or_none()
        )
        if sesion is None or not sesion.activa:
            raise UnauthorizedError("La sesión ya no es válida. Inicia sesión de nuevo.")
        if sesion.expira_en < datetime.now(timezone.utc):
            sesion.activa = False
            self.db.commit()
            raise UnauthorizedError("La sesión expiró. Inicia sesión de nuevo.")

        usuario = self.usuarios.get_by_id(sesion.usuario_id)
        if usuario is None or not usuario.activo:
            raise UnauthorizedError("El usuario ya no está disponible.")

        roles = _roles_de(usuario)
        access_token, _, access_exp = create_access_token(usuario.id, roles, actor="admin")

        # Rotación del refresh token (BUG-05 de QA): cada uso invalida el
        # refresh token presentado y entrega uno nuevo. Así un refresh
        # token robado deja de servir en cuanto el dueño legítimo renueva
        # su sesión, y deja de ser un pase válido por 7 días fijos.
        nuevo_refresh, nuevo_jti, nuevo_exp = create_refresh_token(usuario.id, actor="admin")
        sesion.activa = False
        self.db.add(
            Sesion(
                usuario_id=usuario.id,
                token_jti=nuevo_jti,
                ip=sesion.ip,
                user_agent=sesion.user_agent,
                creado_en=datetime.now(timezone.utc),
                expira_en=nuevo_exp,
                activa=True,
            )
        )
        self.db.commit()

        return TokenResponse(
            access_token=access_token,
            refresh_token=nuevo_refresh,
            expires_at=access_exp,
        )

    def logout(self, refresh_token: str) -> None:
        try:
            payload = decode_token(refresh_token, expected_type="refresh")
        except TokenError:
            # Cerrar sesión con un token ya inválido no es un error para
            # el usuario: el resultado deseado (no quedar autenticado)
            # ya se cumple.
            return

        sesion = (
            self.db.query(Sesion)
            .filter(Sesion.token_jti == payload["jti"])
            .one_or_none()
        )
        if sesion is not None:
            sesion.activa = False
            self.bitacora.registrar(
                usuario_id=sesion.usuario_id,
                accion="LOGOUT",
                entidad="usuarios",
                entidad_id=sesion.usuario_id,
            )
            self.db.commit()

    def get_usuario_desde_access_token(self, access_token: str) -> Usuario:
        try:
            payload = decode_token(access_token, expected_type="access")
        except TokenError as exc:
            raise UnauthorizedError("Credenciales inválidas o expiradas.") from exc

        if payload.get("actor") != "admin":
            raise UnauthorizedError("Credenciales inválidas o expiradas.")

        usuario_id = int(payload["sub"])
        usuario = self.usuarios.get_by_id(usuario_id)
        if usuario is None or not usuario.activo:
            raise UnauthorizedError("El usuario ya no está disponible.")
        return usuario
