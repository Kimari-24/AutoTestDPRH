import { apiClient } from './apiClient'
import type { Algoritmo, AlgoritmoCreate, Escala, EscalaCreate, Factor, FactorCreate } from '../types/algoritmo'
import type { Opcion, OpcionCreate, Pregunta, PreguntaCreate } from '../types/pregunta'
import type {
  CategoriaPrueba,
  CategoriaPruebaCreate,
  Prueba,
  PruebaCreate,
  PruebaUpdate,
  VersionPrueba,
} from '../types/prueba'

export const evaluacionService = {
  // --- categorías ---
  listarCategorias: () => apiClient.get<CategoriaPrueba[]>('/evaluaciones/categorias').then((r) => r.data),
  crearCategoria: (data: CategoriaPruebaCreate) =>
    apiClient.post<CategoriaPrueba>('/evaluaciones/categorias', data).then((r) => r.data),

  // --- pruebas ---
  listar: (params?: { categoria_id?: number; solo_activas?: boolean }) =>
    apiClient.get<Prueba[]>('/evaluaciones', { params }).then((r) => r.data),
  obtener: (id: number) => apiClient.get<Prueba>(`/evaluaciones/${id}`).then((r) => r.data),
  crear: (data: PruebaCreate) => apiClient.post<Prueba>('/evaluaciones', data).then((r) => r.data),
  actualizar: (id: number, data: PruebaUpdate) =>
    apiClient.put<Prueba>(`/evaluaciones/${id}`, data).then((r) => r.data),
  activar: (id: number) => apiClient.post<Prueba>(`/evaluaciones/${id}/activar`).then((r) => r.data),
  desactivar: (id: number) => apiClient.delete<Prueba>(`/evaluaciones/${id}`).then((r) => r.data),

  // --- versiones ---
  listarVersiones: (pruebaId: number) =>
    apiClient.get<VersionPrueba[]>(`/evaluaciones/${pruebaId}/versiones`).then((r) => r.data),
  crearVersion: (pruebaId: number, notas?: string) =>
    apiClient
      .post<VersionPrueba>(`/evaluaciones/${pruebaId}/versiones`, { notas: notas ?? null })
      .then((r) => r.data),
  activarVersion: (pruebaId: number, versionId: number) =>
    apiClient
      .post<VersionPrueba>(`/evaluaciones/${pruebaId}/versiones/${versionId}/activar`)
      .then((r) => r.data),

  // --- preguntas y opciones ---
  listarPreguntas: (versionId: number) =>
    apiClient.get<Pregunta[]>(`/evaluaciones/versiones/${versionId}/preguntas`).then((r) => r.data),
  crearPregunta: (versionId: number, data: PreguntaCreate) =>
    apiClient
      .post<Pregunta>(`/evaluaciones/versiones/${versionId}/preguntas`, data)
      .then((r) => r.data),
  desactivarPregunta: (preguntaId: number) =>
    apiClient.delete<Pregunta>(`/evaluaciones/preguntas/${preguntaId}`).then((r) => r.data),
  agregarOpcion: (preguntaId: number, data: OpcionCreate) =>
    apiClient
      .post<Opcion>(`/evaluaciones/preguntas/${preguntaId}/opciones`, data)
      .then((r) => r.data),
  eliminarOpcion: (opcionId: number) => apiClient.delete(`/evaluaciones/opciones/${opcionId}`),

  // --- algoritmo, factores y escalas ---
  listarAlgoritmos: (pruebaId: number) =>
    apiClient.get<Algoritmo[]>(`/evaluaciones/${pruebaId}/algoritmos`).then((r) => r.data),
  crearAlgoritmo: (pruebaId: number, data: AlgoritmoCreate) =>
    apiClient.post<Algoritmo>(`/evaluaciones/${pruebaId}/algoritmos`, data).then((r) => r.data),
  agregarFactor: (algoritmoId: number, data: FactorCreate) =>
    apiClient
      .post<Factor>(`/evaluaciones/algoritmos/${algoritmoId}/factores`, data)
      .then((r) => r.data),
  eliminarFactor: (factorId: number) => apiClient.delete(`/evaluaciones/factores/${factorId}`),
  agregarEscala: (factorId: number, data: EscalaCreate) =>
    apiClient.post<Escala>(`/evaluaciones/factores/${factorId}/escalas`, data).then((r) => r.data),
  eliminarEscala: (escalaId: number) => apiClient.delete(`/evaluaciones/escalas/${escalaId}`),
}
