export interface CatalogoRef {
  id: number
  codigo: string
  nombre: string
}

export interface EmpresaRef {
  id: number
  nombre_comercial: string
}

export interface Candidato {
  id: number
  nombre: string
  apellidos: string
  correo: string
  puesto: string | null
  fecha_nacimiento: string | null
  activo: boolean
  creado_en: string
  empresa: EmpresaRef | null
  sexo: CatalogoRef | null
  escolaridad: CatalogoRef | null
  estatus: CatalogoRef | null
}

export interface CandidatoCreate {
  nombre: string
  apellidos: string
  correo: string
  puesto?: string | null
  fecha_nacimiento?: string | null
  empresa_id?: number | null
  sexo_codigo?: string | null
  escolaridad_codigo?: string | null
  estatus_candidato_codigo?: string | null
}

export type CandidatoUpdate = Partial<CandidatoCreate>

export interface EvaluacionAsignada {
  asignacion_id: number
  prueba: string
  categoria: string
  estatus: string
  fecha_asignacion: string
  fecha_inicio: string | null
  fecha_finalizacion: string | null
  progreso_porcentaje: number
  tiempo_disponible_minutos: number | null
  resultado_disponible: boolean
}

export interface ExpedienteCandidato {
  candidato: Candidato
  evaluaciones: EvaluacionAsignada[]
}
