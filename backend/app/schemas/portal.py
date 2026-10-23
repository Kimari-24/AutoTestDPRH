from datetime import datetime

from pydantic import BaseModel, Field


class LoginEvaluadoRequest(BaseModel):
    usuario: str
    password: str


class TokenEvaluadoResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    candidato_nombre: str


class MiEvaluacionOut(BaseModel):
    """Una evaluación asignada, tal como la ve el propio evaluado
    (sección 6, paso 8: "el evaluado ve únicamente sus evaluaciones")."""

    asignacion_id: int
    prueba_nombre: str
    estatus: str
    fecha_asignacion: datetime
    fecha_limite: datetime | None
    tiempo_limite_minutos: int | None
    puede_iniciar: bool


class OpcionPortalOut(BaseModel):
    """Vista de una opción SIN el campo `valor`: ese campo puede
    contener la clave o el peso usado por el motor de calificación,
    y nunca debe llegar al evaluado mientras responde."""

    id: int
    texto: str | None
    imagen_url: str | None
    orden: int


class PreguntaPortalOut(BaseModel):
    """Vista de una pregunta SIN el campo `configuracion` (ahí vive la
    clave correcta, los pesos, etc. — nunca se expone al evaluado)."""

    id: int
    tipo_pregunta_codigo: str
    enunciado: str
    imagen_url: str | None
    orden: int
    opciones: list[OpcionPortalOut]
    respuesta_actual: str | None = None


class GuardarRespuestaRequest(BaseModel):
    opcion_id: int | None = None
    valor: str | None = Field(default=None, max_length=4000)


class ProgresoSesionOut(BaseModel):
    total_preguntas: int
    preguntas_respondidas: int
    porcentaje: int
    tiempo_restante_segundos: int | None
    estatus: str


class IniciarSesionOut(BaseModel):
    sesion_id: int
    estatus: str
    tiempo_restante_segundos: int | None
