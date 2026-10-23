from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.base import UpdateSinNulos


class EmpresaBase(BaseModel):
    nombre_comercial: str = Field(min_length=1, max_length=200)
    razon_social: str | None = Field(default=None, max_length=200)
    correo_contacto: EmailStr | None = None
    telefono_contacto: str | None = Field(default=None, max_length=50)
    direccion: str | None = Field(default=None, max_length=300)


class EmpresaCreate(EmpresaBase):
    pass


class EmpresaUpdate(UpdateSinNulos):
    campos_no_nulos = ("nombre_comercial",)

    nombre_comercial: str | None = Field(default=None, min_length=1, max_length=200)
    razon_social: str | None = Field(default=None, max_length=200)
    correo_contacto: EmailStr | None = None
    telefono_contacto: str | None = Field(default=None, max_length=50)
    direccion: str | None = Field(default=None, max_length=300)


class EmpresaOut(EmpresaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    activo: bool
    creado_en: datetime
    total_candidatos: int = 0
