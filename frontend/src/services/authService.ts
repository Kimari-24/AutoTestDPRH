import { apiClient } from './apiClient'
import type { LoginRequest, TokenResponse, UsuarioMe } from '../types/auth'

export const authService = {
  login: (data: LoginRequest) =>
    apiClient.post<TokenResponse>('/auth/login', data).then((r) => r.data),

  refresh: (refresh_token: string) =>
    apiClient.post<TokenResponse>('/auth/refresh', { refresh_token }).then((r) => r.data),

  logout: (refresh_token: string) =>
    apiClient.post('/auth/logout', { refresh_token }),

  me: () => apiClient.get<UsuarioMe>('/auth/me').then((r) => r.data),
}
