import { createContext, useContext, useMemo, useState, type ReactNode } from 'react'
import { portalService, portalTokenStore } from '../services/portalService'

const NOMBRE_KEY = 'autotest_dprh_portal_nombre'

interface PortalAuthContextValue {
  autenticado: boolean
  nombre: string | null
  login: (usuario: string, password: string) => Promise<void>
  logout: () => Promise<void>
}

const PortalAuthContext = createContext<PortalAuthContextValue | undefined>(undefined)

export function PortalAuthProvider({ children }: { children: ReactNode }) {
  const [autenticado, setAutenticado] = useState<boolean>(() => portalTokenStore.get() !== null)
  const [nombre, setNombre] = useState<string | null>(() => sessionStorage.getItem(NOMBRE_KEY))

  const login = async (usuario: string, password: string) => {
    const tokens = await portalService.login({ usuario, password })
    portalTokenStore.set(tokens.access_token)
    sessionStorage.setItem(NOMBRE_KEY, tokens.candidato_nombre)
    setNombre(tokens.candidato_nombre)
    setAutenticado(true)
  }

  const logout = async () => {
    try {
      await portalService.logout()
    } catch {
      // Si el servidor ya no reconoce la sesión, igual se cierra localmente.
    }
    portalTokenStore.clear()
    sessionStorage.removeItem(NOMBRE_KEY)
    setNombre(null)
    setAutenticado(false)
  }

  const value = useMemo(() => ({ autenticado, nombre, login, logout }), [autenticado, nombre])

  return <PortalAuthContext.Provider value={value}>{children}</PortalAuthContext.Provider>
}

export function usePortalAuth(): PortalAuthContextValue {
  const context = useContext(PortalAuthContext)
  if (!context) {
    throw new Error('usePortalAuth debe usarse dentro de un <PortalAuthProvider>')
  }
  return context
}
