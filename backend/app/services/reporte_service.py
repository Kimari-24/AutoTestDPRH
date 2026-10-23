"""Servicio de reportes: junta los datos ya calculados (candidato,
empresa, evaluación, resultado, factores, escalas) y delega el
renderizado a `app/reportes/pdf_reporte.py`."""

from sqlalchemy.orm import Session, selectinload

from app.core.exceptions.base import ConflictError, NotFoundError
from app.models.aplicacion import Asignacion, Resultado, ResultadoEscala, ResultadoFactor, SesionPrueba
from app.models.candidato import Candidato
from app.models.catalogo_prueba import Prueba
from app.reportes.pdf_reporte import generar_pdf_resultado


class ReporteService:
    def __init__(self, db: Session):
        self.db = db

    def generar_pdf_resultado(self, sesion_prueba_id: int) -> bytes:
        sesion = (
            self.db.query(SesionPrueba)
            .options(
                selectinload(SesionPrueba.asignacion).selectinload(Asignacion.candidato).selectinload(Candidato.empresa),
                selectinload(SesionPrueba.asignacion).selectinload(Asignacion.prueba).selectinload(Prueba.categoria),
            )
            .filter(SesionPrueba.id == sesion_prueba_id)
            .first()
        )
        if sesion is None:
            raise NotFoundError("Sesión de prueba no encontrada.")

        resultado = (
            self.db.query(Resultado)
            .options(
                selectinload(Resultado.resultado_factores).selectinload(ResultadoFactor.factor),
                selectinload(Resultado.resultado_escalas).selectinload(ResultadoEscala.escala),
            )
            .filter(Resultado.sesion_prueba_id == sesion_prueba_id)
            .first()
        )
        if resultado is None:
            raise ConflictError(
                "Esta sesión todavía no tiene un resultado calculado. "
                "Usa POST /api/resultados/sesiones/{id}/calcular primero."
            )

        candidato = sesion.asignacion.candidato
        prueba = sesion.asignacion.prueba
        empresa = candidato.empresa

        datos = {
            "candidato": {
                "nombre": candidato.nombre,
                "apellidos": candidato.apellidos,
                "correo": candidato.correo,
                "puesto": candidato.puesto,
            },
            "empresa": {"nombre_comercial": empresa.nombre_comercial} if empresa else None,
            "prueba": {
                "nombre": prueba.nombre,
                "categoria": prueba.categoria.nombre if prueba.categoria else None,
            },
            "resultado": {
                "calculado_en": resultado.calculado_en,
                "puntuacion_global": resultado.puntuacion_global,
                "puntuacion_normalizada": resultado.puntuacion_normalizada,
                "interpretacion_global": resultado.interpretacion_global,
            },
            "factores": [
                {
                    "nombre": rf.factor.nombre,
                    "codigo": rf.factor.codigo,
                    "puntuacion": rf.puntuacion,
                    "interpretacion": rf.interpretacion,
                }
                for rf in resultado.resultado_factores
            ],
            "escalas": [
                {
                    "nombre": re.escala.nombre,
                    "codigo": re.escala.codigo,
                    "valor": re.valor,
                    "interpretacion": re.interpretacion,
                }
                for re in resultado.resultado_escalas
            ],
        }

        return generar_pdf_resultado(datos)
