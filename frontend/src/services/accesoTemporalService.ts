import { apiClient } from './apiClient'
import type { AccesoTemporal, AccesoTemporalCreado, Asignacion } from '../types/accesoTemporal'

export const accesoTemporalService = {
  listarAccesos: (candidatoId: number) =>
    apiClient
      .get<AccesoTemporal[]>(`/evaluados/${candidatoId}/accesos-temporales`)
      .then((r) => r.data),

  crearAcceso: (candidatoId: number, horas_vigencia = 48) =>
    apiClient
      .post<AccesoTemporalCreado>(`/evaluados/${candidatoId}/accesos-temporales`, { horas_vigencia })
      .then((r) => r.data),

  revocarAcceso: (accesoId: number) =>
    apiClient
      .post<AccesoTemporal>(`/evaluados/accesos-temporales/${accesoId}/revocar`)
      .then((r) => r.data),

  listarAsignaciones: (candidatoId: number) =>
    apiClient.get<Asignacion[]>(`/evaluados/${candidatoId}/asignaciones`).then((r) => r.data),

  asignarEvaluacion: (candidatoId: number, pruebaId: number, fecha_limite?: string | null) =>
    apiClient
      .post<Asignacion>(`/evaluados/${candidatoId}/asignaciones`, {
        prueba_id: pruebaId,
        fecha_limite: fecha_limite ?? null,
      })
      .then((r) => r.data),
}
