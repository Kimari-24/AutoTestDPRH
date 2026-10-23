export interface Escala {
  id: number
  factor_id: number
  codigo: string
  nombre: string
  valor_min: number | null
  valor_max: number | null
  descripcion: string | null
  orden: number
}

export interface EscalaCreate {
  codigo: string
  nombre: string
  valor_min?: number | null
  valor_max?: number | null
  descripcion?: string | null
  orden?: number
}

export interface Factor {
  id: number
  algoritmo_id: number
  codigo: string
  nombre: string
  descripcion: string | null
  orden: number
  escalas: Escala[]
}

export interface FactorCreate {
  codigo: string
  nombre: string
  descripcion?: string | null
  orden?: number
}

export interface Algoritmo {
  id: number
  prueba_id: number
  nombre: string
  tipo_calculo: string
  configuracion: Record<string, unknown> | null
  activo: boolean
  factores: Factor[]
}

export interface AlgoritmoCreate {
  nombre: string
  tipo_calculo: string
}
