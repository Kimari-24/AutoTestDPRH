export interface Empresa {
  id: number
  nombre_comercial: string
  razon_social: string | null
  correo_contacto: string | null
  telefono_contacto: string | null
  direccion: string | null
  activo: boolean
  creado_en: string
  total_candidatos: number
}

export interface EmpresaCreate {
  nombre_comercial: string
  razon_social?: string | null
  correo_contacto?: string | null
  telefono_contacto?: string | null
  direccion?: string | null
}

export type EmpresaUpdate = Partial<EmpresaCreate>
