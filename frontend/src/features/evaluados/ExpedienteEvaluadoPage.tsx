import { useEffect, useState, type FormEvent } from 'react'
import { Link, useParams } from 'react-router-dom'
import { accesoTemporalService } from '../../services/accesoTemporalService'
import { evaluacionService } from '../../services/evaluacionService'
import { evaluadoService } from '../../services/evaluadoService'
import type { AccesoTemporal, AccesoTemporalCreado } from '../../types/accesoTemporal'
import type { ExpedienteCandidato } from '../../types/candidato'
import type { Prueba } from '../../types/prueba'

export default function ExpedienteEvaluadoPage() {
  const { id } = useParams<{ id: string }>()
  const candidatoId = Number(id)
  const [expediente, setExpediente] = useState<ExpedienteCandidato | null>(null)
  const [accesos, setAccesos] = useState<AccesoTemporal[]>([])
  const [pruebas, setPruebas] = useState<Prueba[]>([])
  const [error, setError] = useState<string | null>(null)
  const [ultimoAccesoCreado, setUltimoAccesoCreado] = useState<AccesoTemporalCreado | null>(null)

  const cargarTodo = () => {
    evaluadoService
      .obtenerExpediente(candidatoId)
      .then(setExpediente)
      .catch(() => setError('No se pudo cargar el expediente.'))
    accesoTemporalService.listarAccesos(candidatoId).then(setAccesos).catch(() => {})
  }

  useEffect(() => {
    if (!candidatoId) return
    cargarTodo()
    evaluacionService.listar({ solo_activas: true }).then(setPruebas).catch(() => {})
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [candidatoId])

  if (error) return <p className="text-sm text-red-600">{error}</p>
  if (!expediente) return <p className="text-sm text-gray-500">Cargando…</p>

  const { candidato, evaluaciones } = expediente

  const handleGenerarAcceso = async () => {
    const creado = await accesoTemporalService.crearAcceso(candidatoId, 48)
    setUltimoAccesoCreado(creado)
    accesoTemporalService.listarAccesos(candidatoId).then(setAccesos)
  }

  const handleRevocar = async (accesoId: number) => {
    await accesoTemporalService.revocarAcceso(accesoId)
    accesoTemporalService.listarAccesos(candidatoId).then(setAccesos)
  }

  return (
    <div className="space-y-6">
      <Link to="/evaluados" className="text-sm text-dprh-azul hover:underline">
        ← Volver a evaluados
      </Link>

      <div>
        <h1 className="text-2xl font-semibold text-gray-800">
          {candidato.nombre} {candidato.apellidos}
        </h1>
        <p className="text-sm text-gray-500">{candidato.correo}</p>
      </div>

      <section className="rounded-xl border border-dprh-gray bg-white shadow-sm p-5">
        <h2 className="text-sm font-semibold text-gray-600 uppercase tracking-wide mb-4">
          Datos personales
        </h2>
        <dl className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-sm">
          <Dato etiqueta="Puesto" valor={candidato.puesto ?? '—'} />
          <Dato etiqueta="Empresa" valor={candidato.empresa?.nombre_comercial ?? '—'} />
          <Dato etiqueta="Fecha de nacimiento" valor={candidato.fecha_nacimiento ?? '—'} />
          <Dato etiqueta="Sexo" valor={candidato.sexo?.nombre ?? '—'} />
          <Dato etiqueta="Escolaridad" valor={candidato.escolaridad?.nombre ?? '—'} />
          <Dato etiqueta="Estado" valor={candidato.activo ? 'Activo' : 'Inactivo'} />
        </dl>
      </section>

      <AsignarEvaluacionForm pruebas={pruebas} onAsignada={cargarTodo} candidatoId={candidatoId} />

      <section>
        <h2 className="text-sm font-semibold text-gray-600 uppercase tracking-wide mb-3">
          Evaluaciones asignadas
        </h2>
        <div className="rounded-xl border border-dprh-gray bg-white shadow-sm overflow-hidden">
          {evaluaciones.length === 0 ? (
            <p className="p-5 text-sm text-gray-500">
              Este evaluado todavía no tiene evaluaciones asignadas.
            </p>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-dprh-bg text-gray-500 text-left">
                <tr>
                  <th className="px-5 py-2 font-medium">Evaluación</th>
                  <th className="px-5 py-2 font-medium">Categoría</th>
                  <th className="px-5 py-2 font-medium">Estado</th>
                  <th className="px-5 py-2 font-medium">Progreso</th>
                  <th className="px-5 py-2 font-medium">Asignada</th>
                  <th className="px-5 py-2 font-medium text-right">Acciones</th>
                </tr>
              </thead>
              <tbody>
                {evaluaciones.map((ev) => (
                  <tr key={ev.asignacion_id} className="border-t border-dprh-gray/60">
                    <td className="px-5 py-2.5 text-gray-800">{ev.prueba}</td>
                    <td className="px-5 py-2.5 text-gray-600">{ev.categoria}</td>
                    <td className="px-5 py-2.5 text-gray-600">{ev.estatus}</td>
                    <td className="px-5 py-2.5 text-gray-600">{ev.progreso_porcentaje}%</td>
                    <td className="px-5 py-2.5 text-gray-600">
                      {new Date(ev.fecha_asignacion).toLocaleDateString()}
                    </td>
                    <td className="px-5 py-2.5 text-right">
                      {ev.resultado_disponible ? (
                        <span className="text-sm text-dprh-azul">Ver resultado</span>
                      ) : (
                        <span className="text-sm text-gray-400">Sin resultado</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </section>

      <section>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-gray-600 uppercase tracking-wide">
            Accesos temporales
          </h2>
          <button
            onClick={handleGenerarAcceso}
            className="text-sm text-dprh-azul hover:underline"
          >
            + Generar acceso temporal
          </button>
        </div>

        {ultimoAccesoCreado && (
          <div className="mb-3 rounded-lg border border-dprh-dorado bg-dprh-dorado/10 p-4 text-sm">
            <p className="font-medium text-gray-800">
              Credenciales generadas — cópialas ahora, no se podrán ver de nuevo:
            </p>
            <p className="mt-1 text-gray-700">
              Usuario: <span className="font-mono">{ultimoAccesoCreado.usuario}</span> · Contraseña:{' '}
              <span className="font-mono">{ultimoAccesoCreado.password_temporal}</span>
            </p>
            <p className="text-xs text-gray-500 mt-1">
              Expira: {new Date(ultimoAccesoCreado.expira_en).toLocaleString()}
            </p>
          </div>
        )}

        <div className="rounded-xl border border-dprh-gray bg-white shadow-sm overflow-hidden">
          {accesos.length === 0 ? (
            <p className="p-5 text-sm text-gray-500">Todavía no se ha generado ningún acceso.</p>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-dprh-bg text-gray-500 text-left">
                <tr>
                  <th className="px-5 py-2 font-medium">Usuario</th>
                  <th className="px-5 py-2 font-medium">Expira</th>
                  <th className="px-5 py-2 font-medium">Último acceso</th>
                  <th className="px-5 py-2 font-medium">Estado</th>
                  <th className="px-5 py-2 font-medium text-right">Acciones</th>
                </tr>
              </thead>
              <tbody>
                {accesos.map((a) => (
                  <tr key={a.id} className="border-t border-dprh-gray/60">
                    <td className="px-5 py-2.5 font-mono text-gray-800">{a.usuario}</td>
                    <td className="px-5 py-2.5 text-gray-600">
                      {new Date(a.expira_en).toLocaleString()}
                    </td>
                    <td className="px-5 py-2.5 text-gray-600">
                      {a.ultimo_acceso ? new Date(a.ultimo_acceso).toLocaleString() : 'Nunca'}
                    </td>
                    <td className="px-5 py-2.5">
                      <span
                        className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${
                          a.revocado
                            ? 'bg-gray-100 text-gray-500'
                            : 'bg-green-100 text-green-700'
                        }`}
                      >
                        {a.revocado ? 'Revocado' : 'Activo'}
                      </span>
                    </td>
                    <td className="px-5 py-2.5 text-right">
                      {!a.revocado && (
                        <button
                          onClick={() => handleRevocar(a.id)}
                          className="text-sm text-dprh-guinda hover:underline"
                        >
                          Revocar
                        </button>
                      )}
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

function AsignarEvaluacionForm({
  pruebas,
  candidatoId,
  onAsignada,
}: {
  pruebas: Prueba[]
  candidatoId: number
  onAsignada: () => void
}) {
  const [pruebaId, setPruebaId] = useState('')
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setError(null)
    try {
      await accesoTemporalService.asignarEvaluacion(candidatoId, Number(pruebaId))
      setPruebaId('')
      onAsignada()
    } catch {
      setError('No se pudo asignar la evaluación.')
    }
  }

  return (
    <section className="rounded-xl border border-dprh-gray bg-white shadow-sm p-5">
      <h2 className="text-sm font-semibold text-gray-600 uppercase tracking-wide mb-3">
        Asignar evaluación
      </h2>
      <form onSubmit={handleSubmit} className="flex flex-wrap gap-2 items-end">
        <select required value={pruebaId} onChange={(e) => setPruebaId(e.target.value)} className="campo max-w-xs">
          <option value="">Selecciona una evaluación…</option>
          {pruebas.map((p) => (
            <option key={p.id} value={p.id}>
              {p.nombre}
            </option>
          ))}
        </select>
        <button
          type="submit"
          className="rounded-lg bg-dprh-guinda text-white text-sm font-medium px-4 py-2 hover:bg-dprh-guinda-dark transition-colors"
        >
          Asignar
        </button>
      </form>
      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
    </section>
  )
}

function Dato({ etiqueta, valor }: { etiqueta: string; valor: string }) {
  return (
    <div>
      <dt className="text-gray-500">{etiqueta}</dt>
      <dd className="text-gray-800 font-medium">{valor}</dd>
    </div>
  )
}
