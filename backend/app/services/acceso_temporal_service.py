"""
Servicio de accesos temporales (sección 8 de los requisitos).

Cubre dos roles distintos:
- El ADMINISTRADOR, que crea y revoca accesos temporales de un evaluado.
- El propio EVALUADO, que inicia sesión con esas credenciales.

Las contraseñas temporales se generan con `secrets` (aleatoriedad
criptográfica) y solo se devuelven UNA vez, en texto plano, en el
momento de crearlas — nunca se guardan ni se pueden recuperar después.
"""

import secrets
import string
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.exceptions.base import ForbiddenError, NotFoundError, UnauthorizedError
from app.core.security.jwt import create_evaluado_access_token, marca_de_sesion
from app.core.security.password import hash_password, verify_password
from app.models.candidato import Candidato, UsuarioTemporal
from app.repositories.acceso_temporal_repository import AccesoTemporalRepository
from app.repositories.auditoria_repository import BitacoraRepository, HistorialLoginRepository
from app.repositories.candidato_repository import CandidatoRepository
from app.schemas.portal import TokenEvaluadoResponse

MAXIMO_INTENTOS_FALLIDOS = 5
_ALFABETO_PASSWORD = string.ascii_letters + string.digits


def _generar_password_temporal(longitud: int = 10) -> str:
    return "".join(secrets.choice(_ALFABETO_PASSWORD) for _ in range(longitud))


