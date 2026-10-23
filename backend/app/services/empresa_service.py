"""
Servicio de gestión de empresas.

El rol funcional EMPRESA no está habilitado en esta versión (ver
docs/ARQUITECTURA.md); este servicio cubre únicamente la capacidad
del ADMINISTRADOR de administrar el catálogo de empresas clientes de
DPRH (crear, editar, desactivar, listar).
"""

from sqlalchemy.orm import Session

from app.core.exceptions.base import NotFoundError
from app.models.empresa import Empresa
from app.repositories.auditoria_repository import BitacoraRepository
from app.repositories.empresa_repository import EmpresaRepository
from app.schemas.empresa import EmpresaCreate, EmpresaUpdate


class EmpresaService:
    def __init__(self, db: Session):
        self.db = db
        self.empresas = EmpresaRepository(db)
        self.bitacora = BitacoraRepository(db)

    def listar(
        self,
        skip: int = 0,
        limit: int = 50,
        buscar: str | None = None,
        solo_activas: bool = False,
    ) -> list[Empresa]:
        return self.empresas.list(skip=skip, limit=limit, buscar=buscar, solo_activas=solo_activas)

    def obtener(self, empresa_id: int) -> Empresa:
        empresa = self.empresas.get_by_id(empresa_id)
        if empresa is None:
            raise NotFoundError("Empresa no encontrada.")
        return empresa

    def crear(self, data: EmpresaCreate, creado_por_usuario_id: int | None = None) -> Empresa:
        empresa = Empresa(
            nombre_comercial=data.nombre_comercial,
            razon_social=data.razon_social,
            correo_contacto=data.correo_contacto,
            telefono_contacto=data.telefono_contacto,
            direccion=data.direccion,
            activo=True,
        )
        self.empresas.create(empresa)
        self.bitacora.registrar(
            usuario_id=creado_por_usuario_id,
            accion="CREAR",
            entidad="empresas",
            entidad_id=empresa.id,
        )
        self.db.commit()
        return self.obtener(empresa.id)

    def actualizar(
        self,
        empresa_id: int,
        data: EmpresaUpdate,
        actualizado_por_usuario_id: int | None = None,
    ) -> Empresa:
        empresa = self.obtener(empresa_id)

        for campo, valor in data.model_dump(exclude_unset=True).items():
            setattr(empresa, campo, valor)

        self.empresas.save()
        self.bitacora.registrar(
            usuario_id=actualizado_por_usuario_id,
            accion="ACTUALIZAR",
            entidad="empresas",
            entidad_id=empresa.id,
        )
        self.db.commit()
        return self.obtener(empresa.id)

    def desactivar(
        self, empresa_id: int, desactivado_por_usuario_id: int | None = None
    ) -> Empresa:
        empresa = self.obtener(empresa_id)
        empresa.activo = False
        self.empresas.save()
        self.bitacora.registrar(
            usuario_id=desactivado_por_usuario_id,
            accion="DESACTIVAR",
            entidad="empresas",
            entidad_id=empresa.id,
        )
        self.db.commit()
        return empresa
