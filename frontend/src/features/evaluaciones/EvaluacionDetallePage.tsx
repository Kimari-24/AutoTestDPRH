import { useEffect, useState, type FormEvent } from 'react'
import { Link, useParams } from 'react-router-dom'
import { evaluacionService } from '../../services/evaluacionService'
import type { Algoritmo, Factor } from '../../types/algoritmo'
import type { OpcionCreate, Pregunta } from '../../types/pregunta'
import type { Prueba, VersionPrueba } from '../../types/prueba'

// TODO (Fase 6+): reemplazar por GET /api/catalogos/tipo_pregunta.
const TIPOS_PREGUNTA = [
  { codigo: 'OPCION_UNICA', nombre: 'Opción única' },
  { codigo: 'OPCION_MULTIPLE', nombre: 'Opción múltiple' },
  { codigo: 'VERDADERO_FALSO', nombre: 'Verdadero / Falso' },
  { codigo: 'ESCALA', nombre: 'Escala' },
  { codigo: 'ASOCIACION', nombre: 'Asociación' },
  { codigo: 'ORDENAMIENTO', nombre: 'Ordenamiento' },
  { codigo: 'IMAGEN', nombre: 'Pregunta con imagen' },
  { codigo: 'TEXTO', nombre: 'Pregunta basada en texto' },
  { codigo: 'ESTIMULO_VISUAL', nombre: 'Pregunta con estímulo visual' },
]

