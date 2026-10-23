import axios from 'axios'
import type {
  GuardarRespuestaRequest,
  IniciarSesion,
  LoginEvaluadoRequest,
  MiEvaluacion,
  PreguntaPortal,
  ProgresoSesion,
  TokenEvaluado,
} from '../types/portal'

const PORTAL_TOKEN_KEY = 'autotest_dprh_portal_token'

/**
 * Cliente HTTP del portal del evaluado. Totalmente independiente de
 * `apiClient` (administrador): usa su propio token, guardado en
 * sessionStorage (se pierde al cerrar la pestaña), y nunca comparte
 * interceptores ni refresh con la sesión administrativa.
 */
export const portalClient = axios.create({
  baseURL: '/api/portal',
  headers: { 'Content-Type': 'application/json' },
})

export const portalTokenStore = {
  get: () => sessionStorage.getItem(PORTAL_TOKEN_KEY),
  set: (token: string) => sessionStorage.setItem(PORTAL_TOKEN_KEY, token),
  clear: () => sessionStorage.removeItem(PORTAL_TOKEN_KEY),
}

portalClient.interceptors.request.use((config) => {
  const token = portalTokenStore.get()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export const portalService = {
  login: (data: LoginEvaluadoRequest) =>
    portalClient.post<TokenEvaluado>('/login', data).then((r) => r.data),

  logout: () => portalClient.post('/logout'),

  misEvaluaciones: () =>
    portalClient.get<MiEvaluacion[]>('/mis-evaluaciones').then((r) => r.data),

  iniciar: (asignacionId: number) =>
    portalClient.post<IniciarSesion>(`/evaluaciones/${asignacionId}/iniciar`).then((r) => r.data),

  preguntas: (sesionId: number) =>
    portalClient.get<PreguntaPortal[]>(`/sesiones/${sesionId}/preguntas`).then((r) => r.data),

  guardarRespuesta: (sesionId: number, preguntaId: number, data: GuardarRespuestaRequest) =>
    portalClient.put(`/sesiones/${sesionId}/preguntas/${preguntaId}/respuesta`, data),

  progreso: (sesionId: number) =>
    portalClient.get<ProgresoSesion>(`/sesiones/${sesionId}/progreso`).then((r) => r.data),

  finalizar: (sesionId: number) =>
    portalClient.post<ProgresoSesion>(`/sesiones/${sesionId}/finalizar`).then((r) => r.data),
}
