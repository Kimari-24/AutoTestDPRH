import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { authTokenStore } from '../services/apiClient'
import { authService } from '../services/authService'
import type { TokenResponse, UsuarioMe } from '../types/auth'

const REFRESH_TOKEN_KEY = 'autotest_dprh_refresh_token'

interface AuthContextValue {
  usuario: UsuarioMe | null
  cargando: boolean
  login: (correo: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

/**
 * Con rotación de refresh tokens (cada refresh invalida el token usado),
 * la restauración de sesión al cargar la app debe ejecutarse UNA sola
 * vez. En desarrollo React StrictMode corre los efectos dos veces: sin
 * esta promesa compartida, la segunda llamada usaría un token ya
 * rotado, fallaría, y borraría la sesión recién restaurada.
 */
let restauracionDeSesion: Promise<UsuarioMe | null> | null = null

function restaurarSesion(): Promise<UsuarioMe | null> {
  if (restauracionDeSesion) return restauracionDeSesion

  const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY)
  if (!refreshToken) return Promise.resolve(null)

  restauracionDeSesion = authService
    .refresh(refreshToken)
    .then(async (tokens) => {
      authTokenStore.accessToken = tokens.access_token
      localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token)
      return authService.me()
    })
    .catch(() => {
      localStorage.removeItem(REFRESH_TOKEN_KEY)
      return null
    })
    .finally(() => {
      // Se libera para poder restaurar de nuevo tras un logout/login.
      setTimeout(() => {
        restauracionDeSesion = null
      }, 0)
    })
  return restauracionDeSesion
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [usuario, setUsuario] = useState<UsuarioMe | null>(null)
  const [cargando, setCargando] = useState(true)

  const limpiarSesion = () => {
    authTokenStore.accessToken = null
    localStorage.removeItem(REFRESH_TOKEN_KEY)
    setUsuario(null)
  }

  useEffect(() => {
    authTokenStore.getRefreshToken = () => localStorage.getItem(REFRESH_TOKEN_KEY)
    authTokenStore.onTokensRefreshed = (tokens: TokenResponse) => {
      localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token)
    }
    authTokenStore.onSessionExpired = () => {
      limpiarSesion()
    }
  }, [])

  useEffect(() => {
    // Al cargar la app, si hay un refresh token guardado, se intenta
    // restablecer la sesion sin pedir credenciales de nuevo.
    restaurarSesion()
      .then((me) => {
        if (me) setUsuario(me)
      })
      .finally(() => setCargando(false))
  }, [])

  const login = async (correo: string, password: string) => {
    const tokens = await authService.login({ correo, password })
    authTokenStore.accessToken = tokens.access_token
    localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token)
    const me = await authService.me()
    setUsuario(me)
  }

  const logout = () => {
    const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY)
    if (refreshToken) {
      authService.logout(refreshToken).catch(() => {
        // Si la revocacion en el servidor falla (p. ej. ya expiro),
        // igual se cierra la sesion localmente.
      })
    }
    limpiarSesion()
  }

  const value = useMemo(() => ({ usuario, cargando, login, logout }), [usuario, cargando])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth debe usarse dentro de un <AuthProvider>')
  }
  return context
}
