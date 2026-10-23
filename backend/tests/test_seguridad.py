"""Pruebas de endurecimiento de seguridad (Fase 9).

Los tests de rate limiting reactivan temporalmente el límite real
(desactivado por defecto en conftest.py para el resto de la suite) y
lo restauran a un no-op al terminar, para no afectar otras pruebas.
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from app.api.routes.auth import _limite_login
from app.api.routes.portal import _limite_login_evaluado
from app.core.security.password import hash_password
from app.db.session import SessionLocal
from app.main import app
from app.models.seguridad import Bitacora, HistorialLogin, Rol, Sesion, Usuario, UsuarioRol

client = TestClient(app)

SUFIJO = uuid.uuid4().hex[:8]
CORREO_ADMIN = f"test_fase9_{SUFIJO}@example.com"
PASSWORD_ADMIN = "PasswordDePrueba123!"


@pytest.fixture(scope="module")
def db():
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture(scope="module")
def admin_de_prueba(db):
    rol = db.query(Rol).filter(Rol.codigo == "ADMINISTRADOR").one_or_none()
    if rol is None:
        rol = Rol(codigo="ADMINISTRADOR", nombre="Administrador")
        db.add(rol)
        db.flush()

    usuario = Usuario(
        nombre="Test", apellidos="Fase9", correo=CORREO_ADMIN,
        password_hash=hash_password(PASSWORD_ADMIN), activo=True,
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


def test_cabeceras_de_seguridad_presentes():
    response = client.get("/")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "same-origin"


def test_rate_limit_bloquea_login_admin_tras_varios_intentos():
    app.dependency_overrides.pop(_limite_login, None)
    try:
        codigos = [
            client.post(
                "/api/auth/login", json={"correo": "no-existe@example.com", "password": "mal"}
            ).status_code
            for _ in range(15)
        ]
        assert 429 in codigos
    finally:
        app.dependency_overrides[_limite_login] = lambda: None


def test_rate_limit_bloquea_login_evaluado_tras_varios_intentos():
    app.dependency_overrides.pop(_limite_login_evaluado, None)
    try:
        codigos = [
            client.post(
                "/api/portal/login", json={"usuario": "no-existe", "password": "mal"}
            ).status_code
            for _ in range(15)
        ]
        assert 429 in codigos
    finally:
        app.dependency_overrides[_limite_login_evaluado] = lambda: None


def test_cambiar_password_con_actual_incorrecta_devuelve_401(token_admin):
    response = client.put(
        "/api/usuarios/me/password",
        headers={"Authorization": f"Bearer {token_admin}"},
        json={"password_actual": "incorrecta", "password_nueva": "NuevaPassword123!"},
    )
    assert response.status_code == 401


def test_cambiar_password_nueva_muy_corta_devuelve_422(token_admin):
    response = client.put(
        "/api/usuarios/me/password",
        headers={"Authorization": f"Bearer {token_admin}"},
        json={"password_actual": PASSWORD_ADMIN, "password_nueva": "corta"},
    )
    assert response.status_code == 422


def test_cambiar_password_exitoso_permite_login_con_la_nueva(token_admin):
    nueva_password = "NuevaPasswordSegura123!"
    cambio = client.put(
        "/api/usuarios/me/password",
        headers={"Authorization": f"Bearer {token_admin}"},
        json={"password_actual": PASSWORD_ADMIN, "password_nueva": nueva_password},
    )
    assert cambio.status_code == 204

    login_con_vieja = client.post(
        "/api/auth/login", json={"correo": CORREO_ADMIN, "password": PASSWORD_ADMIN}
    )
    assert login_con_vieja.status_code == 401

    login_con_nueva = client.post(
        "/api/auth/login", json={"correo": CORREO_ADMIN, "password": nueva_password}
    )
    assert login_con_nueva.status_code == 200
