export interface LoginEvaluadoRequest {
  usuario: string
  password: string
}

export interface TokenEvaluado {
  access_token: string
  token_type: string
  expires_at: string
  candidato_nombre: string
}

export interface MiEvaluacion {
  asignacion_id: number
  prueba_nombre: string
  estatus: string
  fecha_asignacion: string
  fecha_limite: string | null
  tiempo_limite_minutos: number | null
  puede_iniciar: boolean
}

export interface OpcionPortal {
  id: number
  texto: string | null
  imagen_url: string | null
  orden: number
}

export interface PreguntaPortal {
  id: number
  tipo_pregunta_codigo: string
  enunciado: string
  imagen_url: string | null
  orden: number
  opciones: OpcionPortal[]
  respuesta_actual: string | null
}

export interface IniciarSesion {
  sesion_id: number
  estatus: string
  tiempo_restante_segundos: number | null
}

export interface ProgresoSesion {
  total_preguntas: number
  preguntas_respondidas: number
  porcentaje: number
  tiempo_restante_segundos: number | null
  estatus: string
}

export interface GuardarRespuestaRequest {
  opcion_id?: number | null
  valor?: string | null
}
