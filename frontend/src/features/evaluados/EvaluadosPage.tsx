import { useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { empresaService } from '../../services/empresaService'
import { evaluadoService } from '../../services/evaluadoService'
import type { Candidato } from '../../types/candidato'
import type { Empresa } from '../../types/empresa'

// TODO (Fase 5+): reemplazar por un endpoint de catálogos genérico
// (GET /api/catalogos/{tipo}) en vez de códigos fijos en el frontend.
const OPCIONES_SEXO = [
  { codigo: 'MASCULINO', nombre: 'Masculino' },
  { codigo: 'FEMENINO', nombre: 'Femenino' },
]

const OPCIONES_ESCOLARIDAD = [
  { codigo: 'PRIMARIA', nombre: 'Primaria' },
  { codigo: 'SECUNDARIA', nombre: 'Secundaria' },
  { codigo: 'PREPARATORIA', nombre: 'Preparatoria / Bachillerato' },
  { codigo: 'LICENCIATURA', nombre: 'Licenciatura' },
  { codigo: 'MAESTRIA', nombre: 'Maestría' },
  { codigo: 'DOCTORADO', nombre: 'Doctorado' },
]

export default function EvaluadosPage() {
  const [evaluados, setEvaluados] = useState<Candidato[]>([])
  const [empresas, setEmpresas] = useState<Empresa[]>([])
  const [buscar, setBuscar] = useState('')
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [mostrarForm, setMostrarForm] = useState(false)

  const cargar = (filtro?: string) => {
    setCargando(true)
    evaluadoService
      .listar(filtro ? { buscar: filtro } : undefined)
      .then(setEvaluados)
      .catch(() => setError('No se pudieron cargar los evaluados.'))
      .finally(() => setCargando(false))
  }

  useEffect(() => {
    cargar()
    empresaService.listar({ solo_activas: true }).then(setEmpresas).catch(() => {})
  }, [])

  const handleBuscar = (event: FormEvent) => {
    event.preventDefault()
    cargar(buscar || undefined)
  }

  const handleDesactivar = async (id: number) => {
    await evaluadoService.desactivar(id)
    cargar(buscar || undefined)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-800">Evaluados</h1>
          <p className="text-sm text-gray-500">Personas registradas para aplicar evaluaciones</p>
        </div>
        <button
          onClick={() => setMostrarForm((v) => !v)}
          className="rounded-lg bg-dprh-guinda text-white text-sm font-medium px-4 py-2 hover:bg-dprh-guinda-dark transition-colors"
        >
          {mostrarForm ? 'Cancelar' : '+ Nuevo evaluado'}
        </button>
      </div>

      {mostrarForm && (
        <NuevoEvaluadoForm
          empresas={empresas}
          onCreado={() => {
            setMostrarForm(false)
            cargar(buscar || undefined)
          }}
        />
      )}

      <form onSubmit={handleBuscar} className="flex gap-2">
        <input
          value={buscar}
          onChange={(e) => setBuscar(e.target.value)}
          placeholder="Buscar por nombre, apellidos o correo…"
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
        ) : evaluados.length === 0 ? (
          <p className="p-5 text-sm text-gray-500">No se encontraron evaluados.</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-dprh-bg text-gray-500 text-left">
              <tr>
                <th className="px-5 py-2 font-medium">Nombre</th>
                <th className="px-5 py-2 font-medium">Correo</th>
                <th className="px-5 py-2 font-medium">Empresa</th>
                <th className="px-5 py-2 font-medium">Escolaridad</th>
                <th className="px-5 py-2 font-medium">Estado</th>
                <th className="px-5 py-2 font-medium text-right">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {evaluados.map((c) => (
                <tr key={c.id} className="border-t border-dprh-gray/60">
                  <td className="px-5 py-2.5">
                    <Link to={`/evaluados/${c.id}`} className="text-dprh-azul hover:underline">
                      {c.nombre} {c.apellidos}
                    </Link>
                  </td>
                  <td className="px-5 py-2.5 text-gray-600">{c.correo}</td>
                  <td className="px-5 py-2.5 text-gray-600">
                    {c.empresa?.nombre_comercial ?? '—'}
                  </td>
                  <td className="px-5 py-2.5 text-gray-600">{c.escolaridad?.nombre ?? '—'}</td>
                  <td className="px-5 py-2.5">
                    <span
                      className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${
                        c.activo ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
                      }`}
                    >
                      {c.activo ? 'Activo' : 'Inactivo'}
                    </span>
                  </td>
                  <td className="px-5 py-2.5 text-right space-x-3">
                    <Link to={`/evaluados/${c.id}`} className="text-sm text-dprh-azul hover:underline">
                      Ver expediente
                    </Link>
                    {c.activo && (
                      <button
                        onClick={() => handleDesactivar(c.id)}
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

function NuevoEvaluadoForm({
  empresas,
  onCreado,
}: {
  empresas: Empresa[]
  onCreado: () => void
}) {
  const [nombre, setNombre] = useState('')
  const [apellidos, setApellidos] = useState('')
  const [correo, setCorreo] = useState('')
  const [puesto, setPuesto] = useState('')
  const [empresaId, setEmpresaId] = useState('')
  const [sexoCodigo, setSexoCodigo] = useState('')
  const [escolaridadCodigo, setEscolaridadCodigo] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setError(null)
    setEnviando(true)
    try {
      await evaluadoService.crear({
        nombre,
        apellidos,
        correo,
        puesto: puesto || null,
        empresa_id: empresaId ? Number(empresaId) : null,
        sexo_codigo: sexoCodigo || null,
        escolaridad_codigo: escolaridadCodigo || null,
      })
      onCreado()
    } catch {
      setError('No se pudo crear el evaluado. Verifica que el correo no esté repetido.')
    } finally {
      setEnviando(false)
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="rounded-xl border border-dprh-gray bg-white shadow-sm p-5 grid grid-cols-1 sm:grid-cols-2 gap-4"
    >
      <Campo label="Nombre">
        <input
          required
          value={nombre}
          onChange={(e) => setNombre(e.target.value)}
          className="campo"
        />
      </Campo>
      <Campo label="Apellidos">
        <input
          required
          value={apellidos}
          onChange={(e) => setApellidos(e.target.value)}
          className="campo"
        />
      </Campo>
      <Campo label="Correo">
        <input
          type="email"
          required
          value={correo}
          onChange={(e) => setCorreo(e.target.value)}
          className="campo"
        />
      </Campo>
      <Campo label="Puesto">
        <input value={puesto} onChange={(e) => setPuesto(e.target.value)} className="campo" />
      </Campo>
      <Campo label="Empresa">
        <select value={empresaId} onChange={(e) => setEmpresaId(e.target.value)} className="campo">
          <option value="">Sin empresa</option>
          {empresas.map((e) => (
            <option key={e.id} value={e.id}>
              {e.nombre_comercial}
            </option>
          ))}
        </select>
      </Campo>
      <Campo label="Sexo">
        <select value={sexoCodigo} onChange={(e) => setSexoCodigo(e.target.value)} className="campo">
          <option value="">No especificado</option>
          {OPCIONES_SEXO.map((o) => (
            <option key={o.codigo} value={o.codigo}>
              {o.nombre}
            </option>
          ))}
        </select>
      </Campo>
      <Campo label="Escolaridad">
        <select
          value={escolaridadCodigo}
          onChange={(e) => setEscolaridadCodigo(e.target.value)}
          className="campo"
        >
          <option value="">No especificada</option>
          {OPCIONES_ESCOLARIDAD.map((o) => (
            <option key={o.codigo} value={o.codigo}>
              {o.nombre}
            </option>
          ))}
        </select>
      </Campo>

      {error && <p className="sm:col-span-2 text-sm text-red-600">{error}</p>}
      <div className="sm:col-span-2">
        <button
          type="submit"
          disabled={enviando}
          className="rounded-lg bg-dprh-guinda text-white text-sm font-medium px-4 py-2 hover:bg-dprh-guinda-dark transition-colors disabled:opacity-60"
        >
          {enviando ? 'Guardando…' : 'Guardar evaluado'}
        </button>
      </div>
    </form>
  )
}

function Campo({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
      {children}
    </div>
  )
}
