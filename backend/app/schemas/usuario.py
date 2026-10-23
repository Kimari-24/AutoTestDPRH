"""Schemas de entrada/salida del módulo de usuarios administrativos.

Nota: estos schemas son para `Usuario` (personal administrativo,
rol ADMINISTRADOR y, a futuro, EMPRESA). Los evaluados NO usan este
módulo — se gestionan mediante `UsuarioTemporal` (Fase 4).
"""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.base import normalizar_correo


class RolOut(BaseModel):
    id: int
    codigo: str
    nombre: str

    model_config = {"from_attributes": True}


class UsuarioBase(BaseModel):
    nombre: str = Field(min_length=1, max_length=150)
    apellidos: str = Field(min_length=1, max_length=150)
    correo: EmailStr

    @field_validator("correo", mode="after")
    @classmethod
    def _correo_en_minusculas(cls, valor):
        return normalizar_correo(valor)


class UsuarioCreate(UsuarioBase):
    """Datos para crear un usuario administrativo."""

    password: str = Field(min_length=8, max_length=72)
    roles: list[str] = Field(
        default_factory=list,
        description="Códigos de rol a asignar, p. ej. ['ADMINISTRADOR'].",
    )

    @field_validator("password")
    @classmethod
    def password_debe_ser_razonable(cls, value: str) -> str:
        if value.strip() != value:
            raise ValueError("La contraseña no debe iniciar ni terminar con espacios.")
        return value


class UsuarioUpdate(BaseModel):
    """Datos para actualizar un usuario administrativo (todos opcionales)."""

    nombre: str | None = Field(default=None, min_length=1, max_length=150)
    apellidos: str | None = Field(default=None, min_length=1, max_length=150)
    correo: EmailStr | None = None
    roles: list[str] | None = None

    @field_validator("correo", mode="after")
    @classmethod
    def _correo_en_minusculas(cls, valor):
        return normalizar_correo(valor)


class CambiarPasswordRequest(BaseModel):
    password_actual: str
    password_nueva: str = Field(min_length=8, max_length=72)


class UsuarioOut(UsuarioBase):
    id: int
    activo: bool
    roles: list[str] = Field(default_factory=list)
    creado_en: datetime

    model_config = {"from_attributes": True}
