import { apiClient } from './apiClient'
import type { Candidato, CandidatoCreate, CandidatoUpdate, ExpedienteCandidato } from '../types/candidato'

export const evaluadoService = {
  listar: (params?: {
    buscar?: string
    empresa_id?: number
    estatus_candidato_id?: number
    solo_activos?: boolean
  }) => apiClient.get<Candidato[]>('/evaluados', { params }).then((r) => r.data),

  obtener: (id: number) => apiClient.get<Candidato>(`/evaluados/${id}`).then((r) => r.data),

  obtenerExpediente: (id: number) =>
    apiClient.get<ExpedienteCandidato>(`/evaluados/${id}/expediente`).then((r) => r.data),

  crear: (data: CandidatoCreate) =>
    apiClient.post<Candidato>('/evaluados', data).then((r) => r.data),

  actualizar: (id: number, data: CandidatoUpdate) =>
    apiClient.put<Candidato>(`/evaluados/${id}`, data).then((r) => r.data),

  desactivar: (id: number) =>
    apiClient.delete<Candidato>(`/evaluados/${id}`).then((r) => r.data),
}
