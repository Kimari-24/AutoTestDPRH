export interface LoginRequest {
  correo: string
  password: string
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_at: string
}

export interface UsuarioMe {
  id: number
  nombre: string
  apellidos: string
  correo: string
  roles: string[]
  activo: boolean
}
