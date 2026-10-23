export interface TipoPreguntaRef {
  id: number
  codigo: string
  nombre: string
}

export interface Opcion {
  id: number
  texto: string | null
  imagen_url: string | null
  valor: string | null
  orden: number
}

export interface OpcionCreate {
  texto?: string | null
  imagen_url?: string | null
  valor?: string | null
  orden?: number
}

export interface Pregunta {
  id: number
  version_prueba_id: number
  tipo_pregunta: TipoPreguntaRef
  enunciado: string
  imagen_url: string | null
  configuracion: Record<string, unknown> | null
  orden: number
  activa: boolean
  opciones: Opcion[]
}

export interface PreguntaCreate {
  tipo_pregunta_codigo: string
  enunciado: string
  imagen_url?: string | null
  orden?: number
  opciones?: OpcionCreate[]
}
