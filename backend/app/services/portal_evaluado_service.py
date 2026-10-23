"""
Servicio del portal del evaluado (sección 6 de los requisitos: flujo
completo desde que ve sus evaluaciones asignadas hasta que termina).

Toda operación aquí valida que la sesión/asignación pertenezca al
candidato autenticado — un evaluado nunca debe poder leer ni escribir
datos de otro evaluado.
"""

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session, selectinload

from app.core.exceptions.base import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.engine.motor import MotorEvaluacion
from app.models.aplicacion import Asignacion, Respuesta, SesionPrueba
from app.models.catalogo_prueba import Pregunta
from app.models.catalogos import EstatusPrueba
from app.repositories.asignacion_repository import AsignacionRepository
from app.repositories.auditoria_repository import BitacoraRepository
from app.repositories.prueba_repository import VersionPruebaRepository
from app.repositories.sesion_prueba_repository import RespuestaRepository, SesionPruebaRepository
from app.schemas.portal import (
    GuardarRespuestaRequest,
    IniciarSesionOut,
    MiEvaluacionOut,
    OpcionPortalOut,
    PreguntaPortalOut,
    ProgresoSesionOut,
)

logger = logging.getLogger("autotest_dprh")


class PortalEvaluadoService:
    def __init__(self, db: Session):
        self.db = db
        self.asignaciones = AsignacionRepository(db)
        self.sesiones = SesionPruebaRepository(db)
        self.respuestas = RespuestaRepository(db)
        self.versiones = VersionPruebaRepository(db)
        self.bitacora = BitacoraRepository(db)

    # -- helpers de seguridad / estatus -----------------------------------

    def _estatus_id(self, codigo: str) -> int:
        estatus = self.db.query(EstatusPrueba).filter(EstatusPrueba.codigo == codigo).first()
        if estatus is None:
            raise ValidationError(f"Falta el estatus_prueba '{codigo}'. Ejecuta scripts/seed_catalogos.py.")
        return estatus.id

    def _obtener_asignacion_del_candidato(self, candidato_id: int, asignacion_id: int) -> Asignacion:
        asignacion = self.asignaciones.get_by_id(asignacion_id)
        if asignacion is None:
            raise NotFoundError("Evaluación asignada no encontrada.")
        if asignacion.candidato_id != candidato_id:
            raise ForbiddenError("Esta evaluación no está asignada a tu usuario.")
        return asignacion

    def _obtener_sesion_del_candidato(self, candidato_id: int, sesion_id: int) -> SesionPrueba:
        sesion = self.sesiones.get_by_id(sesion_id)
        if sesion is None:
            raise NotFoundError("Sesión no encontrada.")
        if sesion.asignacion.candidato_id != candidato_id:
            raise ForbiddenError("Esta sesión no pertenece a tu usuario.")
        return sesion

    @staticmethod
    def _plazo_vencido(asignacion: Asignacion) -> bool:
        """La `fecha_limite` de la asignación ya pasó (BUG-03 de QA)."""
        limite = asignacion.fecha_limite
        if limite is None:
            return False
        if limite.tzinfo is None:
            limite = limite.replace(tzinfo=timezone.utc)
        return limite < datetime.now(timezone.utc)

    def _actualizar_tiempo_restante(self, sesion: SesionPrueba) -> int | None:
        """Recalcula el tiempo restante a partir de `iniciada_en` y el
        límite de la prueba, y expira la sesión automáticamente si ya
        se agotó (sección 6, "temporizador")."""
        prueba = sesion.asignacion.prueba
        if not prueba.tiempo_limite_minutos:
            return None

        limite_segundos = prueba.tiempo_limite_minutos * 60
        transcurridos = (datetime.now(timezone.utc) - sesion.iniciada_en).total_seconds()
        restante = max(0, int(limite_segundos - transcurridos))
        sesion.tiempo_restante_segundos = restante

        if restante <= 0 and sesion.estatus.codigo == "EN_PROCESO":
            sesion.estatus_prueba_id = self._estatus_id("EXPIRADA")
            sesion.finalizada_en = datetime.now(timezone.utc)
            sesion.asignacion.estatus_prueba_id = self._estatus_id("EXPIRADA")
            self.sesiones.save()
            self.db.commit()

        return restante

    # -- mis evaluaciones ---------------------------------------------------

    def listar_mis_evaluaciones(self, candidato_id: int) -> list[MiEvaluacionOut]:
        asignaciones = self.asignaciones.list_por_candidato(candidato_id)

        # La expiración por tiempo se evalúa "perezosamente" (al consultar),
        # así que antes de listar se revisan las sesiones en proceso para
        # que una evaluación vencida no aparezca como todavía iniciable.
        hubo_cambios = False
        for a in asignaciones:
            if a.estatus.codigo == "EN_PROCESO":
                sesion = self.asignaciones.get_sesion_en_proceso(a.id)
                if sesion is not None:
                    restante = self._actualizar_tiempo_restante(sesion)
                    if restante is not None and restante <= 0:
                        hubo_cambios = True
        if hubo_cambios:
            self.db.expire_all()
            asignaciones = self.asignaciones.list_por_candidato(candidato_id)

        resultado = []
        for a in asignaciones:
            resultado.append(
                MiEvaluacionOut(
                    asignacion_id=a.id,
                    prueba_nombre=a.prueba.nombre,
                    estatus=a.estatus.codigo,
                    fecha_asignacion=a.fecha_asignacion,
                    fecha_limite=a.fecha_limite,
                    tiempo_limite_minutos=a.prueba.tiempo_limite_minutos,
                    puede_iniciar=(
                        a.estatus.codigo in ("PENDIENTE", "EN_PROCESO")
                        and not (a.estatus.codigo == "PENDIENTE" and self._plazo_vencido(a))
                    ),
                )
            )
        return resultado

    # -- iniciar / continuar ------------------------------------------------

    def iniciar_o_continuar(self, candidato_id: int, asignacion_id: int) -> IniciarSesionOut:
        asignacion = self._obtener_asignacion_del_candidato(candidato_id, asignacion_id)

        if asignacion.estatus.codigo not in ("PENDIENTE", "EN_PROCESO"):
            raise ConflictError(
                f"Esta evaluación no se puede iniciar (estatus: {asignacion.estatus.codigo})."
            )

        sesion_en_proceso = self.asignaciones.get_sesion_en_proceso(asignacion_id)
        if sesion_en_proceso is not None:
            restante = self._actualizar_tiempo_restante(sesion_en_proceso)
            if restante is not None and restante <= 0:
                raise ConflictError("El tiempo de esta evaluación ya expiró.")
            return IniciarSesionOut(
                sesion_id=sesion_en_proceso.id,
                estatus=sesion_en_proceso.estatus.codigo,
                tiempo_restante_segundos=sesion_en_proceso.tiempo_restante_segundos,
            )

        # BUG-03 de QA: pasada la fecha límite ya no se puede empezar.
        if self._plazo_vencido(asignacion):
            asignacion.estatus_prueba_id = self._estatus_id("EXPIRADA")
            self.asignaciones.save()
            self.db.commit()
            raise ConflictError("La fecha límite para realizar esta evaluación ya venció.")

        # BUG-11 de QA: sin versión con preguntas no se puede iniciar, y
        # eso no debe consumir un intento del evaluado.
        if asignacion.version_prueba_id is None:
            version_vigente = self.versiones.get_version_activa(asignacion.prueba_id)
            if version_vigente is not None:
                asignacion.version_prueba_id = version_vigente.id
        if asignacion.version_prueba_id is None:
            raise ConflictError("Esta evaluación todavía no está disponible (sin versión vigente).")
        preguntas_activas = (
            self.db.query(Pregunta)
            .filter(
                Pregunta.version_prueba_id == asignacion.version_prueba_id,
                Pregunta.activa.is_(True),
            )
            .count()
        )
        if preguntas_activas == 0:
            raise ConflictError("Esta evaluación todavía no tiene preguntas disponibles.")

        intentos_ya_usados = self.asignaciones.count_sesiones(asignacion_id)
        if intentos_ya_usados >= asignacion.prueba.intentos_permitidos:
            raise ConflictError("Ya se agotaron los intentos permitidos para esta evaluación.")

        tiempo_limite_segundos = (
            asignacion.prueba.tiempo_limite_minutos * 60
            if asignacion.prueba.tiempo_limite_minutos
            else None
        )

        sesion = SesionPrueba(
            asignacion_id=asignacion.id,
            estatus_prueba_id=self._estatus_id("EN_PROCESO"),
            iniciada_en=datetime.now(timezone.utc),
            ultima_actividad_en=datetime.now(timezone.utc),
            tiempo_restante_segundos=tiempo_limite_segundos,
        )
        self.sesiones.create(sesion)

        asignacion.estatus_prueba_id = self._estatus_id("EN_PROCESO")
        self.asignaciones.save()
        self.db.commit()

        return IniciarSesionOut(
            sesion_id=sesion.id, estatus="EN_PROCESO", tiempo_restante_segundos=tiempo_limite_segundos
        )

    # -- preguntas ------------------------------------------------------------

    def obtener_preguntas(self, candidato_id: int, sesion_id: int) -> list[PreguntaPortalOut]:
        sesion = self._obtener_sesion_del_candidato(candidato_id, sesion_id)
        version_id = sesion.asignacion.version_prueba_id
        if version_id is None:
            raise ValidationError("Esta asignación no tiene una versión de evaluación fijada.")

        preguntas = (
            self.db.query(Pregunta)
            .options(selectinload(Pregunta.opciones))
            .filter(Pregunta.version_prueba_id == version_id, Pregunta.activa.is_(True))
            .order_by(Pregunta.orden)
            .all()
        )

        respuestas_por_pregunta = {
            r.pregunta_id: r for r in self.respuestas.list_por_sesion(sesion_id)
        }

        salida = []
        for p in preguntas:
            respuesta_existente = respuestas_por_pregunta.get(p.id)
            respuesta_actual = None
            if respuesta_existente is not None:
                respuesta_actual = (
                    str(respuesta_existente.opcion_id)
                    if respuesta_existente.opcion_id is not None
                    else respuesta_existente.valor
                )
            salida.append(
                PreguntaPortalOut(
                    id=p.id,
                    tipo_pregunta_codigo=p.tipo_pregunta.codigo,
                    enunciado=p.enunciado,
                    imagen_url=p.imagen_url,
                    orden=p.orden,
                    opciones=[
                        OpcionPortalOut(id=o.id, texto=o.texto, imagen_url=o.imagen_url, orden=o.orden)
                        for o in sorted(p.opciones, key=lambda o: o.orden)
                    ],
                    respuesta_actual=respuesta_actual,
                )
            )
        return salida

    # -- respuestas (autoguardado) ---------------------------------------------

    def guardar_respuesta(
        self, candidato_id: int, sesion_id: int, pregunta_id: int, data: GuardarRespuestaRequest
    ) -> None:
        sesion = self._obtener_sesion_del_candidato(candidato_id, sesion_id)

        if sesion.estatus.codigo != "EN_PROCESO":
            raise ConflictError(
                f"No se pueden modificar respuestas: la sesión está {sesion.estatus.codigo}."
            )

        restante = self._actualizar_tiempo_restante(sesion)
        if restante is not None and restante <= 0:
            raise ConflictError("El tiempo para esta evaluación ya expiró.")

        pregunta = self.db.get(Pregunta, pregunta_id)
        if pregunta is None or pregunta.version_prueba_id != sesion.asignacion.version_prueba_id:
            raise ValidationError("Esa pregunta no pertenece a esta evaluación.")

        existente = self.respuestas.get_por_sesion_y_pregunta(sesion_id, pregunta_id)
        if existente is not None:
            existente.opcion_id = data.opcion_id
            existente.valor = data.valor
            existente.respondida_en = datetime.now(timezone.utc)
        else:
            self.respuestas.create(
                Respuesta(
                    sesion_prueba_id=sesion_id,
                    pregunta_id=pregunta_id,
                    opcion_id=data.opcion_id,
                    valor=data.valor,
                    respondida_en=datetime.now(timezone.utc),
                )
            )

        sesion.ultima_actividad_en = datetime.now(timezone.utc)
        self.sesiones.save()
        self.db.commit()

    # -- progreso ------------------------------------------------------------

    def obtener_progreso(self, candidato_id: int, sesion_id: int) -> ProgresoSesionOut:
        sesion = self._obtener_sesion_del_candidato(candidato_id, sesion_id)
        restante = self._actualizar_tiempo_restante(sesion)
        self.db.refresh(sesion)

        total = (
            self.db.query(Pregunta)
            .filter(
                Pregunta.version_prueba_id == sesion.asignacion.version_prueba_id,
                Pregunta.activa.is_(True),
            )
            .count()
        )
        respondidas = len(self.respuestas.list_por_sesion(sesion_id))
        porcentaje = int((respondidas / total) * 100) if total else 0

        return ProgresoSesionOut(
            total_preguntas=total,
            preguntas_respondidas=respondidas,
            porcentaje=porcentaje,
            tiempo_restante_segundos=restante,
            estatus=sesion.estatus.codigo,
        )

    # -- finalizar ------------------------------------------------------------

    def finalizar(self, candidato_id: int, sesion_id: int) -> ProgresoSesionOut:
        sesion = self._obtener_sesion_del_candidato(candidato_id, sesion_id)
        if sesion.estatus.codigo != "EN_PROCESO":
            raise ConflictError(f"Esta sesión ya está {sesion.estatus.codigo}.")

        sesion.finalizada_en = datetime.now(timezone.utc)
        sesion.estatus_prueba_id = self._estatus_id("COMPLETADA")
        sesion.asignacion.estatus_prueba_id = self._estatus_id("COMPLETADA")
        self.sesiones.save()
        self.bitacora.registrar(
            usuario_id=None, accion="FINALIZAR", entidad="sesiones_prueba", entidad_id=sesion.id
        )
        self.db.commit()

        # El motor procesa las respuestas automáticamente (sección 6,
        # paso 16). Si la evaluación todavía no tiene un algoritmo
        # activo configurado, se deja la sesión en COMPLETADA para que
        # el administrador la califique más tarde manualmente.
        try:
            MotorEvaluacion(self.db).calcular(sesion.id)
            self.db.refresh(sesion)
        except ValidationError as exc:
            # La sesión queda COMPLETADA (sin calificar) para que el
            # administrador la califique cuando la evaluación esté lista.
            logger.warning(
                "Sesión %s finalizada pero sin calificar automáticamente: %s", sesion.id, exc.detail
            )

        return self.obtener_progreso(candidato_id, sesion_id)
