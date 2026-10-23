import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { portalService } from '../../services/portalService'
import type { PreguntaPortal } from '../../types/portal'

type Fase = 'cargando' | 'respondiendo' | 'finalizada' | 'expirada' | 'error'

function formatearTiempo(segundos: number): string {
  const m = Math.floor(segundos / 60)
  const s = segundos % 60
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

export default function AplicarEvaluacionPage() {
  const { asignacionId } = useParams<{ asignacionId: string }>()

  const [fase, setFase] = useState<Fase>('cargando')
  const [mensajeError, setMensajeError] = useState<string | null>(null)
  const [sesionId, setSesionId] = useState<number | null>(null)
  const [preguntas, setPreguntas] = useState<PreguntaPortal[]>([])
  const [indice, setIndice] = useState(0)
  const [respuestas, setRespuestas] = useState<Record<number, string>>({})
  const [segundosRestantes, setSegundosRestantes] = useState<number | null>(null)
  const [guardando, setGuardando] = useState(false)
  const [finalizando, setFinalizando] = useState(false)
  const temporizadoresTexto = useRef<Record<number, ReturnType<typeof setTimeout>>>({})

  // --- carga inicial: iniciar (o continuar) la sesión y traer las preguntas ---
  useEffect(() => {
    let cancelado = false
    async function cargar() {
      try {
        const inicio = await portalService.iniciar(Number(asignacionId))
        const lista = await portalService.preguntas(inicio.sesion_id)
        if (cancelado) return
        setSesionId(inicio.sesion_id)
        setPreguntas(lista)
        setSegundosRestantes(inicio.tiempo_restante_segundos)
        const previas: Record<number, string> = {}
        lista.forEach((p) => {
          if (p.respuesta_actual !== null) previas[p.id] = p.respuesta_actual
        })
        setRespuestas(previas)
        setFase('respondiendo')
      } catch (err: unknown) {
        if (cancelado) return
        const detalle = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
        setMensajeError(detalle ?? 'No se pudo iniciar la evaluación.')
        setFase('error')
      }
    }
    cargar()
    return () => {
      cancelado = true
    }
  }, [asignacionId])

  // --- temporizador ---
  useEffect(() => {
    if (fase !== 'respondiendo' || segundosRestantes === null) return
    if (segundosRestantes <= 0) {
      // Sincroniza con el servidor: es quien marca la sesión como EXPIRADA.
      if (sesionId !== null) portalService.progreso(sesionId).catch(() => {})
      setFase('expirada')
      return
    }
    const id = setTimeout(() => setSegundosRestantes((s) => (s === null ? s : s - 1)), 1000)
    return () => clearTimeout(id)
  }, [fase, segundosRestantes, sesionId])

  const guardar = useCallback(
    async (preguntaId: number, payload: { opcion_id?: number | null; valor?: string | null }) => {
      if (sesionId === null) return
      setGuardando(true)
      try {
        await portalService.guardarRespuesta(sesionId, preguntaId, payload)
      } catch (err: unknown) {
        const status = (err as { response?: { status?: number } }).response?.status
        if (status === 409) {
          setFase('expirada')
        } else {
          setMensajeError('No se pudo guardar tu última respuesta. Revisa tu conexión.')
        }
      } finally {
        setGuardando(false)
      }
    },
    [sesionId],
  )

  const elegirOpcion = (pregunta: PreguntaPortal, opcionId: number) => {
    setRespuestas((prev) => ({ ...prev, [pregunta.id]: String(opcionId) }))
    guardar(pregunta.id, { opcion_id: opcionId })
  }

  const alternarOpcionMultiple = (pregunta: PreguntaPortal, opcionId: number) => {
    const actuales = (respuestas[pregunta.id] ?? '').split(',').filter(Boolean)
    const id = String(opcionId)
    const nuevas = actuales.includes(id) ? actuales.filter((x) => x !== id) : [...actuales, id]
    const valor = nuevas.join(',')
    setRespuestas((prev) => ({ ...prev, [pregunta.id]: valor }))
    guardar(pregunta.id, { valor })
  }

  const escribirTexto = (pregunta: PreguntaPortal, texto: string) => {
    setRespuestas((prev) => ({ ...prev, [pregunta.id]: texto }))
    // Autoguardado con retraso para no enviar una petición por cada tecla.
    clearTimeout(temporizadoresTexto.current[pregunta.id])
    temporizadoresTexto.current[pregunta.id] = setTimeout(
      () => guardar(pregunta.id, { valor: texto }),
      800,
    )
  }

  const handleFinalizar = async () => {
    if (sesionId === null) return
    const sinResponder = preguntas.filter((p) => !respuestas[p.id]).length
    const aviso =
      sinResponder > 0
        ? `Te quedan ${sinResponder} pregunta(s) sin responder. ¿Finalizar de todas formas?`
        : '¿Seguro que quieres finalizar la evaluación? Ya no podrás cambiar tus respuestas.'
    if (!window.confirm(aviso)) return

    setFinalizando(true)
    try {
      // Se vacían los guardados pendientes de texto antes de cerrar.
      Object.values(temporizadoresTexto.current).forEach(clearTimeout)
      await Promise.all(
        preguntas
          .filter((p) => respuestas[p.id] && p.opciones.length === 0)
          .map((p) => portalService.guardarRespuesta(sesionId, p.id, { valor: respuestas[p.id] })),
      )
      await portalService.finalizar(sesionId)
      setFase('finalizada')
    } catch {
      setMensajeError('No se pudo finalizar la evaluación. Inténtalo de nuevo.')
    } finally {
      setFinalizando(false)
    }
  }

  // --- estados que no son la pregunta en curso ---
  if (fase === 'cargando') return <p className="text-sm text-gray-500">Preparando tu evaluación…</p>

  if (fase === 'error') {
    return (
      <div className="space-y-3">
        <p className="text-sm text-red-600">{mensajeError}</p>
        <Link to="/portal" className="text-sm text-dprh-azul hover:underline">
          ← Volver a mis evaluaciones
        </Link>
      </div>
    )
  }

  if (fase === 'finalizada') {
    return (
      <div className="rounded-xl border border-dprh-gray bg-white shadow-sm p-8 text-center space-y-3">
        <h1 className="text-xl font-semibold text-gray-800">¡Evaluación finalizada!</h1>
        <p className="text-sm text-gray-600">
          Tus respuestas se guardaron correctamente. Gracias por tu tiempo; el equipo de DPRH se
          pondrá en contacto contigo.
        </p>
        <Link to="/portal" className="inline-block text-sm text-dprh-azul hover:underline">
          Volver a mis evaluaciones
        </Link>
      </div>
    )
  }

  if (fase === 'expirada') {
    return (
      <div className="rounded-xl border border-dprh-gray bg-white shadow-sm p-8 text-center space-y-3">
        <h1 className="text-xl font-semibold text-gray-800">Se agotó el tiempo</h1>
        <p className="text-sm text-gray-600">
          El tiempo de esta evaluación terminó. Las respuestas que alcanzaste a guardar quedaron
          registradas.
        </p>
        <Link to="/portal" className="inline-block text-sm text-dprh-azul hover:underline">
          Volver a mis evaluaciones
        </Link>
      </div>
    )
  }

  // --- pregunta en curso ---
  if (preguntas.length === 0) {
    return <p className="text-sm text-gray-500">Esta evaluación todavía no tiene preguntas.</p>
  }

  const pregunta = preguntas[indice]
  const respondidas = preguntas.filter((p) => respuestas[p.id]).length
  const porcentaje = Math.round((respondidas / preguntas.length) * 100)
  const esUltima = indice === preguntas.length - 1

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between text-sm">
        <span className="text-gray-600">
          Pregunta {indice + 1} de {preguntas.length}
        </span>
        <span className="flex items-center gap-3">
          {guardando && <span className="text-xs text-gray-400">Guardando…</span>}
          {segundosRestantes !== null && (
            <span
              className={`font-mono font-medium ${
                segundosRestantes <= 60 ? 'text-red-600' : 'text-gray-700'
              }`}
            >
              ⏱ {formatearTiempo(segundosRestantes)}
            </span>
          )}
        </span>
      </div>

      <div className="h-2 rounded-full bg-dprh-gray overflow-hidden">
        <div className="h-full bg-dprh-azul transition-all" style={{ width: `${porcentaje}%` }} />
      </div>

      <div className="rounded-xl border border-dprh-gray bg-white shadow-sm p-6 space-y-4">
        <p className="text-gray-800">{pregunta.enunciado}</p>
        {pregunta.imagen_url && (
          <img src={pregunta.imagen_url} alt="" className="max-h-64 rounded-lg border border-dprh-gray" />
        )}

        {pregunta.opciones.length > 0 && pregunta.tipo_pregunta_codigo === 'OPCION_MULTIPLE' && (
          <div className="space-y-2">
            {pregunta.opciones.map((o) => {
              const marcada = (respuestas[pregunta.id] ?? '').split(',').includes(String(o.id))
              return (
                <label
                  key={o.id}
                  className="flex items-center gap-3 rounded-lg border border-dprh-gray p-3 cursor-pointer hover:bg-dprh-bg"
                >
                  <input
                    type="checkbox"
                    checked={marcada}
                    onChange={() => alternarOpcionMultiple(pregunta, o.id)}
                  />
                  <span className="text-sm text-gray-700">{o.texto}</span>
                </label>
              )
            })}
          </div>
        )}

        {pregunta.opciones.length > 0 && pregunta.tipo_pregunta_codigo !== 'OPCION_MULTIPLE' && (
          <div className="space-y-2">
            {pregunta.opciones.map((o) => (
              <label
                key={o.id}
                className="flex items-center gap-3 rounded-lg border border-dprh-gray p-3 cursor-pointer hover:bg-dprh-bg"
              >
                <input
                  type="radio"
                  name={`pregunta-${pregunta.id}`}
                  checked={respuestas[pregunta.id] === String(o.id)}
                  onChange={() => elegirOpcion(pregunta, o.id)}
                />
                <span className="text-sm text-gray-700">{o.texto}</span>
              </label>
            ))}
          </div>
        )}

        {pregunta.opciones.length === 0 && (
          <textarea
            value={respuestas[pregunta.id] ?? ''}
            onChange={(e) => escribirTexto(pregunta, e.target.value)}
            rows={4}
            placeholder="Escribe tu respuesta…"
            className="campo"
          />
        )}
      </div>

      {mensajeError && <p className="text-sm text-red-600">{mensajeError}</p>}

      <div className="flex items-center justify-between">
        <button
          onClick={() => setIndice((i) => Math.max(0, i - 1))}
          disabled={indice === 0}
          className="rounded-lg border border-dprh-gray px-4 py-2 text-sm text-gray-600 hover:bg-dprh-bg disabled:opacity-40"
        >
          Anterior
        </button>

        {esUltima ? (
          <button
            onClick={handleFinalizar}
            disabled={finalizando}
            className="rounded-lg bg-dprh-guinda text-white text-sm font-medium px-5 py-2 hover:bg-dprh-guinda-dark transition-colors disabled:opacity-60"
          >
            {finalizando ? 'Finalizando…' : 'Finalizar evaluación'}
          </button>
        ) : (
          <button
            onClick={() => setIndice((i) => Math.min(preguntas.length - 1, i + 1))}
            className="rounded-lg bg-dprh-azul text-white text-sm font-medium px-5 py-2 hover:opacity-90 transition-opacity"
          >
            Siguiente
          </button>
        )}
      </div>
    </div>
  )
}
