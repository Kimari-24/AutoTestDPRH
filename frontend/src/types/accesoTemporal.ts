export interface AccesoTemporalCreado {
  id: number
  usuario: string
  password_temporal: string
  expira_en: string
}

export interface AccesoTemporal {
  id: number
  usuario: string
  creado_en: string
  expira_en: string
  intentos_fallidos: number
  ultimo_acceso: string | null
  sesion_activa: boolean
  revocado: boolean
}

export interface Asignacion {
  id: number
  prueba_id: number
  prueba_nombre: string
  estatus: string
  fecha_asignacion: string
  fecha_limite: string | null
}
