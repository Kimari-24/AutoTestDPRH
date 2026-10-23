"""
Modelos de seguridad.

Cubre usuarios administrativos (rol ADMINISTRADOR y, a futuro,
usuarios de EMPRESA), el esquema RBAC (roles/permisos) y las tablas
de auditoría (bitácora, historial de login, historial de acciones).

Nota: los EVALUADOS no usan `Usuario` — se autentican con credenciales
temporales (`UsuarioTemporal`, ver `candidato.py`), ya que su acceso
es efímero y no requiere gestión de roles/permisos.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.empresa import Empresa


class Usuario(TimestampMixin, Base):
    """Usuario administrativo del sistema (ADMINISTRADOR o, a futuro, EMPRESA)."""

    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    apellidos: Mapped[str] = mapped_column(String(150), nullable=False)
    correo: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Solo aplica a usuarios con rol EMPRESA (no habilitado funcionalmente aun).
    empresa_id: Mapped[int | None] = mapped_column(
        ForeignKey("empresas.id"), nullable=True
    )
    empresa: Mapped["Empresa | None"] = relationship(back_populates="usuarios")

    roles: Mapped[list["UsuarioRol"]] = relationship(
        back_populates="usuario", cascade="all, delete-orphan"
    )
    sesiones: Mapped[list["Sesion"]] = relationship(back_populates="usuario")


class Rol(Base):
    """Rol del sistema: ADMINISTRADOR, EMPRESA o EVALUADO (conceptual)."""

    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(255), nullable=True)

    usuarios: Mapped[list["UsuarioRol"]] = relationship(back_populates="rol")
    permisos: Mapped[list["RolPermiso"]] = relationship(back_populates="rol")


class Permiso(Base):
    """Permiso granular que puede asignarse a uno o varios roles."""

    __tablename__ = "permisos"

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(255), nullable=True)

    roles: Mapped[list["RolPermiso"]] = relationship(back_populates="permiso")


class UsuarioRol(Base):
    """Tabla de asociación usuario <-> rol (un usuario puede tener varios roles)."""

    __tablename__ = "usuario_roles"

    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), primary_key=True)
    rol_id: Mapped[int] = mapped_column(ForeignKey("roles.id"), primary_key=True)

    usuario: Mapped["Usuario"] = relationship(back_populates="roles")
    rol: Mapped["Rol"] = relationship(back_populates="usuarios")


class RolPermiso(Base):
    """Tabla de asociación rol <-> permiso."""

    __tablename__ = "rol_permisos"

    rol_id: Mapped[int] = mapped_column(ForeignKey("roles.id"), primary_key=True)
    permiso_id: Mapped[int] = mapped_column(ForeignKey("permisos.id"), primary_key=True)

    rol: Mapped["Rol"] = relationship(back_populates="permisos")
    permiso: Mapped["Permiso"] = relationship(back_populates="roles")


class Sesion(Base):
    """Sesión activa de un usuario administrativo autenticado (JWT)."""

    __tablename__ = "sesiones"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    token_jti: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expira_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    activa: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    usuario: Mapped["Usuario"] = relationship(back_populates="sesiones")


class Bitacora(Base):
    """Registro de auditoría de alto nivel: qué usuario hizo qué acción
    sobre qué entidad (creación/edición/baja de evaluados, empresas,
    evaluaciones, etc.)."""

    __tablename__ = "bitacora"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    accion: Mapped[str] = mapped_column(String(100), nullable=False)
    entidad: Mapped[str] = mapped_column(String(100), nullable=False)
    entidad_id: Mapped[int | None] = mapped_column(nullable=True)
    detalle: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class TokenRecuperacion(Base):
    """Token de recuperación/restablecimiento de contraseña de un usuario."""

    __tablename__ = "tokens_recuperacion"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expira_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    usado: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class HistorialLogin(Base):
    """Registro de cada intento de inicio de sesión (exitoso o fallido),
    tanto de usuarios administrativos como de accesos temporales de evaluados."""

    __tablename__ = "historial_login"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    usuario_temporal_id: Mapped[int | None] = mapped_column(
        ForeignKey("usuarios_temporales.id"), nullable=True
    )
    exitoso: Mapped[bool] = mapped_column(Boolean, nullable=False)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class HistorialAccion(Base):
    """Registro detallado de acciones realizadas dentro de una sesión
    (más granular que la bitácora; útil para trazabilidad fina, p. ej.
    durante la aplicación de una evaluación)."""

    __tablename__ = "historial_acciones"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    usuario_temporal_id: Mapped[int | None] = mapped_column(
        ForeignKey("usuarios_temporales.id"), nullable=True
    )
    accion: Mapped[str] = mapped_column(String(100), nullable=False)
    detalle: Mapped[str | None] = mapped_column(String(500), nullable=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
