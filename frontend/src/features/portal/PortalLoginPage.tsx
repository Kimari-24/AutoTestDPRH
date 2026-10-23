import { useState, type FormEvent } from 'react'
import { Navigate } from 'react-router-dom'
import { usePortalAuth } from '../../contexts/PortalAuthContext'

export default function PortalLoginPage() {
  const { autenticado, login } = usePortalAuth()
  const [usuario, setUsuario] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)

  if (autenticado) {
    return <Navigate to="/portal" replace />
  }

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setError(null)
    setEnviando(true)
    try {
      await login(usuario, password)
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } }).response?.status
      if (status === 403) {
        setError('Tu acceso está bloqueado, expiró o fue revocado. Contacta a tu reclutador.')
      } else {
        setError('Usuario o contraseña incorrectos.')
      }
    } finally {
      setEnviando(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-dprh-bg px-4">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-sm rounded-xl border border-dprh-gray bg-white shadow-sm p-8"
      >
        <div className="mb-6 text-center">
          <div className="mx-auto mb-3 h-12 w-12 rounded-lg bg-dprh-guinda flex items-center justify-center text-white font-bold text-lg">
            DPRH
          </div>
          <h1 className="text-xl font-semibold text-gray-800">Portal de evaluaciones</h1>
          <p className="text-sm text-gray-500">Ingresa con las credenciales que te enviaron</p>
        </div>

        <label className="block text-sm font-medium text-gray-700 mb-1" htmlFor="usuario">
          Usuario
        </label>
        <input
          id="usuario"
          required
          autoComplete="username"
          value={usuario}
          onChange={(e) => setUsuario(e.target.value)}
          className="campo mb-4"
        />

        <label className="block text-sm font-medium text-gray-700 mb-1" htmlFor="password">
          Contraseña
        </label>
        <input
          id="password"
          type="password"
          required
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="campo mb-4"
        />

        {error && <p className="mb-4 text-sm text-red-600">{error}</p>}

        <button
          type="submit"
          disabled={enviando}
          className="w-full rounded-lg bg-dprh-guinda text-white text-sm font-medium py-2.5 hover:bg-dprh-guinda-dark transition-colors disabled:opacity-60"
        >
          {enviando ? 'Ingresando…' : 'Ingresar'}
        </button>
      </form>
    </div>
  )
}
