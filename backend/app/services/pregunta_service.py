"""
Servicio de administración de preguntas y opciones dentro de una
versión de una prueba.

No valida contenido psicométrico (claves correctas, puntajes): solo
administra la estructura genérica (enunciado, tipo, opciones) que el
motor universal usará en la Fase 6.
"""

from sqlalchemy.orm import Session

from app.core.exceptions.base import ConflictError, NotFoundError, ValidationError
from app.models.catalogo_prueba import Opcion, Pregunta
from app.models.catalogos import TipoPregunta
from app.repositories.auditoria_repository import BitacoraRepository
from app.repositories.catalogo_repository import CatalogoRepository
from app.repositories.pregunta_repository import OpcionRepository, PreguntaRepository
from app.repositories.prueba_repository import VersionPruebaRepository
from app.schemas.pregunta import OpcionCreate, OpcionUpdate, PreguntaCreate, PreguntaUpdate


class PreguntaService:
    def __init__(self, db: Session):
        self.db = db
        self.preguntas = PreguntaRepository(db)
        self.opciones = OpcionRepository(db)
        self.versiones = VersionPruebaRepository(db)
        self.tipos_pregunta = CatalogoRepository(db, TipoPregunta)
        self.bitacora = BitacoraRepository(db)

    def _validar_version(self, version_prueba_id: int) -> None:
        if self.versiones.get_by_id(version_prueba_id) is None:
            raise NotFoundError("Versión de evaluación no encontrada.")

    def listar_por_version(self, version_prueba_id: int) -> list[Pregunta]:
        self._validar_version(version_prueba_id)
        return self.preguntas.list_por_version(version_prueba_id)

    def obtener(self, pregunta_id: int) -> Pregunta:
        pregunta = self.preguntas.get_by_id(pregunta_id)
        if pregunta is None:
            raise NotFoundError("Pregunta no encontrada.")
        return pregunta

    def crear(
        self,
        version_prueba_id: int,
        data: PreguntaCreate,
        usuario_id: int | None = None,
    ) -> Pregunta:
        self._validar_version(version_prueba_id)

        tipo = self.tipos_pregunta.get_by_codigo(data.tipo_pregunta_codigo)
        if tipo is None:
            raise ValidationError(
                f"El tipo de pregunta '{data.tipo_pregunta_codigo}' no existe."
            )

        pregunta = Pregunta(
            version_prueba_id=version_prueba_id,
            tipo_pregunta_id=tipo.id,
            enunciado=data.enunciado,
            imagen_url=data.imagen_url,
            configuracion=data.configuracion,
            orden=data.orden,
            activa=True,
        )
        for opcion_data in data.opciones:
            pregunta.opciones.append(
                Opcion(
                    texto=opcion_data.texto,
                    imagen_url=opcion_data.imagen_url,
                    valor=opcion_data.valor,
                    orden=opcion_data.orden,
                )
            )

        self.preguntas.create(pregunta)
        self.bitacora.registrar(
            usuario_id=usuario_id, accion="CREAR", entidad="preguntas", entidad_id=pregunta.id
        )
        self.db.commit()
        return self.obtener(pregunta.id)

    def actualizar(
        self, pregunta_id: int, data: PreguntaUpdate, usuario_id: int | None = None
    ) -> Pregunta:
        pregunta = self.obtener(pregunta_id)

        if data.tipo_pregunta_codigo is not None:
            tipo = self.tipos_pregunta.get_by_codigo(data.tipo_pregunta_codigo)
            if tipo is None:
                raise ValidationError(
                    f"El tipo de pregunta '{data.tipo_pregunta_codigo}' no existe."
                )
            pregunta.tipo_pregunta_id = tipo.id

        for campo in ("enunciado", "imagen_url", "configuracion", "orden"):
            valor = getattr(data, campo)
            if valor is not None:
                setattr(pregunta, campo, valor)

        self.preguntas.save()
        self.bitacora.registrar(
            usuario_id=usuario_id,
            accion="ACTUALIZAR",
            entidad="preguntas",
            entidad_id=pregunta.id,
        )
        self.db.commit()
        return self.obtener(pregunta_id)

    def desactivar(self, pregunta_id: int, usuario_id: int | None = None) -> Pregunta:
        pregunta = self.obtener(pregunta_id)
        pregunta.activa = False
        self.preguntas.save()
        self.bitacora.registrar(
            usuario_id=usuario_id,
            accion="DESACTIVAR",
            entidad="preguntas",
            entidad_id=pregunta.id,
        )
        self.db.commit()
        return pregunta

    # --- opciones ---

    def agregar_opcion(
        self, pregunta_id: int, data: OpcionCreate, usuario_id: int | None = None
    ) -> Opcion:
        pregunta = self.obtener(pregunta_id)
        opcion = Opcion(
            pregunta_id=pregunta.id,
            texto=data.texto,
            imagen_url=data.imagen_url,
            valor=data.valor,
            orden=data.orden,
        )
        self.opciones.create(opcion)
        self.bitacora.registrar(
            usuario_id=usuario_id, accion="CREAR", entidad="opciones", entidad_id=opcion.id
        )
        self.db.commit()
        return opcion

    def actualizar_opcion(
        self, opcion_id: int, data: OpcionUpdate, usuario_id: int | None = None
    ) -> Opcion:
        opcion = self.opciones.get_by_id(opcion_id)
        if opcion is None:
            raise NotFoundError("Opción no encontrada.")

        for campo, valor in data.model_dump(exclude_unset=True).items():
            setattr(opcion, campo, valor)

        self.opciones.save()
        self.bitacora.registrar(
            usuario_id=usuario_id, accion="ACTUALIZAR", entidad="opciones", entidad_id=opcion.id
        )
        self.db.commit()
        return opcion

    def eliminar_opcion(self, opcion_id: int, usuario_id: int | None = None) -> None:
        opcion = self.opciones.get_by_id(opcion_id)
        if opcion is None:
            raise NotFoundError("Opción no encontrada.")
        if self.opciones.tiene_respuestas_asociadas(opcion_id):
            raise ConflictError(
                "No se puede eliminar la opción: ya tiene respuestas de evaluados registradas."
            )
        self.bitacora.registrar(
            usuario_id=usuario_id, accion="ELIMINAR", entidad="opciones", entidad_id=opcion_id
        )
        self.opciones.delete(opcion)
        self.db.commit()
