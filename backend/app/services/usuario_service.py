"""
Servicio de gestión de usuarios administrativos.

Contiene la lógica de negocio para crear, actualizar, listar y
desactivar usuarios del panel administrativo, incluida la asignación
de roles. Los endpoints (`api/routes/usuarios.py`) no deben construir
objetos `Usuario` directamente ni tocar SQLAlchemy.
"""

from sqlalchemy.orm import Session

from app.core.exceptions.base import ConflictError, NotFoundError, UnauthorizedError, ValidationError
from app.core.security.password import hash_password, verify_password
from app.models.seguridad import Rol, Usuario, UsuarioRol
from app.repositories.auditoria_repository import BitacoraRepository, SesionRepository
from app.repositories.usuario_repository import RolRepository, UsuarioRepository
from app.schemas.usuario import CambiarPasswordRequest, UsuarioCreate, UsuarioUpdate


class UsuarioService:
    def __init__(self, db: Session):
        self.db = db
        self.usuarios = UsuarioRepository(db)
        self.roles = RolRepository(db)
        self.bitacora = BitacoraRepository(db)

    def listar(self, skip: int = 0, limit: int = 50) -> list[Usuario]:
        return self.usuarios.list(skip=skip, limit=limit)

    def obtener(self, usuario_id: int) -> Usuario:
        usuario = self.usuarios.get_by_id(usuario_id)
        if usuario is None:
            raise NotFoundError("Usuario no encontrado.")
        return usuario

    def crear(self, data: UsuarioCreate, creado_por_usuario_id: int | None = None) -> Usuario:
        if self.usuarios.get_by_correo(data.correo) is not None:
            raise ConflictError("Ya existe un usuario registrado con ese correo.")

        usuario = Usuario(
            nombre=data.nombre,
            apellidos=data.apellidos,
            correo=data.correo,
            password_hash=hash_password(data.password),
            activo=True,
        )
        self.usuarios.create(usuario)
        self._asignar_roles(usuario, data.roles)
        self.usuarios.save()

        self.bitacora.registrar(
            usuario_id=creado_por_usuario_id,
            accion="CREAR",
            entidad="usuarios",
            entidad_id=usuario.id,
        )
        self.db.commit()
        return self.obtener(usuario.id)

    # --- protección contra quedarse sin administradores (BUG-09 de QA) ---

    @staticmethod
    def _es_administrador(usuario: Usuario) -> bool:
        return any(asignacion.rol.codigo == "ADMINISTRADOR" for asignacion in usuario.roles)

    def _contar_administradores_activos(self) -> int:
        return (
            self.db.query(Usuario.id)
            .join(UsuarioRol, UsuarioRol.usuario_id == Usuario.id)
            .join(Rol, Rol.id == UsuarioRol.rol_id)
            .filter(Rol.codigo == "ADMINISTRADOR", Usuario.activo.is_(True))
            .distinct()
            .count()
        )

    def actualizar(
        self, usuario_id: int, data: UsuarioUpdate, actualizado_por_usuario_id: int | None = None
    ) -> Usuario:
        usuario = self.obtener(usuario_id)

        if data.correo and data.correo != usuario.correo:
            existente = self.usuarios.get_by_correo(data.correo)
            if existente is not None and existente.id != usuario.id:
                raise ConflictError("Ya existe un usuario registrado con ese correo.")
            usuario.correo = data.correo

        if data.nombre is not None:
            usuario.nombre = data.nombre
        if data.apellidos is not None:
            usuario.apellidos = data.apellidos
        if data.roles is not None:
            quita_admin = self._es_administrador(usuario) and "ADMINISTRADOR" not in data.roles
            if quita_admin:
                if usuario.id == actualizado_por_usuario_id:
                    raise ConflictError(
                        "No puedes quitarte a ti mismo el rol ADMINISTRADOR: te quedarías sin acceso."
                    )
                if usuario.activo and self._contar_administradores_activos() <= 1:
                    raise ConflictError(
                        "No se puede quitar el rol ADMINISTRADOR al único administrador activo."
                    )
            self._asignar_roles(usuario, data.roles, reemplazar=True)

        self.usuarios.save()
        self.bitacora.registrar(
            usuario_id=actualizado_por_usuario_id,
            accion="ACTUALIZAR",
            entidad="usuarios",
            entidad_id=usuario.id,
        )
        self.db.commit()
        return self.obtener(usuario.id)

    def desactivar(self, usuario_id: int, desactivado_por_usuario_id: int | None = None) -> Usuario:
        usuario = self.obtener(usuario_id)
        if usuario.id == desactivado_por_usuario_id:
            raise ConflictError("No puedes desactivar tu propia cuenta.")
        if (
            usuario.activo
            and self._es_administrador(usuario)
            and self._contar_administradores_activos() <= 1
        ):
            raise ConflictError("No se puede desactivar al único administrador activo.")

        usuario.activo = False
        SesionRepository(self.db).revocar_todas_de_usuario(usuario.id)
        self.usuarios.save()
        self.bitacora.registrar(
            usuario_id=desactivado_por_usuario_id,
            accion="DESACTIVAR",
            entidad="usuarios",
            entidad_id=usuario.id,
        )
        self.db.commit()
        return usuario

    def cambiar_password(self, usuario_id: int, data: CambiarPasswordRequest) -> None:
        """Cambio de contraseña por el propio usuario (requiere la
        contraseña actual). No es lo mismo que un reseteo por el
        administrador; aquí siempre hay que demostrar conocer la
        contraseña vigente."""
        usuario = self.obtener(usuario_id)
        if not verify_password(data.password_actual, usuario.password_hash):
            raise UnauthorizedError("La contraseña actual no es correcta.")

        usuario.password_hash = hash_password(data.password_nueva)
        # Tras cambiar la contraseña, ninguna sesión previa debe seguir
        # renovándose (BUG-04 de QA): si la contraseña estaba
        # comprometida, un refresh token robado ya no sirve.
        SesionRepository(self.db).revocar_todas_de_usuario(usuario_id)
        self.usuarios.save()
        self.bitacora.registrar(
            usuario_id=usuario_id, accion="CAMBIAR_PASSWORD", entidad="usuarios", entidad_id=usuario.id
        )
        self.db.commit()

    def _asignar_roles(
        self, usuario: Usuario, codigos_rol: list[str], reemplazar: bool = False
    ) -> None:
        if reemplazar:
            self.usuarios.clear_roles(usuario)
            self.usuarios.save()

        for codigo in codigos_rol:
            rol = self.roles.get_by_codigo(codigo)
            if rol is None:
                raise ValidationError(f"El rol '{codigo}' no existe.")
            self.usuarios.add_rol(usuario, rol)
