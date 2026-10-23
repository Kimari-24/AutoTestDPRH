import type { Candidato } from './candidato'

export interface DashboardResumen {
  total_evaluados: number
  total_evaluaciones_disponibles: number
  total_resultados: number
  evaluaciones_pendientes: number
  evaluaciones_en_proceso: number
  evaluaciones_completadas: number
  evaluados_recientes: Candidato[]
}
