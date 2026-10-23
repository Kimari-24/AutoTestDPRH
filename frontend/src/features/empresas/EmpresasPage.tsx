import { useEffect, useState, type FormEvent } from 'react'
import { empresaService } from '../../services/empresaService'
import type { Empresa } from '../../types/empresa'

export default function EmpresasPage() {
  const [empresas, setEmpresas] = useState<Empresa[]>([])
  const [buscar, setBuscar] = useState('')
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [mostrarForm, setMostrarForm] = useState(false)

  const cargar = (filtro?: string) => {
    setCargando(true)
    empresaService
      .listar(filtro ? { buscar: filtro } : undefined)
      .then(setEmpresas)
      .catch(() => setError('No se pudieron cargar las empresas.'))
      .finally(() => setCargando(false))
  }

  useEffect(() => {
    cargar()
  }, [])

  const handleBuscar = (event: FormEvent) => {
    event.preventDefault()
    cargar(buscar || undefined)
  }

  const handleDesactivar = async (id: number) => {
    await empresaService.desactivar(id)
    cargar(buscar || undefined)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-800">Empresas</h1>
          <p className="text-sm text-gray-500">Clientes de DPRH cuyos evaluados se administran aquí</p>
        </div>
        <button
          onClick={() => setMostrarForm((v) => !v)}
          className="rounded-lg bg-dprh-guinda text-white text-sm font-medium px-4 py-2 hover:bg-dprh-guinda-dark transition-colors"
        >
          {mostrarForm ? 'Cancelar' : '+ Nueva empresa'}
        </button>
      </div>

      {mostrarForm && (
        <NuevaEmpresaForm
          onCreada={() => {
            setMostrarForm(false)
            cargar(buscar || undefined)
          }}
        />
      )}

      <form onSubmit={handleBuscar} className="flex gap-2">
        <input
          value={buscar}
          onChange={(e) => setBuscar(e.target.value)}
          placeholder="Buscar por nombre comercial o razón social…"
          className="w-full max-w-sm rounded-lg border border-dprh-gray px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-dprh-azul"
        />
        <button
          type="submit"
          className="rounded-lg border border-dprh-gray px-4 py-2 text-sm text-gray-600 hover:bg-dprh-bg"
        >
          Buscar
        </button>
      </form>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <div className="rounded-xl border border-dprh-gray bg-white shadow-sm overflow-hidden">
        {cargando ? (
          <p className="p-5 text-sm text-gray-500">Cargando…</p>
        ) : empresas.length === 0 ? (
          <p className="p-5 text-sm text-gray-500">No se encontraron empresas.</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-dprh-bg text-gray-500 text-left">
              <tr>
                <th className="px-5 py-2 font-medium">Nombre comercial</th>
                <th className="px-5 py-2 font-medium">Contacto</th>
                <th className="px-5 py-2 font-medium">Evaluados</th>
                <th className="px-5 py-2 font-medium">Estado</th>
                <th className="px-5 py-2 font-medium text-right">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {empresas.map((empresa) => (
                <tr key={empresa.id} className="border-t border-dprh-gray/60">
                  <td className="px-5 py-2.5 text-gray-800">{empresa.nombre_comercial}</td>
                  <td className="px-5 py-2.5 text-gray-600">
                    {empresa.correo_contacto ?? '—'}
                  </td>
                  <td className="px-5 py-2.5 text-gray-600">{empresa.total_candidatos}</td>
                  <td className="px-5 py-2.5">
                    <span
                      className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${
                        empresa.activo ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
                      }`}
                    >
                      {empresa.activo ? 'Activa' : 'Inactiva'}
                    </span>
                  </td>
                  <td className="px-5 py-2.5 text-right">
                    {empresa.activo && (
                      <button
                        onClick={() => handleDesactivar(empresa.id)}
                        className="text-sm text-dprh-guinda hover:underline"
                      >
                        Desactivar
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

function NuevaEmpresaForm({ onCreada }: { onCreada: () => void }) {
  const [nombreComercial, setNombreComercial] = useState('')
  const [correoContacto, setCorreoContacto] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setError(null)
    setEnviando(true)
    try {
      await empresaService.crear({
        nombre_comercial: nombreComercial,
        correo_contacto: correoContacto || null,
      })
      onCreada()
    } catch {
      setError('No se pudo crear la empresa. Verifica los datos.')
    } finally {
      setEnviando(false)
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="rounded-xl border border-dprh-gray bg-white shadow-sm p-5 grid grid-cols-1 sm:grid-cols-2 gap-4"
    >
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Nombre comercial</label>
        <input
          required
          value={nombreComercial}
          onChange={(e) => setNombreComercial(e.target.value)}
          className="w-full rounded-lg border border-dprh-gray px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-dprh-azul"
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Correo de contacto</label>
        <input
          type="email"
          value={correoContacto}
          onChange={(e) => setCorreoContacto(e.target.value)}
          className="w-full rounded-lg border border-dprh-gray px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-dprh-azul"
        />
      </div>
      {error && <p className="sm:col-span-2 text-sm text-red-600">{error}</p>}
      <div className="sm:col-span-2">
        <button
          type="submit"
          disabled={enviando}
          className="rounded-lg bg-dprh-guinda text-white text-sm font-medium px-4 py-2 hover:bg-dprh-guinda-dark transition-colors disabled:opacity-60"
        >
          {enviando ? 'Guardando…' : 'Guardar empresa'}
        </button>
      </div>
    </form>
  )
}
