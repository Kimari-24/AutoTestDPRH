"""Pruebas de la Fase 4: dashboard, empresas y evaluados.

Igual que test_auth.py, cada prueba usa datos con sufijos únicos y
limpia lo que crea al finalizar el módulo, para no depender de datos
sembrados por scripts/seed_*.py ni dejar residuos en la base.
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security.password import hash_password
from app.db.session import SessionLocal
from app.main import app
from app.models.candidato import Candidato
from app.models.empresa import Empresa
from app.models.seguridad import Bitacora, HistorialLogin, Rol, Sesion, Usuario, UsuarioRol

client = TestClient(app)

SUFIJO = uuid.uuid4().hex[:8]
CORREO_ADMIN = f"test_fase4_{SUFIJO}@example.com"
PASSWORD_ADMIN = "PasswordDePrueba123!"
NOMBRE_EMPRESA = f"Empresa Fase4 {SUFIJO}"
CORREO_EVALUADO = f"evaluado_fase4_{SUFIJO}@example.com"


@pytest.fixture(scope="module")
def db() -> Session:
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture(scope="module")
def admin_de_prueba(db: Session):
    rol = db.query(Rol).filter(Rol.codigo == "ADMINISTRADOR").one_or_none()
    if rol is None:
        rol = Rol(codigo="ADMINISTRADOR", nombre="Administrador")
        db.add(rol)
        db.flush()

    usuario = Usuario(
        nombre="Test",
        apellidos="Fase4",
        correo=CORREO_ADMIN,
        password_hash=hash_password(PASSWORD_ADMIN),
        activo=True,
    )
    db.add(usuario)
    db.flush()
    db.add(UsuarioRol(usuario_id=usuario.id, rol_id=rol.id))
    db.commit()

    yield usuario

    db.query(Sesion).filter(Sesion.usuario_id == usuario.id).delete()
    db.query(HistorialLogin).filter(HistorialLogin.usuario_id == usuario.id).delete()
    db.query(Bitacora).filter(Bitacora.usuario_id == usuario.id).delete()
    db.query(UsuarioRol).filter(UsuarioRol.usuario_id == usuario.id).delete()
    db.query(Usuario).filter(Usuario.id == usuario.id).delete()
    db.commit()


@pytest.fixture(scope="module")
def token_admin(admin_de_prueba):
    login = client.post(
        "/api/auth/login", json={"correo": CORREO_ADMIN, "password": PASSWORD_ADMIN}
    ).json()
    return login["access_token"]


@pytest.fixture(scope="module")
def auth_headers(token_admin):
    return {"Authorization": f"Bearer {token_admin}"}


@pytest.fixture(scope="module", autouse=True)
def limpiar_datos_al_final(db: Session):
    yield
    db.query(Candidato).filter(Candidato.correo == CORREO_EVALUADO).delete()
    db.query(Empresa).filter(Empresa.nombre_comercial == NOMBRE_EMPRESA).delete()
    db.commit()


def test_dashboard_requiere_rol_administrador():
    response = client.get("/api/dashboard/resumen")
    assert response.status_code == 401


def test_dashboard_devuelve_resumen(auth_headers):
    response = client.get("/api/dashboard/resumen", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    for campo in (
        "total_evaluados",
        "total_evaluaciones_disponibles",
        "total_resultados",
        "evaluaciones_pendientes",
        "evaluaciones_en_proceso",
        "evaluaciones_completadas",
        "evaluados_recientes",
    ):
        assert campo in body


@pytest.fixture(scope="module")
def empresa_de_prueba(auth_headers):
    crear = client.post(
        "/api/empresas",
        headers=auth_headers,
        json={"nombre_comercial": NOMBRE_EMPRESA, "correo_contacto": "contacto@example.com"},
    )
    assert crear.status_code == 201
    return crear.json()


def test_crear_y_listar_empresa(empresa_de_prueba, auth_headers):
    listar = client.get(f"/api/empresas?buscar={NOMBRE_EMPRESA[:10]}", headers=auth_headers)
    assert listar.status_code == 200
    assert any(e["id"] == empresa_de_prueba["id"] for e in listar.json())


def test_crear_evaluado_y_ver_expediente(empresa_de_prueba, auth_headers):
    empresa_id = empresa_de_prueba["id"]

    crear = client.post(
        "/api/evaluados",
        headers=auth_headers,
        json={
            "nombre": "Evaluado",
            "apellidos": f"Fase4 {SUFIJO}",
            "correo": CORREO_EVALUADO,
            "empresa_id": empresa_id,
        },
    )
    assert crear.status_code == 201
    body = crear.json()
    assert body["empresa"]["id"] == empresa_id
    candidato_id = body["id"]

    expediente = client.get(f"/api/evaluados/{candidato_id}/expediente", headers=auth_headers)
    assert expediente.status_code == 200
    expediente_body = expediente.json()
    assert expediente_body["candidato"]["id"] == candidato_id
    assert expediente_body["evaluaciones"] == []


def test_crear_evaluado_con_correo_duplicado_devuelve_409(auth_headers):
    response = client.post(
        "/api/evaluados",
        headers=auth_headers,
        json={"nombre": "Otro", "apellidos": "Nombre", "correo": CORREO_EVALUADO},
    )
    assert response.status_code == 409


def test_crear_evaluado_con_catalogo_inexistente_devuelve_422(auth_headers):
    response = client.post(
        "/api/evaluados",
        headers=auth_headers,
        json={
            "nombre": "X",
            "apellidos": "Y",
            "correo": f"xy_{SUFIJO}@example.com",
            "sexo_codigo": "NO_EXISTE",
        },
    )
    assert response.status_code == 422
