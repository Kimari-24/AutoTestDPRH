"""Repositorio de acceso a datos para las tablas de auditoría de
seguridad: sesiones activas, historial de login y bitácora."""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.seguridad import Bitacora, HistorialLogin, Sesion


class SesionRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, sesion: Sesion) -> Sesion:
        self.db.add(sesion)
        self.db.flush()
        return sesion

    def get_by_jti(self, token_jti: str) -> Sesion | None:
        stmt = select(Sesion).where(Sesion.token_jti == token_jti)
        return self.db.execute(stmt).scalar_one_or_none()

    def revocar(self, sesion: Sesion) -> None:
        sesion.activa = False
        self.db.flush()

    def revocar_todas_de_usuario(self, usuario_id: int) -> None:
        stmt = select(Sesion).where(
            Sesion.usuario_id == usuario_id, Sesion.activa.is_(True)
        )
        for sesion in self.db.execute(stmt).scalars().all():
            sesion.activa = False
        self.db.flush()


class HistorialLoginRepository:
    def __init__(self, db: Session):
        self.db = db

    def registrar(
        self,
        *,
        usuario_id: int | None,
        usuario_temporal_id: int | None,
        exitoso: bool,
        ip: str | None,
        user_agent: str | None,
    ) -> HistorialLogin:
        registro = HistorialLogin(
            usuario_id=usuario_id,
            usuario_temporal_id=usuario_temporal_id,
            exitoso=exitoso,
            ip=ip,
            user_agent=user_agent,
            creado_en=datetime.now(timezone.utc),
        )
        self.db.add(registro)
        self.db.flush()
        return registro


class BitacoraRepository:
    def __init__(self, db: Session):
        self.db = db

    def registrar(
        self,
        *,
        usuario_id: int | None,
        accion: str,
        entidad: str,
        entidad_id: int | None = None,
        detalle: str | None = None,
        ip: str | None = None,
    ) -> Bitacora:
        registro = Bitacora(
            usuario_id=usuario_id,
            accion=accion,
            entidad=entidad,
            entidad_id=entidad_id,
            detalle=detalle,
            ip=ip,
            creado_en=datetime.now(timezone.utc),
        )
        self.db.add(registro)
        self.db.flush()
        return registro
