from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.base import UpdateSinNulos


class CategoriaPruebaCreate(BaseModel):
    codigo: str = Field(min_length=1, max_length=50)
    nombre: str = Field(min_length=1, max_length=150)
    descripcion: str | None = Field(default=None, max_length=255)
    orden: int = 0


class CategoriaPruebaOut(BaseModel):
    id: int
    codigo: str
    nombre: str
    descripcion: str | None
    orden: int


class PruebaCreate(BaseModel):
    categoria_codigo: str
    codigo: str = Field(min_length=1, max_length=50)
    nombre: str = Field(min_length=1, max_length=150)
    descripcion: str | None = None
    instrucciones: str | None = None
    tiempo_limite_minutos: int | None = Field(default=None, ge=1)
    intentos_permitidos: int = Field(default=1, ge=1)


class PruebaUpdate(UpdateSinNulos):
    campos_no_nulos = ("nombre", "intentos_permitidos")

    nombre: str | None = Field(default=None, min_length=1, max_length=150)
    descripcion: str | None = None
    instrucciones: str | None = None
    tiempo_limite_minutos: int | None = Field(default=None, ge=1)
    intentos_permitidos: int | None = Field(default=None, ge=1)


class PruebaOut(BaseModel):
    id: int
    codigo: str
    nombre: str
    descripcion: str | None
    instrucciones: str | None
    tiempo_limite_minutos: int | None
    intentos_permitidos: int
    activa: bool
    categoria: CategoriaPruebaOut
    total_preguntas_activas: int = 0
    creado_en: datetime


class VersionPruebaCreate(BaseModel):
    notas: str | None = Field(default=None, max_length=500)


class VersionPruebaOut(BaseModel):
    id: int
    prueba_id: int
    numero_version: int
    activa: bool
    notas: str | None
    creado_en: datetime
    total_preguntas: int = 0
