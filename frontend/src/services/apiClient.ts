import axios, { type InternalAxiosRequestConfig } from 'axios'
import type { TokenResponse } from '../types/auth'

/**
 * Cliente HTTP centralizado para AutoTest DPRH.
 *
 * Todas las llamadas al backend deben pasar por esta instancia, para
 * mantener configuracion (baseURL, headers, interceptores de auth)
 * en un solo lugar. En desarrollo, Vite hace proxy de /api hacia
 * el backend FastAPI (ver vite.config.ts).
 */
export const apiClient = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

/**
 * Almacen en memoria de los tokens de sesion, mas un par de callbacks
 * que AuthContext registra para poder persistir/leer el refresh token
 * y reaccionar cuando la sesion deja de ser valida. Vive aqui (y no en
 * el contexto) para evitar una dependencia circular entre el cliente
 * HTTP y el contexto de React que lo usa.
 */
interface AuthTokenStore {
  accessToken: string | null
  getRefreshToken: () => string | null
  onTokensRefreshed: (tokens: TokenResponse) => void
  onSessionExpired: () => void
}

export const authTokenStore: AuthTokenStore = {
  accessToken: null,
  getRefreshToken: () => null,
  onTokensRefreshed: () => {},
  onSessionExpired: () => {},
}

apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  if (authTokenStore.accessToken && !config.headers.Authorization) {
    config.headers.Authorization = `Bearer ${authTokenStore.accessToken}`
  }
  return config
})

// Evita disparar varios refresh en paralelo si varias peticiones
// reciben 401 al mismo tiempo: todas esperan la misma promesa.
let refreshEnCurso: Promise<string | null> | null = null

async function refrescarAccessToken(): Promise<string | null> {
  const refreshToken = authTokenStore.getRefreshToken()
  if (!refreshToken) return null

  try {
    const response = await axios.post<TokenResponse>('/api/auth/refresh', {
      refresh_token: refreshToken,
    })
    authTokenStore.accessToken = response.data.access_token
    authTokenStore.onTokensRefreshed(response.data)
    return response.data.access_token
  } catch {
    return null
  }
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config as (InternalAxiosRequestConfig & { _retry?: boolean }) | undefined
    const esLogin = originalRequest?.url?.includes('/auth/login')
    const esRefresh = originalRequest?.url?.includes('/auth/refresh')

    if (
      error.response?.status === 401 &&
      originalRequest &&
      !originalRequest._retry &&
      !esLogin &&
      !esRefresh
    ) {
      originalRequest._retry = true

      if (!refreshEnCurso) {
        refreshEnCurso = refrescarAccessToken().finally(() => {
          refreshEnCurso = null
        })
      }
      const nuevoToken = await refreshEnCurso

      if (nuevoToken) {
        originalRequest.headers.Authorization = `Bearer ${nuevoToken}`
        return apiClient(originalRequest)
      }

      authTokenStore.onSessionExpired()
    }

    return Promise.reject(error)
  },
)