export default function EvaluacionDetallePage() {
  const { id } = useParams<{ id: string }>()
  const pruebaId = Number(id)

  const [prueba, setPrueba] = useState<Prueba | null>(null)
  const [versiones, setVersiones] = useState<VersionPrueba[]>([])
  const [preguntas, setPreguntas] = useState<Pregunta[]>([])
  const [algoritmos, setAlgoritmos] = useState<Algoritmo[]>([])
  const [error, setError] = useState<string | null>(null)

  const versionActiva = versiones.find((v) => v.activa) ?? null

  const cargarTodo = () => {
    evaluacionService.obtener(pruebaId).then(setPrueba).catch(() => setError('No se pudo cargar la evaluación.'))
    evaluacionService.listarVersiones(pruebaId).then(setVersiones).catch(() => {})
    evaluacionService.listarAlgoritmos(pruebaId).then(setAlgoritmos).catch(() => {})
  }

  useEffect(() => {
    cargarTodo()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pruebaId])

  useEffect(() => {
    if (versionActiva) {
      evaluacionService.listarPreguntas(versionActiva.id).then(setPreguntas).catch(() => {})
    } else {
      setPreguntas([])
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [versionActiva?.id])

  if (error) return <p className="text-sm text-red-600">{error}</p>
  if (!prueba) return <p className="text-sm text-gray-500">Cargando…</p>

  return (
    <div className="space-y-8">
      <Link to="/evaluaciones" className="text-sm text-dprh-azul hover:underline">
        ← Volver a evaluaciones
      </Link>

      <div>
        <h1 className="text-2xl font-semibold text-gray-800">{prueba.nombre}</h1>
        <p className="text-sm text-gray-500">
          {prueba.categoria.nombre} · Código {prueba.codigo} ·{' '}
          {prueba.tiempo_limite_minutos ? `${prueba.tiempo_limite_minutos} min` : 'sin límite de tiempo'} ·{' '}
          {prueba.intentos_permitidos} intento(s)
        </p>
      </div>

      <SeccionVersiones
        pruebaId={pruebaId}
        versiones={versiones}
        onCambio={() => {
          evaluacionService.listarVersiones(pruebaId).then(setVersiones)
        }}
      />

      {versionActiva && (
        <SeccionPreguntas
          versionId={versionActiva.id}
          preguntas={preguntas}
          onCambio={() => evaluacionService.listarPreguntas(versionActiva.id).then(setPreguntas)}
        />
      )}

      <SeccionAlgoritmo
        pruebaId={pruebaId}
        algoritmos={algoritmos}
        onCambio={() => evaluacionService.listarAlgoritmos(pruebaId).then(setAlgoritmos)}
      />
    </div>
  )
}

// ---------------------------------------------------------------------------
// Versiones
// ---------------------------------------------------------------------------

function SeccionVersiones({
  pruebaId,
  versiones,
  onCambio,
}: {
  pruebaId: number
  versiones: VersionPrueba[]
  onCambio: () => void
}) {
  const [notas, setNotas] = useState('')

  const handleCrear = async () => {
    await evaluacionService.crearVersion(pruebaId, notas || undefined)
    setNotas('')
    onCambio()
  }

  const handleActivar = async (versionId: number) => {
    await evaluacionService.activarVersion(pruebaId, versionId)
    onCambio()
  }

  return (
    <section>
      <h2 className="text-sm font-semibold text-gray-600 uppercase tracking-wide mb-3">Versiones</h2>
      <div className="rounded-xl border border-dprh-gray bg-white shadow-sm overflow-hidden">
        {versiones.length === 0 ? (
          <p className="p-5 text-sm text-gray-500">Todavía no hay versiones. Crea la primera para poder agregar preguntas.</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-dprh-bg text-gray-500 text-left">
              <tr>
                <th className="px-5 py-2 font-medium">Versión</th>
                <th className="px-5 py-2 font-medium">Preguntas</th>
                <th className="px-5 py-2 font-medium">Notas</th>
                <th className="px-5 py-2 font-medium">Estado</th>
                <th className="px-5 py-2 font-medium text-right">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {versiones.map((v) => (
                <tr key={v.id} className="border-t border-dprh-gray/60">
                  <td className="px-5 py-2.5 text-gray-800">v{v.numero_version}</td>
                  <td className="px-5 py-2.5 text-gray-600">{v.total_preguntas}</td>
                  <td className="px-5 py-2.5 text-gray-600">{v.notas ?? '—'}</td>
                  <td className="px-5 py-2.5">
                    <span
                      className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${
                        v.activa ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
                      }`}
                    >
                      {v.activa ? 'Vigente' : 'Archivada'}
                    </span>
                  </td>
                  <td className="px-5 py-2.5 text-right">
                    {!v.activa && (
                      <button
                        onClick={() => handleActivar(v.id)}
                        className="text-sm text-dprh-azul hover:underline"
                      >
                        Marcar como vigente
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <div className="border-t border-dprh-gray/60 p-4 flex gap-2">
          <input
            value={notas}
            onChange={(e) => setNotas(e.target.value)}
            placeholder="Notas de la nueva versión (opcional)"
            className="campo max-w-sm"
          />
          <button
            onClick={handleCrear}
            className="rounded-lg bg-dprh-guinda text-white text-sm font-medium px-4 py-2 hover:bg-dprh-guinda-dark transition-colors shrink-0"
          >
            + Nueva versión
          </button>
        </div>
      </div>
    </section>
  )
}

// ---------------------------------------------------------------------------
// Preguntas
// ---------------------------------------------------------------------------

function SeccionPreguntas({
  versionId,
  preguntas,
  onCambio,
}: {
  versionId: number
  preguntas: Pregunta[]
  onCambio: () => void
}) {
  const [mostrarForm, setMostrarForm] = useState(false)

  const handleDesactivar = async (preguntaId: number) => {
    await evaluacionService.desactivarPregunta(preguntaId)
    onCambio()
  }

  return (
    <section>
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold text-gray-600 uppercase tracking-wide">
          Preguntas de la versión vigente
        </h2>
        <button
          onClick={() => setMostrarForm((v) => !v)}
          className="text-sm text-dprh-azul hover:underline"
        >
          {mostrarForm ? 'Cancelar' : '+ Agregar pregunta'}
        </button>
      </div>

      {mostrarForm && (
        <NuevaPreguntaForm
          versionId={versionId}
          onCreada={() => {
            setMostrarForm(false)
            onCambio()
          }}
        />
      )}

      <div className="rounded-xl border border-dprh-gray bg-white shadow-sm divide-y divide-dprh-gray/60">
        {preguntas.length === 0 ? (
          <p className="p-5 text-sm text-gray-500">Esta versión todavía no tiene preguntas.</p>
        ) : (
          preguntas.map((p) => (
            <div key={p.id} className="p-4 flex items-start justify-between gap-4">
              <div>
                <div className="text-sm text-gray-800">
                  <span className="text-gray-400">#{p.orden}</span> {p.enunciado}
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  {p.tipo_pregunta.nombre}
                  {p.opciones.length > 0 && ` · ${p.opciones.length} opción(es)`}
                  {!p.activa && ' · Inactiva'}
                </div>
              </div>
              {p.activa && (
                <button
                  onClick={() => handleDesactivar(p.id)}
                  className="text-sm text-dprh-guinda hover:underline shrink-0"
                >
                  Desactivar
                </button>
              )}
            </div>
          ))
        )}
      </div>
    </section>
  )
}

function NuevaPreguntaForm({ versionId, onCreada }: { versionId: number; onCreada: () => void }) {
  const [tipoCodigo, setTipoCodigo] = useState(TIPOS_PREGUNTA[0].codigo)
  const [enunciado, setEnunciado] = useState('')
  const [opciones, setOpciones] = useState<string[]>(['', ''])
  const [error, setError] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)

  const requiereOpciones = ['OPCION_UNICA', 'OPCION_MULTIPLE', 'ASOCIACION', 'ORDENAMIENTO'].includes(
    tipoCodigo,
  )

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setError(null)
    setEnviando(true)
    try {
      const opcionesPayload: OpcionCreate[] = requiereOpciones
        ? opciones
            .filter((texto) => texto.trim().length > 0)
            .map((texto, i) => ({ texto, orden: i + 1 }))
        : []

      await evaluacionService.crearPregunta(versionId, {
        tipo_pregunta_codigo: tipoCodigo,
        enunciado,
        orden: 1,
        opciones: opcionesPayload,
      })
      onCreada()
    } catch {
      setError('No se pudo crear la pregunta.')
    } finally {
      setEnviando(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="rounded-xl border border-dprh-gray bg-white shadow-sm p-5 space-y-4 mb-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Tipo de pregunta</label>
        <select value={tipoCodigo} onChange={(e) => setTipoCodigo(e.target.value)} className="campo">
          {TIPOS_PREGUNTA.map((t) => (
            <option key={t.codigo} value={t.codigo}>
              {t.nombre}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Enunciado</label>
        <textarea
          required
          value={enunciado}
          onChange={(e) => setEnunciado(e.target.value)}
          className="campo"
          rows={2}
        />
      </div>

      {requiereOpciones && (
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Opciones</label>
          <div className="space-y-2">
            {opciones.map((texto, i) => (
              <input
                key={i}
                value={texto}
                onChange={(e) =>
                  setOpciones((prev) => prev.map((o, idx) => (idx === i ? e.target.value : o)))
                }
                placeholder={`Opción ${i + 1}`}
                className="campo"
              />
            ))}
          </div>
          <button
            type="button"
            onClick={() => setOpciones((prev) => [...prev, ''])}
            className="mt-2 text-sm text-dprh-azul hover:underline"
          >
            + Agregar opción
          </button>
        </div>
      )}

      {error && <p className="text-sm text-red-600">{error}</p>}

      <button
        type="submit"
        disabled={enviando}
        className="rounded-lg bg-dprh-guinda text-white text-sm font-medium px-4 py-2 hover:bg-dprh-guinda-dark transition-colors disabled:opacity-60"
      >
        {enviando ? 'Guardando…' : 'Guardar pregunta'}
      </button>
    </form>
  )
}

// ---------------------------------------------------------------------------
// Algoritmo, factores y escalas
// ---------------------------------------------------------------------------

function SeccionAlgoritmo({
  pruebaId,
  algoritmos,
  onCambio,
}: {
  pruebaId: number
  algoritmos: Algoritmo[]
  onCambio: () => void
}) {
  const [nombre, setNombre] = useState('')
  const [tipoCalculo, setTipoCalculo] = useState('')

  const handleCrear = async (event: FormEvent) => {
    event.preventDefault()
    await evaluacionService.crearAlgoritmo(pruebaId, { nombre, tipo_calculo: tipoCalculo })
    setNombre('')
    setTipoCalculo('')
    onCambio()
  }

  return (
    <section>
      <h2 className="text-sm font-semibold text-gray-600 uppercase tracking-wide mb-3">
        Algoritmo de calificación
      </h2>
      <p className="text-xs text-gray-500 mb-3">
        El "tipo de cálculo" es la estrategia genérica que ejecutará el motor (p. ej. suma,
        promedio, ponderación) — no una fórmula psicométrica real; esa la define DPRH después.
      </p>

      {algoritmos.length === 0 ? (
        <form
          onSubmit={handleCrear}
          className="rounded-xl border border-dprh-gray bg-white shadow-sm p-5 grid grid-cols-1 sm:grid-cols-3 gap-4 items-end"
        >
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Nombre</label>
            <input required value={nombre} onChange={(e) => setNombre(e.target.value)} className="campo" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Tipo de cálculo</label>
            <input
              required
              value={tipoCalculo}
              onChange={(e) => setTipoCalculo(e.target.value)}
              placeholder="p. ej. suma, promedio, ponderacion"
              className="campo"
            />
          </div>
          <button
            type="submit"
            className="rounded-lg bg-dprh-guinda text-white text-sm font-medium px-4 py-2 hover:bg-dprh-guinda-dark transition-colors"
          >
            Crear algoritmo
          </button>
        </form>
      ) : (
        algoritmos.map((algoritmo) => (
          <AlgoritmoCard key={algoritmo.id} algoritmo={algoritmo} onCambio={onCambio} />
        ))
      )}
    </section>
  )
}

function AlgoritmoCard({ algoritmo, onCambio }: { algoritmo: Algoritmo; onCambio: () => void }) {
  const [codigoFactor, setCodigoFactor] = useState('')
  const [nombreFactor, setNombreFactor] = useState('')

  const handleAgregarFactor = async (event: FormEvent) => {
    event.preventDefault()
    await evaluacionService.agregarFactor(algoritmo.id, { codigo: codigoFactor, nombre: nombreFactor })
    setCodigoFactor('')
    setNombreFactor('')
    onCambio()
  }

  return (
    <div className="rounded-xl border border-dprh-gray bg-white shadow-sm p-5 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-sm font-medium text-gray-800">{algoritmo.nombre}</div>
          <div className="text-xs text-gray-500">Cálculo: {algoritmo.tipo_calculo}</div>
        </div>
      </div>

      <div className="space-y-3">
        {algoritmo.factores.map((factor) => (
          <FactorRow key={factor.id} factor={factor} onCambio={onCambio} />
        ))}
      </div>

      <form onSubmit={handleAgregarFactor} className="flex flex-wrap gap-2 items-end pt-2 border-t border-dprh-gray/60">
        <input
          required
          value={codigoFactor}
          onChange={(e) => setCodigoFactor(e.target.value)}
          placeholder="Código del factor"
          className="campo max-w-[10rem]"
        />
        <input
          required
          value={nombreFactor}
          onChange={(e) => setNombreFactor(e.target.value)}
          placeholder="Nombre del factor"
          className="campo max-w-xs"
        />
        <button
          type="submit"
          className="rounded-lg border border-dprh-azul text-dprh-azul text-sm font-medium px-3 py-2 hover:bg-dprh-azul/5 transition-colors"
        >
          + Factor
        </button>
      </form>
    </div>
  )
}

function FactorRow({ factor, onCambio }: { factor: Factor; onCambio: () => void }) {
  const [codigoEscala, setCodigoEscala] = useState('')
  const [nombreEscala, setNombreEscala] = useState('')

  const handleAgregarEscala = async (event: FormEvent) => {
    event.preventDefault()
    await evaluacionService.agregarEscala(factor.id, { codigo: codigoEscala, nombre: nombreEscala })
    setCodigoEscala('')
    setNombreEscala('')
    onCambio()
  }

  const handleEliminarFactor = async () => {
    await evaluacionService.eliminarFactor(factor.id)
    onCambio()
  }

  return (
    <div className="rounded-lg bg-dprh-bg p-3">
      <div className="flex items-center justify-between">
        <div className="text-sm font-medium text-gray-700">
          {factor.nombre} <span className="text-gray-400 font-normal">({factor.codigo})</span>
        </div>
        <button onClick={handleEliminarFactor} className="text-xs text-dprh-guinda hover:underline">
          Eliminar factor
        </button>
      </div>

      {factor.escalas.length > 0 && (
        <ul className="mt-2 space-y-1">
          {factor.escalas.map((escala) => (
            <li key={escala.id} className="text-xs text-gray-600 flex justify-between">
              <span>
                {escala.nombre} ({escala.codigo})
                {escala.valor_min !== null && escala.valor_max !== null && (
                  <span className="text-gray-400"> · {escala.valor_min}–{escala.valor_max}</span>
                )}
              </span>
              <button
                onClick={async () => {
                  await evaluacionService.eliminarEscala(escala.id)
                  onCambio()
                }}
                className="text-dprh-guinda hover:underline"
              >
                Eliminar
              </button>
            </li>
          ))}
        </ul>
      )}

      <form onSubmit={handleAgregarEscala} className="mt-2 flex flex-wrap gap-2">
        <input
          required
          value={codigoEscala}
          onChange={(e) => setCodigoEscala(e.target.value)}
          placeholder="Código escala"
          className="campo max-w-[8rem] text-xs py-1.5"
        />
        <input
          required
          value={nombreEscala}
          onChange={(e) => setNombreEscala(e.target.value)}
          placeholder="Nombre escala"
          className="campo max-w-[10rem] text-xs py-1.5"
        />
        <button type="submit" className="text-xs text-dprh-azul hover:underline">
          + Escala
        </button>
      </form>
    </div>
  )
}
