"""
Servicio de gestión de evaluados (candidatos).

Cubre las capacidades de la sección 16 de los requisitos (listar,
buscar, filtrar, crear, editar, desactivar) y el expediente del
evaluado de la sección 17 (datos personales + evaluaciones
asignadas). La asignación de evaluaciones en sí (crear una
`Asignacion`) se implementa en la Fase 5, cuando exista el catálogo
de pruebas cargado; aquí solo se **muestran** las que ya existan.
"""

from sqlalchemy.orm import Session

from app.core.exceptions.base import ConflictError, NotFoundError, ValidationError
from app.models.aplicacion import Asignacion
from app.models.candidato import Candidato
from app.models.catalogos import Escolaridad, EstatusCandidato, Sexo
from app.repositories.auditoria_repository import BitacoraRepository
from app.repositories.candidato_repository import CandidatoRepository
from app.repositories.catalogo_repository import CatalogoRepository
from app.repositories.empresa_repository import EmpresaRepository
from app.schemas.candidato import (
    CandidatoCreate,
    CandidatoUpdate,
    EvaluacionAsignadaOut,
    ExpedienteCandidatoOut,
)


class CandidatoService:
    def __init__(self, db: Session):
        self.db = db
        self.candidatos = CandidatoRepository(db)
        self.empresas = EmpresaRepository(db)
        self.sexos = CatalogoRepository(db, Sexo)
        self.escolaridades = CatalogoRepository(db, Escolaridad)
        self.estatus_candidato = CatalogoRepository(db, EstatusCandidato)
        self.bitacora = BitacoraRepository(db)

    # --- consultas ---

    def listar(
        self,
        skip: int = 0,
        limit: int = 50,
        buscar: str | None = None,
        empresa_id: int | None = None,
        estatus_candidato_id: int | None = None,
        solo_activos: bool = False,
    ) -> list[Candidato]:
        return self.candidatos.list(
            skip=skip,
            limit=limit,
            buscar=buscar,
            empresa_id=empresa_id,
            estatus_candidato_id=estatus_candidato_id,
            solo_activos=solo_activos,
        )

    def obtener(self, candidato_id: int) -> Candidato:
        candidato = self.candidatos.get_by_id(candidato_id)
        if candidato is None:
            raise NotFoundError("Evaluado no encontrado.")
        return candidato

    def obtener_expediente(self, candidato_id: int) -> ExpedienteCandidatoOut:
        candidato = self.candidatos.get_expediente(candidato_id)
        if candidato is None:
            raise NotFoundError("Evaluado no encontrado.")

        evaluaciones: list[EvaluacionAsignadaOut] = []
        for asignacion in candidato.asignaciones:
            evaluaciones.append(self._asignacion_a_evaluacion_out(asignacion))

        from app.schemas.candidato import CandidatoOut

        return ExpedienteCandidatoOut(
            candidato=CandidatoOut.model_validate(candidato, from_attributes=True),
            evaluaciones=evaluaciones,
        )

    def _asignacion_a_evaluacion_out(self, asignacion: Asignacion) -> EvaluacionAsignadaOut:
        sesion = asignacion.sesiones[-1] if asignacion.sesiones else None
        codigo_estatus = asignacion.estatus.codigo if asignacion.estatus else "PENDIENTE"
        resultado_disponible = bool(sesion and sesion.resultado is not None)

        return EvaluacionAsignadaOut(
            asignacion_id=asignacion.id,
            prueba=asignacion.prueba.nombre if asignacion.prueba else "",
            categoria=(
                asignacion.prueba.categoria.nombre
                if asignacion.prueba and asignacion.prueba.categoria
                else ""
            ),
            estatus=codigo_estatus,
            fecha_asignacion=asignacion.fecha_asignacion,
            fecha_inicio=sesion.iniciada_en if sesion else None,
            fecha_finalizacion=sesion.finalizada_en if sesion else None,
            progreso_porcentaje=100 if codigo_estatus in ("COMPLETADA", "CALIFICADA") else 0,
            tiempo_disponible_minutos=(
                asignacion.prueba.tiempo_limite_minutos if asignacion.prueba else None
            ),
            resultado_disponible=resultado_disponible,
        )

    # --- comandos ---

    def crear(self, data: CandidatoCreate, creado_por_usuario_id: int | None = None) -> Candidato:
        if self.candidatos.get_by_correo(data.correo) is not None:
            raise ConflictError("Ya existe un evaluado registrado con ese correo.")

        if data.empresa_id is not None and self.empresas.get_by_id(data.empresa_id) is None:
            raise ValidationError("La empresa indicada no existe.")

        candidato = Candidato(
            nombre=data.nombre,
            apellidos=data.apellidos,
            correo=data.correo,
            puesto=data.puesto,
            fecha_nacimiento=data.fecha_nacimiento,
            empresa_id=data.empresa_id,
            sexo_id=self._resolver_catalogo(self.sexos, data.sexo_codigo, "sexo"),
            escolaridad_id=self._resolver_catalogo(
                self.escolaridades, data.escolaridad_codigo, "escolaridad"
            ),
            estatus_candidato_id=self._resolver_catalogo(
                self.estatus_candidato, data.estatus_candidato_codigo, "estatus de evaluado"
            ),
            activo=True,
        )
        self.candidatos.create(candidato)
        self.bitacora.registrar(
            usuario_id=creado_por_usuario_id,
            accion="CREAR",
            entidad="candidatos",
            entidad_id=candidato.id,
        )
        self.db.commit()
        return self.obtener(candidato.id)

    def actualizar(
        self,
        candidato_id: int,
        data: CandidatoUpdate,
        actualizado_por_usuario_id: int | None = None,
    ) -> Candidato:
        candidato = self.obtener(candidato_id)

        if data.correo and data.correo != candidato.correo:
            existente = self.candidatos.get_by_correo(data.correo)
            if existente is not None and existente.id != candidato.id:
                raise ConflictError("Ya existe un evaluado registrado con ese correo.")
            candidato.correo = data.correo

        if data.empresa_id is not None:
            if self.empresas.get_by_id(data.empresa_id) is None:
                raise ValidationError("La empresa indicada no existe.")
            candidato.empresa_id = data.empresa_id

        for campo in ("nombre", "apellidos", "puesto", "fecha_nacimiento"):
            valor = getattr(data, campo)
            if valor is not None:
                setattr(candidato, campo, valor)

        if data.sexo_codigo is not None:
            candidato.sexo_id = self._resolver_catalogo(self.sexos, data.sexo_codigo, "sexo")
        if data.escolaridad_codigo is not None:
            candidato.escolaridad_id = self._resolver_catalogo(
                self.escolaridades, data.escolaridad_codigo, "escolaridad"
            )
        if data.estatus_candidato_codigo is not None:
            candidato.estatus_candidato_id = self._resolver_catalogo(
                self.estatus_candidato, data.estatus_candidato_codigo, "estatus de evaluado"
            )

        self.candidatos.save()
        self.bitacora.registrar(
            usuario_id=actualizado_por_usuario_id,
            accion="ACTUALIZAR",
            entidad="candidatos",
            entidad_id=candidato.id,
        )
        self.db.commit()
        return self.obtener(candidato.id)

    def desactivar(
        self, candidato_id: int, desactivado_por_usuario_id: int | None = None
    ) -> Candidato:
        candidato = self.obtener(candidato_id)
        candidato.activo = False
        self.candidatos.save()
        self.bitacora.registrar(
            usuario_id=desactivado_por_usuario_id,
            accion="DESACTIVAR",
            entidad="candidatos",
            entidad_id=candidato.id,
        )
        self.db.commit()
        return candidato

    def _resolver_catalogo(
        self, repo: CatalogoRepository, codigo: str | None, etiqueta: str
    ) -> int | None:
        if codigo is None:
            return None
        item = repo.get_by_codigo(codigo)
        if item is None:
            raise ValidationError(f"El valor de {etiqueta} '{codigo}' no existe.")
        return item.id
