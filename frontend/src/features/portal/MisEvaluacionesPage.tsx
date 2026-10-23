import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { portalService } from '../../services/portalService'
import type { MiEvaluacion } from '../../types/portal'

const ETIQUETAS_ESTATUS: Record<string, string> = {
  PENDIENTE: 'Pendiente',
  EN_PROCESO: 'En proceso',
  COMPLETADA: 'Completada',
  CALIFICADA: 'Completada',
  CANCELADA: 'Cancelada',
  EXPIRADA: 'Expirada',
}

export default function MisEvaluacionesPage() {
  const [evaluaciones, setEvaluaciones] = useState<MiEvaluacion[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    portalService
      .misEvaluaciones()
      .then(setEvaluaciones)
      .catch(() => setError('No se pudieron cargar tus evaluaciones.'))
  }, [])

  if (error) return <p className="text-sm text-red-600">{error}</p>
  if (!evaluaciones) return <p className="text-sm text-gray-500">Cargando…</p>

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-gray-800">Mis evaluaciones</h1>
        <p className="text-sm text-gray-500">
          Estas son las evaluaciones que tienes asignadas. Puedes pausar y continuar una evaluación
          en proceso mientras tu acceso siga vigente.
        </p>
      </div>

      {evaluaciones.length === 0 ? (
        <p className="rounded-xl border border-dprh-gray bg-white p-5 text-sm text-gray-500">
          Todavía no tienes evaluaciones asignadas.
        </p>
      ) : (
        <ul className="space-y-3">
          {evaluaciones.map((ev) => (
            <li
              key={ev.asignacion_id}
              className="rounded-xl border border-dprh-gray bg-white shadow-sm p-5 flex items-center justify-between gap-4"
            >
              <div>
                <div className="font-medium text-gray-800">{ev.prueba_nombre}</div>
                <div className="text-xs text-gray-500 mt-1">
                  {ETIQUETAS_ESTATUS[ev.estatus] ?? ev.estatus}
                  {ev.tiempo_limite_minutos && ` · Tiempo límite: ${ev.tiempo_limite_minutos} min`}
                </div>
              </div>
              {ev.puede_iniciar ? (
                <Link
                  to={`/portal/evaluaciones/${ev.asignacion_id}`}
                  className="rounded-lg bg-dprh-guinda text-white text-sm font-medium px-4 py-2 hover:bg-dprh-guinda-dark transition-colors shrink-0"
                >
                  {ev.estatus === 'EN_PROCESO' ? 'Continuar' : 'Iniciar'}
                </Link>
              ) : (
                <span className="text-sm text-gray-400 shrink-0">No disponible</span>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
