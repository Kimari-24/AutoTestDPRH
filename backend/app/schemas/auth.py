"""Schemas de entrada/salida del módulo de autenticación."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.base import normalizar_correo


class LoginRequest(BaseModel):
    """Cuerpo de la petición de login (JSON, no form-data)."""

    correo: EmailStr
    password: str = Field(min_length=1)

    @field_validator("correo", mode="after")
    @classmethod
    def _correo_en_minusculas(cls, valor):
        return normalizar_correo(valor)


class TokenResponse(BaseModel):
    """Respuesta de login/refresh: par de tokens JWT."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_at: datetime


class RefreshRequest(BaseModel):
    """Cuerpo de la petición para renovar el access token."""

    refresh_token: str


class UsuarioMe(BaseModel):
    """Datos del usuario autenticado (endpoint /auth/me)."""

    id: int
    nombre: str
    apellidos: str
    correo: EmailStr
    roles: list[str] = Field(default_factory=list)
    activo: bool

    model_config = {"from_attributes": True}