class AccesoTemporalService:
    def __init__(self, db: Session):
        self.db = db
        self.accesos = AccesoTemporalRepository(db)
        self.candidatos = CandidatoRepository(db)
        self.bitacora = BitacoraRepository(db)
        self.historial_login = HistorialLoginRepository(db)

    # --- administración (ADMINISTRADOR) ---

    def crear_acceso(
        self, candidato_id: int, horas_vigencia: int, creado_por_usuario_id: int | None = None
    ) -> tuple[UsuarioTemporal, str]:
        candidato = self.candidatos.get_by_id(candidato_id)
        if candidato is None:
            raise NotFoundError("Evaluado no encontrado.")

        usuario_generado = self._generar_usuario_unico(candidato)
        password_en_claro = _generar_password_temporal()

        acceso = UsuarioTemporal(
            candidato_id=candidato.id,
            usuario=usuario_generado,
            password_hash=hash_password(password_en_claro),
            creado_en=datetime.now(timezone.utc),
            expira_en=datetime.now(timezone.utc) + timedelta(hours=horas_vigencia),
            intentos_fallidos=0,
            sesion_activa=False,
            revocado=False,
        )
        self.accesos.create(acceso)
        self.bitacora.registrar(
            usuario_id=creado_por_usuario_id,
            accion="CREAR",
            entidad="usuarios_temporales",
            entidad_id=acceso.id,
        )
        self.db.commit()
        return acceso, password_en_claro

    def listar_por_candidato(self, candidato_id: int) -> list[UsuarioTemporal]:
        if self.candidatos.get_by_id(candidato_id) is None:
            raise NotFoundError("Evaluado no encontrado.")
        return self.accesos.list_por_candidato(candidato_id)

    def revocar(self, acceso_id: int, usuario_id: int | None = None) -> UsuarioTemporal:
        acceso = self.accesos.get_by_id(acceso_id)
        if acceso is None:
            raise NotFoundError("Acceso temporal no encontrado.")
        acceso.revocado = True
        acceso.revocado_en = datetime.now(timezone.utc)
        acceso.sesion_activa = False
        self.accesos.save()
        self.bitacora.registrar(
            usuario_id=usuario_id, accion="REVOCAR", entidad="usuarios_temporales", entidad_id=acceso.id
        )
        self.db.commit()
        return acceso

    def _generar_usuario_unico(self, candidato: Candidato) -> str:
        base = "".join(ch for ch in candidato.correo.split("@")[0].lower() if ch.isalnum())[:12] or "evaluado"
        for _ in range(10):
            candidato_usuario = f"{base}{secrets.randbelow(9000) + 1000}"
            if self.accesos.get_by_usuario(candidato_usuario) is None:
                return candidato_usuario
        raise RuntimeError("No se pudo generar un usuario temporal único.")

    # --- autenticación del evaluado ---

    def login(
        self, usuario: str, password: str, ip: str | None = None, user_agent: str | None = None
    ) -> TokenEvaluadoResponse:
        acceso = self.accesos.get_by_usuario(usuario)

        if acceso is None or not verify_password(password, acceso.password_hash):
            if acceso is not None:
                acceso.intentos_fallidos += 1
                self.accesos.save()
            self.historial_login.registrar(
                usuario_id=None, usuario_temporal_id=acceso.id if acceso else None,
                exitoso=False, ip=ip, user_agent=user_agent,
            )
            self.db.commit()
            raise UnauthorizedError("Usuario o contraseña incorrectos.")

        if acceso.revocado:
            raise ForbiddenError("Este acceso ha sido revocado.")
        if acceso.expira_en < datetime.now(timezone.utc):
            raise ForbiddenError("Este acceso ha expirado.")
        if acceso.intentos_fallidos >= MAXIMO_INTENTOS_FALLIDOS:
            raise ForbiddenError(
                "Este acceso se bloqueó por demasiados intentos fallidos. Contacta al administrador."
            )

        # Si el evaluado fue desactivado, su acceso temporal ya no debe
        # funcionar aunque siga vigente (BUG-02 de QA).
        candidato = self.candidatos.get_by_id(acceso.candidato_id)
        if candidato is None or not candidato.activo:
            raise ForbiddenError("Tu usuario está desactivado. Contacta al administrador.")

        ahora = datetime.now(timezone.utc)
        acceso.intentos_fallidos = 0
        acceso.ultimo_acceso = ahora
        acceso.sesion_activa = True
        self.accesos.save()

        self.historial_login.registrar(
            usuario_id=None, usuario_temporal_id=acceso.id, exitoso=True, ip=ip, user_agent=user_agent
        )
        self.bitacora.registrar(
            usuario_id=None, accion="LOGIN_EVALUADO", entidad="usuarios_temporales",
            entidad_id=acceso.id, ip=ip,
        )
        self.db.commit()

        access_token, _, expires_at = create_evaluado_access_token(
            acceso.id, acceso.expira_en, sesion_marca=marca_de_sesion(ahora)
        )
        return TokenEvaluadoResponse(
            access_token=access_token,
            expires_at=expires_at,
            candidato_nombre=f"{candidato.nombre} {candidato.apellidos}" if candidato else "",
        )

    def logout(self, acceso_id: int) -> None:
        acceso = self.accesos.get_by_id(acceso_id)
        if acceso is not None:
            acceso.sesion_activa = False
            self.accesos.save()
            self.bitacora.registrar(
                usuario_id=None, accion="LOGOUT_EVALUADO", entidad="usuarios_temporales",
                entidad_id=acceso.id,
            )
            self.db.commit()

    def obtener_evaluado_activo(
        self, usuario_temporal_id: int, sesion_marca: int | None = None
    ) -> UsuarioTemporal:
        """Vuelve a validar (en cada request) que el acceso siga vigente:
        ni revocado, ni expirado, ni con la sesión cerrada, ni el
        evaluado desactivado — y que el token sea el de la sesión
        VIGENTE (BUG-06 de QA): tras un logout, o un nuevo login, el
        token anterior deja de servir aunque no haya expirado."""
        acceso = self.accesos.get_by_id(usuario_temporal_id)
        if acceso is None:
            raise UnauthorizedError("Acceso no encontrado.")
        if acceso.ultimo_acceso is None or sesion_marca != marca_de_sesion(acceso.ultimo_acceso):
            raise UnauthorizedError("La sesión ya no es válida. Inicia sesión de nuevo.")
        if acceso.revocado:
            raise ForbiddenError("Este acceso ha sido revocado.")
        if acceso.expira_en < datetime.now(timezone.utc):
            raise ForbiddenError("Este acceso ha expirado.")
        if not acceso.sesion_activa:
            raise UnauthorizedError("La sesión ya no está activa. Inicia sesión de nuevo.")
        candidato = self.candidatos.get_by_id(acceso.candidato_id)
        if candidato is None or not candidato.activo:
            raise ForbiddenError("Tu usuario está desactivado. Contacta al administrador.")
        return acceso
