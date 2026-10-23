from datetime import datetime, timezone

from pydantic import BaseModel, Field, field_validator


class CrearAccesoTemporalRequest(BaseModel):
    horas_vigencia: int = Field(default=48, ge=1, le=24 * 30, description="Horas hasta que expire el acceso.")


class AccesoTemporalCreadoOut(BaseModel):
    """Se devuelve UNA sola vez, al crear el acceso: es la única
    oportunidad de ver la contraseña temporal en claro (nunca se
    almacena ni se puede recuperar después — sección 8)."""

    id: int
    usuario: str
    password_temporal: str
    expira_en: datetime


class AccesoTemporalOut(BaseModel):
    id: int
    usuario: str
    creado_en: datetime
    expira_en: datetime
    intentos_fallidos: int
    ultimo_acceso: datetime | None
    sesion_activa: bool
    revocado: bool


class AsignarEvaluacionRequest(BaseModel):
    prueba_id: int
    fecha_limite: datetime | None = None

    @field_validator("fecha_limite", mode="after")
    @classmethod
    def _fecha_limite_en_el_futuro(cls, valor):
        """Una fecha límite ya vencida dejaría la evaluación asignada
        pero imposible de aplicar (BUG-15 de QA)."""
        if valor is None:
            return valor
        if valor.tzinfo is None:
            valor = valor.replace(tzinfo=timezone.utc)
        if valor <= datetime.now(timezone.utc):
            raise ValueError("La fecha límite debe estar en el futuro.")
        return valor


class AsignacionOut(BaseModel):
    id: int
    prueba_id: int
    prueba_nombre: str
    estatus: str
    fecha_asignacion: datetime
    fecha_limite: datetime | None
