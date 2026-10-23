import { Navigate, Outlet } from 'react-router-dom'
import { usePortalAuth } from '../contexts/PortalAuthContext'

/**
 * Estructura del portal del evaluado: intencionalmente mínima (sin
 * sidebar ni navegación administrativa), y protegida — si no hay
 * sesión de evaluado, redirige al login del portal.
 */
export default function PortalLayout() {
  const { autenticado, nombre, logout } = usePortalAuth()

  if (!autenticado) {
    return <Navigate to="/portal/login" replace />
  }

  return (
    <div className="min-h-screen bg-dprh-bg">
      <header className="h-16 bg-dprh-guinda text-white flex items-center justify-between px-6">
        <div className="font-semibold">AutoTest DPRH</div>
        <div className="flex items-center gap-4 text-sm">
          <span className="text-white/80">{nombre}</span>
          <button onClick={logout} className="underline hover:text-white">
            Salir
          </button>
        </div>
      </header>
      <main className="max-w-3xl mx-auto p-6">
        <Outlet />
      </main>
    </div>
  )
}
