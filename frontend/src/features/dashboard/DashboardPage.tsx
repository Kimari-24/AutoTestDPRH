import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { dashboardService } from '../../services/dashboardService'
import type { DashboardResumen } from '../../types/dashboard'
import StatCard from './StatCard'

export default function DashboardPage() {
  const [resumen, setResumen] = useState<DashboardResumen | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    dashboardService
      .obtenerResumen()
      .then(setResumen)
      .catch(() => setError('No se pudo cargar el dashboard.'))
  }, [])

  if (error) {
    return <p className="text-sm text-red-600">{error}</p>
  }

  if (!resumen) {
    return <p className="text-sm text-gray-500">Cargando dashboard…</p>
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold text-gray-800">Dashboard</h1>
        <p className="text-sm text-gray-500">Resumen general del sistema</p>
      </div>

      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <StatCard label="Total de evaluados" value={resumen.total_evaluados} accent="guinda" />
        <StatCard
          label="Evaluaciones disponibles"
          value={resumen.total_evaluaciones_disponibles}
          accent="azul"
        />
        <StatCard label="Resultados generados" value={resumen.total_resultados} accent="dorado" />
      </section>

      <section>
        <h2 className="text-sm font-semibold text-gray-600 uppercase tracking-wide mb-3">
          Estado de evaluaciones
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <StatCard label="Pendientes" value={resumen.evaluaciones_pendientes} accent="dorado" />
          <StatCard label="En proceso" value={resumen.evaluaciones_en_proceso} accent="azul" />
          <StatCard label="Completadas" value={resumen.evaluaciones_completadas} accent="guinda" />
        </div>
      </section>

      <section>
        <h2 className="text-sm font-semibold text-gray-600 uppercase tracking-wide mb-3">
          Acciones rápidas
        </h2>
        <div className="flex flex-wrap gap-3">
          <Link
            to="/evaluados"
            className="rounded-lg bg-dprh-guinda text-white text-sm font-medium px-4 py-2 hover:bg-dprh-guinda-dark transition-colors"
          >
            + Nuevo evaluado
          </Link>
          <Link
            to="/empresas"
            className="rounded-lg border border-dprh-azul text-dprh-azul text-sm font-medium px-4 py-2 hover:bg-dprh-azul/5 transition-colors"
          >
            + Nueva empresa
          </Link>
        </div>
      </section>

      <section>
        <h2 className="text-sm font-semibold text-gray-600 uppercase tracking-wide mb-3">
          Evaluados recientes
        </h2>
        <div className="rounded-xl border border-dprh-gray bg-white shadow-sm overflow-hidden">
          {resumen.evaluados_recientes.length === 0 ? (
            <p className="p-5 text-sm text-gray-500">Todavía no hay evaluados registrados.</p>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-dprh-bg text-gray-500 text-left">
                <tr>
                  <th className="px-5 py-2 font-medium">Nombre</th>
                  <th className="px-5 py-2 font-medium">Correo</th>
                  <th className="px-5 py-2 font-medium">Empresa</th>
                  <th className="px-5 py-2 font-medium">Estado</th>
                </tr>
              </thead>
              <tbody>
                {resumen.evaluados_recientes.map((c) => (
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
                    <td className="px-5 py-2.5">
                      <span
                        className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${
                          c.activo ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
                        }`}
                      >
                        {c.activo ? 'Activo' : 'Inactivo'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </section>
    </div>
  )
}
