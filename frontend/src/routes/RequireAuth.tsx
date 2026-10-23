import { Navigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

export default function RequireAuth({ children }: { children: React.ReactNode }) {
  const { usuario, cargando } = useAuth()

  if (cargando) {
    return (
      <div className="min-h-screen flex items-center justify-center text-gray-500 text-sm">
        Cargando…
      </div>
    )
  }

  if (!usuario) {
    return <Navigate to="/login" replace />
  }

  return <>{children}</>
}
