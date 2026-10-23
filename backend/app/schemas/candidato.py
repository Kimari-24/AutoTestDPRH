from datetime import date, datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.base import normalizar_correo


class CatalogoRef(BaseModel):
    """Referencia liviana a un valor de catálogo (id + código + nombre)."""

    id: int
    codigo: str
    nombre: str


class EmpresaRef(BaseModel):
    id: int
    nombre_comercial: str


class CandidatoCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=150)
    apellidos: str = Field(min_length=1, max_length=150)
    correo: EmailStr
    puesto: str | None = Field(default=None, max_length=150)
    fecha_nacimiento: date | None = None
    empresa_id: int | None = None
    sexo_codigo: str | None = None
    escolaridad_codigo: str | None = None
    estatus_candidato_codigo: str | None = None

    @field_validator("correo", mode="after")
    @classmethod
    def _correo_en_minusculas(cls, valor):
        return normalizar_correo(valor)

    @field_validator("fecha_nacimiento", mode="after")
    @classmethod
    def _fecha_nacimiento_no_futura(cls, valor):
        """Una fecha de nacimiento en el futuro es imposible (BUG-15 de QA)."""
        if valor is not None and valor > date.today():
            raise ValueError("La fecha de nacimiento no puede ser futura.")
        return valor


class CandidatoUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=150)
    apellidos: str | None = Field(default=None, min_length=1, max_length=150)
    correo: EmailStr | None = None
    puesto: str | None = Field(default=None, max_length=150)
    fecha_nacimiento: date | None = None
    empresa_id: int | None = None
    sexo_codigo: str | None = None
    escolaridad_codigo: str | None = None
    estatus_candidato_codigo: str | None = None

    @field_validator("correo", mode="after")
    @classmethod
    def _correo_en_minusculas(cls, valor):
        return normalizar_correo(valor)

    @field_validator("fecha_nacimiento", mode="after")
    @classmethod
    def _fecha_nacimiento_no_futura(cls, valor):
        """Una fecha de nacimiento en el futuro es imposible (BUG-15 de QA)."""
        if valor is not None and valor > date.today():
            raise ValueError("La fecha de nacimiento no puede ser futura.")
        return valor


class CandidatoOut(BaseModel):
    id: int
    nombre: str
    apellidos: str
    correo: str
    puesto: str | None
    fecha_nacimiento: date | None
    activo: bool
    creado_en: datetime
    empresa: EmpresaRef | None
    sexo: CatalogoRef | None
    escolaridad: CatalogoRef | None
    estatus: CatalogoRef | None


class EvaluacionAsignadaOut(BaseModel):
    """Una fila del bloque "Evaluaciones asignadas" del expediente (sección 17)."""

    asignacion_id: int
    prueba: str
    categoria: str
    estatus: str
    fecha_asignacion: datetime
    fecha_inicio: datetime | None
    fecha_finalizacion: datetime | None
    progreso_porcentaje: int
    tiempo_disponible_minutos: int | None
    resultado_disponible: bool


class ExpedienteCandidatoOut(BaseModel):
    """Datos personales + evaluaciones asignadas (sección 17 de los requisitos)."""

    candidato: CandidatoOut
    evaluaciones: list[EvaluacionAsignadaOut]
