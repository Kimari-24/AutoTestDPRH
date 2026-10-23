"""Repositorio de acceso a datos para `Usuario` (personal administrativo).

Esta es la única capa que debe construir queries de SQLAlchemy sobre
estas tablas; `services/` nunca debe hacer `db.query(...)` o
`select(...)` directamente.
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.seguridad import Rol, Usuario, UsuarioRol


class UsuarioRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, usuario_id: int) -> Usuario | None:
        stmt = (
            select(Usuario)
            .where(Usuario.id == usuario_id)
            .options(selectinload(Usuario.roles).selectinload(UsuarioRol.rol))
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_correo(self, correo: str) -> Usuario | None:
        stmt = (
            select(Usuario)
            .where(func.lower(Usuario.correo) == correo.strip().lower())
            .options(selectinload(Usuario.roles).selectinload(UsuarioRol.rol))
            .order_by(Usuario.id)
        )
        # `.first()` y no `scalar_one_or_none()`: si ya existieran dos
        # filas que solo difieren en mayúsculas (datos previos a la
        # normalización de correos), no debe fallar con un error.
        return self.db.execute(stmt).scalars().first()

    def list(self, skip: int = 0, limit: int = 50) -> list[Usuario]:
        stmt = (
            select(Usuario)
            .options(selectinload(Usuario.roles).selectinload(UsuarioRol.rol))
            .order_by(Usuario.id)
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())

    def create(self, usuario: Usuario) -> Usuario:
        self.db.add(usuario)
        self.db.flush()
        return usuario

    def add_rol(self, usuario: Usuario, rol: Rol) -> None:
        self.db.add(UsuarioRol(usuario_id=usuario.id, rol_id=rol.id))

    def clear_roles(self, usuario: Usuario) -> None:
        for asignacion in list(usuario.roles):
            self.db.delete(asignacion)

    def save(self) -> None:
        self.db.flush()


class RolRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_codigo(self, codigo: str) -> Rol | None:
        stmt = select(Rol).where(Rol.codigo == codigo)
        return self.db.execute(stmt).scalar_one_or_none()

    def list(self) -> list[Rol]:
        return list(self.db.execute(select(Rol)).scalars().all())
