"""Pruebas de la Fase 2: modelos ORM, metadata y operaciones básicas de BD."""

from datetime import datetime, timezone

import pytest
from sqlalchemy.orm import Session

from app import models  # noqa: F401 - fuerza el registro de todos los modelos
from app.db.session import Base, SessionLocal, engine


@pytest.fixture(scope="module")
def db() -> Session:
    """Sesión de BD para las pruebas de la Fase 2.

    Requiere una base de datos PostgreSQL accesible vía DATABASE_URL
    (ver backend/.env) con las migraciones de Alembic ya aplicadas.
    """
    session = SessionLocal()
    yield session
    session.rollback()
    session.close()


def test_todas_las_tablas_definidas():
    """Las 40 tablas del modelo de datos deben estar registradas en metadata."""
    assert len(Base.metadata.tables) == 40


def test_tablas_clave_existen():
    nombres = set(Base.metadata.tables.keys())
    esperadas = {
        "usuarios",
        "roles",
        "permisos",
        "empresas",
        "candidatos",
        "usuarios_temporales",
        "categorias_prueba",
        "pruebas",
        "algoritmos",
        "factores",
        "escalas",
        "preguntas",
        "opciones",
        "asignaciones",
        "sesiones_prueba",
        "respuestas",
        "resultados",
        "resultado_factores",
        "resultado_escalas",
        "version_prueba",
    }
    assert esperadas.issubset(nombres)


def test_crud_basico_catalogo_y_empresa(db: Session):
    """Crea un catálogo simple, una empresa y un candidato, y confirma
    que las relaciones funcionan de punta a punta contra PostgreSQL."""
    sexo = models.Sexo(codigo="M_TEST_MODELS", nombre="Masculino (prueba)")
    escolaridad = models.Escolaridad(codigo="LIC_TEST_MODELS", nombre="Licenciatura (prueba)")
    estatus = models.EstatusCandidato(codigo="ACTIVO_TEST_MODELS", nombre="Activo (prueba)")
    empresa = models.Empresa(nombre_comercial="Empresa de prueba (test_models)")

    db.add_all([sexo, escolaridad, estatus, empresa])
    db.flush()

    candidato = models.Candidato(
        nombre="Ana",
        apellidos="Pérez",
        correo="ana.perez@example.com",
        empresa_id=empresa.id,
        sexo_id=sexo.id,
        escolaridad_id=escolaridad.id,
        estatus_candidato_id=estatus.id,
    )
    db.add(candidato)
    db.flush()

    assert candidato.id is not None
    assert candidato.empresa.nombre_comercial == "Empresa de prueba (test_models)"
    assert candidato.sexo.codigo == "M_TEST_MODELS"

    acceso = models.UsuarioTemporal(
        candidato_id=candidato.id,
        usuario="ana.perez.tmp",
        password_hash="hash-de-prueba",
        creado_en=datetime.now(timezone.utc),
        expira_en=datetime.now(timezone.utc),
    )
    db.add(acceso)
    db.flush()

    assert acceso.candidato.correo == "ana.perez@example.com"
