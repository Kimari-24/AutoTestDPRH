"""
Servicio de administración del catálogo de pruebas.

Cubre la sección 18 de los requisitos: crear/editar evaluación,
activar/desactivar, crear versión, y configurar tiempo/instrucciones/
intentos. No genera ni valida contenido psicométrico: solo administra
la estructura (ver docs/ARQUITECTURA.md, sección 5 - motor universal).
"""

from sqlalchemy.orm import Session

from app.core.exceptions.base import ConflictError, NotFoundError, ValidationError
from app.models.catalogo_prueba import CategoriaPrueba, Prueba
from app.models.versionado import VersionPrueba
from app.repositories.auditoria_repository import BitacoraRepository
from app.repositories.prueba_repository import (
    CategoriaPruebaRepository,
    PruebaRepository,
    VersionPruebaRepository,
)
from app.schemas.prueba import CategoriaPruebaCreate, PruebaCreate, PruebaUpdate


class CategoriaPruebaService:
    def __init__(self, db: Session):
        self.db = db
        self.categorias = CategoriaPruebaRepository(db)

    def listar(self) -> list[CategoriaPrueba]:
        return self.categorias.list()

    def crear(self, data: CategoriaPruebaCreate) -> CategoriaPrueba:
        if self.categorias.get_by_codigo(data.codigo) is not None:
            raise ConflictError(f"Ya existe una categoría con código '{data.codigo}'.")
        categoria = CategoriaPrueba(
            codigo=data.codigo,
            nombre=data.nombre,
            descripcion=data.descripcion,
            orden=data.orden,
        )
        self.categorias.create(categoria)
        self.db.commit()
        return categoria


class PruebaService:
    def __init__(self, db: Session):
        self.db = db
        self.pruebas = PruebaRepository(db)
        self.categorias = CategoriaPruebaRepository(db)
        self.versiones = VersionPruebaRepository(db)
        self.bitacora = BitacoraRepository(db)

    def listar(
        self,
        skip: int = 0,
        limit: int = 50,
        categoria_id: int | None = None,
        solo_activas: bool = False,
    ) -> list[Prueba]:
        return self.pruebas.list(
            skip=skip, limit=limit, categoria_id=categoria_id, solo_activas=solo_activas
        )

    def obtener(self, prueba_id: int) -> Prueba:
        prueba = self.pruebas.get_by_id(prueba_id)
        if prueba is None:
            raise NotFoundError("Evaluación no encontrada.")
        return prueba

    def contar_preguntas_activas(self, prueba_id: int) -> int:
        return self.pruebas.count_preguntas_activas(prueba_id)

    def crear(self, data: PruebaCreate, creado_por_usuario_id: int | None = None) -> Prueba:
        categoria = self.categorias.get_by_codigo(data.categoria_codigo)
        if categoria is None:
            raise ValidationError(f"La categoría '{data.categoria_codigo}' no existe.")
        if self.pruebas.get_by_codigo(data.codigo) is not None:
            raise ConflictError(f"Ya existe una evaluación con código '{data.codigo}'.")

        prueba = Prueba(
            categoria_id=categoria.id,
            codigo=data.codigo,
            nombre=data.nombre,
            descripcion=data.descripcion,
            instrucciones=data.instrucciones,
            tiempo_limite_minutos=data.tiempo_limite_minutos,
            intentos_permitidos=data.intentos_permitidos,
            activa=True,
        )
        self.pruebas.create(prueba)
        self.bitacora.registrar(
            usuario_id=creado_por_usuario_id, accion="CREAR", entidad="pruebas", entidad_id=prueba.id
        )
        self.db.commit()
        return self.obtener(prueba.id)

    def actualizar(
        self, prueba_id: int, data: PruebaUpdate, actualizado_por_usuario_id: int | None = None
    ) -> Prueba:
        prueba = self.obtener(prueba_id)
        for campo, valor in data.model_dump(exclude_unset=True).items():
            setattr(prueba, campo, valor)
        self.pruebas.save()
        self.bitacora.registrar(
            usuario_id=actualizado_por_usuario_id,
            accion="ACTUALIZAR",
            entidad="pruebas",
            entidad_id=prueba.id,
        )
        self.db.commit()
        return self.obtener(prueba_id)

    def cambiar_estado(
        self, prueba_id: int, activa: bool, usuario_id: int | None = None
    ) -> Prueba:
        prueba = self.obtener(prueba_id)
        prueba.activa = activa
        self.pruebas.save()
        self.bitacora.registrar(
            usuario_id=usuario_id,
            accion="ACTIVAR" if activa else "DESACTIVAR",
            entidad="pruebas",
            entidad_id=prueba.id,
        )
        self.db.commit()
        return prueba

    # --- versiones ---

    def listar_versiones(self, prueba_id: int) -> list[VersionPrueba]:
        self.obtener(prueba_id)  # valida que exista
        return self.versiones.list_por_prueba(prueba_id)

    def crear_version(
        self, prueba_id: int, notas: str | None, usuario_id: int | None = None
    ) -> VersionPrueba:
        self.obtener(prueba_id)  # valida que exista
        version = self.versiones.create(prueba_id, notas=notas)
        self.bitacora.registrar(
            usuario_id=usuario_id,
            accion="CREAR",
            entidad="version_prueba",
            entidad_id=version.id,
        )
        self.db.commit()
        return version

    def activar_version(
        self, prueba_id: int, version_id: int, usuario_id: int | None = None
    ) -> VersionPrueba:
        self.obtener(prueba_id)  # valida que exista
        version = self.versiones.get_by_id(version_id)
        if version is None or version.prueba_id != prueba_id:
            raise NotFoundError("Versión no encontrada para esta evaluación.")

        self.versiones.desactivar_todas(prueba_id)
        version.activa = True
        self.versiones.save()
        self.bitacora.registrar(
            usuario_id=usuario_id,
            accion="ACTIVAR",
            entidad="version_prueba",
            entidad_id=version.id,
        )
        self.db.commit()
        return version
