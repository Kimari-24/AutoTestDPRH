import { apiClient } from './apiClient'
import type { Empresa, EmpresaCreate, EmpresaUpdate } from '../types/empresa'

export const empresaService = {
  listar: (params?: { buscar?: string; solo_activas?: boolean }) =>
    apiClient.get<Empresa[]>('/empresas', { params }).then((r) => r.data),

  obtener: (id: number) => apiClient.get<Empresa>(`/empresas/${id}`).then((r) => r.data),

  crear: (data: EmpresaCreate) =>
    apiClient.post<Empresa>('/empresas', data).then((r) => r.data),

  actualizar: (id: number, data: EmpresaUpdate) =>
    apiClient.put<Empresa>(`/empresas/${id}`, data).then((r) => r.data),

  desactivar: (id: number) =>
    apiClient.delete<Empresa>(`/empresas/${id}`).then((r) => r.data),
}
