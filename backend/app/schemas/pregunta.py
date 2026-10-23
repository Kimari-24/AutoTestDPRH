from typing import Any

from pydantic import BaseModel, Field

from app.schemas.base import UpdateSinNulos


class OpcionCreate(BaseModel):
    texto: str | None = Field(default=None, max_length=2000)
    imagen_url: str | None = Field(default=None, max_length=500)
    valor: str | None = Field(default=None, max_length=100)
    orden: int = 0


class OpcionUpdate(UpdateSinNulos):
    campos_no_nulos = ("orden",)

    texto: str | None = Field(default=None, max_length=2000)
    imagen_url: str | None = Field(default=None, max_length=500)
    valor: str | None = Field(default=None, max_length=100)
    orden: int | None = None


class OpcionOut(BaseModel):
    id: int
    texto: str | None
    imagen_url: str | None
    valor: str | None
    orden: int


class TipoPreguntaRef(BaseModel):
    id: int
    codigo: str
    nombre: str


class PreguntaCreate(BaseModel):
    tipo_pregunta_codigo: str
    enunciado: str = Field(min_length=1)
    imagen_url: str | None = Field(default=None, max_length=500)
    configuracion: dict[str, Any] | None = None
    orden: int = 0
    opciones: list[OpcionCreate] = Field(default_factory=list)


class PreguntaUpdate(BaseModel):
    tipo_pregunta_codigo: str | None = None
    enunciado: str | None = Field(default=None, min_length=1)
    imagen_url: str | None = Field(default=None, max_length=500)
    configuracion: dict[str, Any] | None = None
    orden: int | None = None


class PreguntaOut(BaseModel):
    id: int
    version_prueba_id: int
    tipo_pregunta: TipoPreguntaRef
    enunciado: str
    imagen_url: str | None
    configuracion: dict[str, Any] | None
    orden: int
    activa: bool
    opciones: list[OpcionOut]
