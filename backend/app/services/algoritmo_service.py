"""
Servicio de administración del algoritmo de una prueba, sus factores
y sus escalas.

`tipo_calculo` y `configuracion` son la ESTRATEGIA genérica que el
motor universal ejecutará (Fase 6) — nunca una fórmula psicométrica
real. Los coeficientes/baremos concretos los aporta DPRH como datos.
"""

from sqlalchemy.orm import Session

from app.core.exceptions.base import NotFoundError, ValidationError
from app.models.catalogo_prueba import Algoritmo, Escala, Factor
from app.models.catalogos import TipoEscala, TipoFactor
from app.repositories.algoritmo_repository import (
    AlgoritmoRepository,
    EscalaRepository,
    FactorRepository,
)
from app.repositories.auditoria_repository import BitacoraRepository
from app.repositories.catalogo_repository import CatalogoRepository
from app.repositories.prueba_repository import PruebaRepository
from app.schemas.algoritmo import (
    AlgoritmoCreate,
    AlgoritmoUpdate,
    EscalaCreate,
    EscalaUpdate,
    FactorCreate,
    FactorUpdate,
)


class AlgoritmoService:
    def __init__(self, db: Session):
        self.db = db
        self.algoritmos = AlgoritmoRepository(db)
        self.factores = FactorRepository(db)
        self.escalas = EscalaRepository(db)
        self.pruebas = PruebaRepository(db)
        self.tipos_factor = CatalogoRepository(db, TipoFactor)
        self.tipos_escala = CatalogoRepository(db, TipoEscala)
        self.bitacora = BitacoraRepository(db)

    # --- algoritmo ---

    def listar_por_prueba(self, prueba_id: int) -> list[Algoritmo]:
        if self.pruebas.get_by_id(prueba_id) is None:
            raise NotFoundError("Evaluación no encontrada.")
        return self.algoritmos.list_por_prueba(prueba_id)

    def obtener(self, algoritmo_id: int) -> Algoritmo:
        algoritmo = self.algoritmos.get_by_id(algoritmo_id)
        if algoritmo is None:
            raise NotFoundError("Algoritmo no encontrado.")
        return algoritmo

    def crear(
        self, prueba_id: int, data: AlgoritmoCreate, usuario_id: int | None = None
    ) -> Algoritmo:
        if self.pruebas.get_by_id(prueba_id) is None:
            raise NotFoundError("Evaluación no encontrada.")

        algoritmo = Algoritmo(
            prueba_id=prueba_id,
            nombre=data.nombre,
            tipo_calculo=data.tipo_calculo,
            configuracion=data.configuracion,
            activo=True,
        )
        self.algoritmos.create(algoritmo)
        self.bitacora.registrar(
            usuario_id=usuario_id, accion="CREAR", entidad="algoritmos", entidad_id=algoritmo.id
        )
        self.db.commit()
        return self.obtener(algoritmo.id)

    def actualizar(
        self, algoritmo_id: int, data: AlgoritmoUpdate, usuario_id: int | None = None
    ) -> Algoritmo:
        algoritmo = self.obtener(algoritmo_id)
        for campo, valor in data.model_dump(exclude_unset=True).items():
            setattr(algoritmo, campo, valor)
        self.algoritmos.save()
        self.bitacora.registrar(
            usuario_id=usuario_id,
            accion="ACTUALIZAR",
            entidad="algoritmos",
            entidad_id=algoritmo.id,
        )
        self.db.commit()
        return self.obtener(algoritmo_id)

    # --- factores ---

    def agregar_factor(
        self, algoritmo_id: int, data: FactorCreate, usuario_id: int | None = None
    ) -> Factor:
        algoritmo = self.obtener(algoritmo_id)
        tipo_factor_id = self._resolver_tipo_factor(data.tipo_factor_codigo)

        factor = Factor(
            algoritmo_id=algoritmo.id,
            tipo_factor_id=tipo_factor_id,
            codigo=data.codigo,
            nombre=data.nombre,
            descripcion=data.descripcion,
            configuracion=data.configuracion,
            orden=data.orden,
        )
        self.factores.create(factor)
        self.bitacora.registrar(
            usuario_id=usuario_id, accion="CREAR", entidad="factores", entidad_id=factor.id
        )
        self.db.commit()
        return self.factores.get_by_id(factor.id)

    def actualizar_factor(
        self, factor_id: int, data: FactorUpdate, usuario_id: int | None = None
    ) -> Factor:
        factor = self.factores.get_by_id(factor_id)
        if factor is None:
            raise NotFoundError("Factor no encontrado.")

        if data.tipo_factor_codigo is not None:
            factor.tipo_factor_id = self._resolver_tipo_factor(data.tipo_factor_codigo)

        for campo in ("codigo", "nombre", "descripcion", "configuracion", "orden"):
            valor = getattr(data, campo)
            if valor is not None:
                setattr(factor, campo, valor)

        self.factores.save()
        self.bitacora.registrar(
            usuario_id=usuario_id, accion="ACTUALIZAR", entidad="factores", entidad_id=factor.id
        )
        self.db.commit()
        return self.factores.get_by_id(factor_id)

    def eliminar_factor(self, factor_id: int, usuario_id: int | None = None) -> None:
        factor = self.factores.get_by_id(factor_id)
        if factor is None:
            raise NotFoundError("Factor no encontrado.")
        self.bitacora.registrar(
            usuario_id=usuario_id, accion="ELIMINAR", entidad="factores", entidad_id=factor_id
        )
        self.factores.delete(factor)
        self.db.commit()

    # --- escalas ---

    def agregar_escala(
        self, factor_id: int, data: EscalaCreate, usuario_id: int | None = None
    ) -> Escala:
        factor = self.factores.get_by_id(factor_id)
        if factor is None:
            raise NotFoundError("Factor no encontrado.")
        tipo_escala_id = self._resolver_tipo_escala(data.tipo_escala_codigo)

        escala = Escala(
            factor_id=factor.id,
            tipo_escala_id=tipo_escala_id,
            codigo=data.codigo,
            nombre=data.nombre,
            valor_min=data.valor_min,
            valor_max=data.valor_max,
            descripcion=data.descripcion,
            orden=data.orden,
        )
        self.escalas.create(escala)
        self.bitacora.registrar(
            usuario_id=usuario_id, accion="CREAR", entidad="escalas", entidad_id=escala.id
        )
        self.db.commit()
        return escala

    def actualizar_escala(
        self, escala_id: int, data: EscalaUpdate, usuario_id: int | None = None
    ) -> Escala:
        escala = self.escalas.get_by_id(escala_id)
        if escala is None:
            raise NotFoundError("Escala no encontrada.")

        if data.tipo_escala_codigo is not None:
            escala.tipo_escala_id = self._resolver_tipo_escala(data.tipo_escala_codigo)

        for campo in ("codigo", "nombre", "valor_min", "valor_max", "descripcion", "orden"):
            valor = getattr(data, campo)
            if valor is not None:
                setattr(escala, campo, valor)

        # El schema solo ve lo que viene en la petición; aquí se valida el
        # rango final contra los valores que ya tenía guardados (BUG-16).
        if (
            escala.valor_min is not None
            and escala.valor_max is not None
            and escala.valor_min > escala.valor_max
        ):
            self.db.rollback()
            raise ValidationError("valor_min no puede ser mayor que valor_max.")

        self.escalas.save()
        self.bitacora.registrar(
            usuario_id=usuario_id, accion="ACTUALIZAR", entidad="escalas", entidad_id=escala.id
        )
        self.db.commit()
        return escala

    def eliminar_escala(self, escala_id: int, usuario_id: int | None = None) -> None:
        escala = self.escalas.get_by_id(escala_id)
        if escala is None:
            raise NotFoundError("Escala no encontrada.")
        self.bitacora.registrar(
            usuario_id=usuario_id, accion="ELIMINAR", entidad="escalas", entidad_id=escala_id
        )
        self.escalas.delete(escala)
        self.db.commit()

    # --- helpers ---

    def _resolver_tipo_factor(self, codigo: str | None) -> int | None:
        if codigo is None:
            return None
        tipo = self.tipos_factor.get_by_codigo(codigo)
        if tipo is None:
            raise ValidationError(f"El tipo de factor '{codigo}' no existe.")
        return tipo.id

    def _resolver_tipo_escala(self, codigo: str | None) -> int | None:
        if codigo is None:
            return None
        tipo = self.tipos_escala.get_by_codigo(codigo)
        if tipo is None:
            raise ValidationError(f"El tipo de escala '{codigo}' no existe.")
        return tipo.id
