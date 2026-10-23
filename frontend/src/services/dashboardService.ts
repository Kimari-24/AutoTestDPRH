import { apiClient } from './apiClient'
import type { DashboardResumen } from '../types/dashboard'

export const dashboardService = {
  obtenerResumen: () =>
    apiClient.get<DashboardResumen>('/dashboard/resumen').then((r) => r.data),
}
