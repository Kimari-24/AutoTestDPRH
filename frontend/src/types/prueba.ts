export interface CategoriaPrueba {
  id: number
  codigo: string
  nombre: string
  descripcion: string | null
  orden: number
}

export interface CategoriaPruebaCreate {
  codigo: string
  nombre: string
  descripcion?: string | null
  orden?: number
}

export interface Prueba {
  id: number
  codigo: string
  nombre: string
  descripcion: string | null
  instrucciones: string | null
  tiempo_limite_minutos: number | null
  intentos_permitidos: number
  activa: boolean
  categoria: CategoriaPrueba
  total_preguntas_activas: number
  creado_en: string
}

export interface PruebaCreate {
  categoria_codigo: string
  codigo: string
  nombre: string
  descripcion?: string | null
  instrucciones?: string | null
  tiempo_limite_minutos?: number | null
  intentos_permitidos?: number
}

export type PruebaUpdate = Partial<
  Pick<PruebaCreate, 'descripcion' | 'instrucciones' | 'tiempo_limite_minutos' | 'intentos_permitidos'> & {
    nombre: string
  }
>

export interface VersionPrueba {
  id: number
  prueba_id: number
  numero_version: number
  activa: boolean
  notas: string | null
  creado_en: string
  total_preguntas: number
}
