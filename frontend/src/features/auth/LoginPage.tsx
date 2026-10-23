import { useState, type FormEvent } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'

export default function LoginPage() {
  const { usuario, cargando, login } = useAuth()
  const [correo, setCorreo] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)

  if (!cargando && usuario) {
    return <Navigate to="/" replace />
  }

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setError(null)
    setEnviando(true)
    try {
      await login(correo, password)
    } catch {
      setError('Correo o contraseña incorrectos.')
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
          <h1 className="text-xl font-semibold text-gray-800">AutoTest DPRH</h1>
          <p className="text-sm text-gray-500">Panel administrativo</p>
        </div>

        <label className="block text-sm font-medium text-gray-700 mb-1" htmlFor="correo">
          Correo
        </label>
        <input
          id="correo"
          type="email"
          required
          autoComplete="username"
          value={correo}
          onChange={(e) => setCorreo(e.target.value)}
          className="w-full mb-4 rounded-lg border border-dprh-gray px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-dprh-azul"
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
          className="w-full mb-4 rounded-lg border border-dprh-gray px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-dprh-azul"
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
