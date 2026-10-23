import { useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { evaluacionService } from '../../services/evaluacionService'
import type { CategoriaPrueba, Prueba } from '../../types/prueba'

export default function EvaluacionesPage() {
  const [pruebas, setPruebas] = useState<Prueba[]>([])
  const [categorias, setCategorias] = useState<CategoriaPrueba[]>([])
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [mostrarForm, setMostrarForm] = useState(false)

  const cargar = () => {
    setCargando(true)
    evaluacionService
      .listar()
      .then(setPruebas)
      .catch(() => setError('No se pudieron cargar las evaluaciones.'))
      .finally(() => setCargando(false))
  }

  useEffect(() => {
    cargar()
    evaluacionService.listarCategorias().then(setCategorias).catch(() => {})
  }, [])

  const handleCambiarEstado = async (prueba: Prueba) => {
    if (prueba.activa) {
      await evaluacionService.desactivar(prueba.id)
    } else {
      await evaluacionService.activar(prueba.id)
    }
    cargar()
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-800">Evaluaciones</h1>
          <p className="text-sm text-gray-500">
            Catálogo de pruebas psicométricas. Aquí se administra la estructura (preguntas,
            algoritmo, factores y escalas) — el contenido psicométrico real lo carga DPRH.
          </p>
        </div>
        <button
          onClick={() => setMostrarForm((v) => !v)}
          className="rounded-lg bg-dprh-guinda text-white text-sm font-medium px-4 py-2 hover:bg-dprh-guinda-dark transition-colors shrink-0"
        >
          {mostrarForm ? 'Cancelar' : '+ Nueva evaluación'}
        </button>
      </div>

      {mostrarForm && (
        <NuevaEvaluacionForm
          categorias={categorias}
          onCategoriaCreada={(c) => setCategorias((prev) => [...prev, c])}
          onCreada={() => {
            setMostrarForm(false)
            cargar()
          }}
        />
      )}

      {error && <p className="text-sm text-red-600">{error}</p>}

      <div className="rounded-xl border border-dprh-gray bg-white shadow-sm overflow-hidden">
        {cargando ? (
          <p className="p-5 text-sm text-gray-500">Cargando…</p>
        ) : pruebas.length === 0 ? (
          <p className="p-5 text-sm text-gray-500">Todavía no hay evaluaciones configuradas.</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-dprh-bg text-gray-500 text-left">
              <tr>
                <th className="px-5 py-2 font-medium">Evaluación</th>
                <th className="px-5 py-2 font-medium">Categoría</th>
                <th className="px-5 py-2 font-medium">Preguntas activas</th>
                <th className="px-5 py-2 font-medium">Tiempo límite</th>
                <th className="px-5 py-2 font-medium">Estado</th>
                <th className="px-5 py-2 font-medium text-right">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {pruebas.map((p) => (
                <tr key={p.id} className="border-t border-dprh-gray/60">
                  <td className="px-5 py-2.5">
                    <Link to={`/evaluaciones/${p.id}`} className="text-dprh-azul hover:underline">
                      {p.nombre}
                    </Link>
                    <div className="text-xs text-gray-400">{p.codigo}</div>
                  </td>
                  <td className="px-5 py-2.5 text-gray-600">{p.categoria.nombre}</td>
                  <td className="px-5 py-2.5 text-gray-600">{p.total_preguntas_activas}</td>
                  <td className="px-5 py-2.5 text-gray-600">
                    {p.tiempo_limite_minutos ? `${p.tiempo_limite_minutos} min` : '—'}
                  </td>
                  <td className="px-5 py-2.5">
                    <span
                      className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${
                        p.activa ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
                      }`}
                    >
                      {p.activa ? 'Activa' : 'Inactiva'}
                    </span>
                  </td>
                  <td className="px-5 py-2.5 text-right space-x-3">
                    <Link to={`/evaluaciones/${p.id}`} className="text-sm text-dprh-azul hover:underline">
                      Configurar
                    </Link>
                    <button
                      onClick={() => handleCambiarEstado(p)}
                      className="text-sm text-dprh-guinda hover:underline"
                    >
                      {p.activa ? 'Desactivar' : 'Activar'}
                    </button>
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

function NuevaEvaluacionForm({
  categorias,
  onCategoriaCreada,
  onCreada,
}: {
  categorias: CategoriaPrueba[]
  onCategoriaCreada: (categoria: CategoriaPrueba) => void
  onCreada: () => void
}) {
  const [categoriaCodigo, setCategoriaCodigo] = useState('')
  const [nuevaCategoriaCodigo, setNuevaCategoriaCodigo] = useState('')
  const [nuevaCategoriaNombre, setNuevaCategoriaNombre] = useState('')
  const [codigo, setCodigo] = useState('')
  const [nombre, setNombre] = useState('')
  const [tiempoLimite, setTiempoLimite] = useState('')
  const [intentos, setIntentos] = useState('1')
  const [error, setError] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)

  const handleCrearCategoria = async () => {
    if (!nuevaCategoriaCodigo || !nuevaCategoriaNombre) return
    try {
      const categoria = await evaluacionService.crearCategoria({
        codigo: nuevaCategoriaCodigo.toUpperCase(),
        nombre: nuevaCategoriaNombre,
      })
      onCategoriaCreada(categoria)
      setCategoriaCodigo(categoria.codigo)
      setNuevaCategoriaCodigo('')
      setNuevaCategoriaNombre('')
    } catch {
      setError('No se pudo crear la categoría (¿código repetido?).')
    }
  }

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setError(null)
    setEnviando(true)
    try {
      await evaluacionService.crear({
        categoria_codigo: categoriaCodigo,
        codigo: codigo.toUpperCase(),
        nombre,
        tiempo_limite_minutos: tiempoLimite ? Number(tiempoLimite) : null,
        intentos_permitidos: Number(intentos) || 1,
      })
      onCreada()
    } catch {
      setError('No se pudo crear la evaluación. Verifica que el código no esté repetido.')
    } finally {
      setEnviando(false)
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="rounded-xl border border-dprh-gray bg-white shadow-sm p-5 space-y-4"
    >
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Categoría</label>
          <select
            required
            value={categoriaCodigo}
            onChange={(e) => setCategoriaCodigo(e.target.value)}
            className="campo"
          >
            <option value="">Selecciona una categoría…</option>
            {categorias.map((c) => (
              <option key={c.id} value={c.codigo}>
                {c.nombre}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Código</label>
          <input
            required
            value={codigo}
            onChange={(e) => setCodigo(e.target.value)}
            placeholder="p. ej. TERMAN"
            className="campo"
          />
        </div>
        <div className="sm:col-span-2">
          <label className="block text-sm font-medium text-gray-700 mb-1">Nombre</label>
          <input required value={nombre} onChange={(e) => setNombre(e.target.value)} className="campo" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Tiempo límite (min)</label>
          <input
            type="number"
            min={1}
            value={tiempoLimite}
            onChange={(e) => setTiempoLimite(e.target.value)}
            className="campo"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Intentos permitidos</label>
          <input
            type="number"
            min={1}
            value={intentos}
            onChange={(e) => setIntentos(e.target.value)}
            className="campo"
          />
        </div>
      </div>

      <details className="text-sm">
        <summary className="cursor-pointer text-dprh-azul">¿No existe la categoría? Crear una nueva</summary>
        <div className="mt-3 grid grid-cols-1 sm:grid-cols-3 gap-3 items-end">
          <input
            value={nuevaCategoriaCodigo}
            onChange={(e) => setNuevaCategoriaCodigo(e.target.value)}
            placeholder="Código (p. ej. PERSONALIDAD)"
            className="campo"
          />
          <input
            value={nuevaCategoriaNombre}
            onChange={(e) => setNuevaCategoriaNombre(e.target.value)}
            placeholder="Nombre visible"
            className="campo"
          />
          <button
            type="button"
            onClick={handleCrearCategoria}
            className="rounded-lg border border-dprh-gray px-4 py-2 text-sm text-gray-600 hover:bg-dprh-bg"
          >
            Crear categoría
          </button>
        </div>
      </details>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <button
        type="submit"
        disabled={enviando || !categoriaCodigo}
        className="rounded-lg bg-dprh-guinda text-white text-sm font-medium px-4 py-2 hover:bg-dprh-guinda-dark transition-colors disabled:opacity-60"
      >
        {enviando ? 'Guardando…' : 'Guardar evaluación'}
      </button>
    </form>
  )
}
