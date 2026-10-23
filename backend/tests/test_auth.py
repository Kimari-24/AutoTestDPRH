"""Pruebas de la Fase 3: autenticación, JWT y RBAC.

Requiere una base de datos PostgreSQL accesible vía DATABASE_URL con
las migraciones de Alembic ya aplicadas (igual que test_models.py).
Cada prueba crea sus propios datos con un correo único y los limpia
al finalizar el módulo, para no depender de haber corrido
`scripts/seed_roles.py` ni dejar residuos en la base de datos.
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security.password import hash_password
from app.db.session import SessionLocal
from app.main import app
from app.models.seguridad import (
    Bitacora,
    HistorialLogin,
    Rol,
    Sesion,
    Usuario,
    UsuarioRol,
)

client = TestClient(app)

CORREO_ADMIN = f"test_auth_{uuid.uuid4().hex[:8]}@example.com"
PASSWORD_ADMIN = "PasswordDePrueba123!"


@pytest.fixture(scope="module")
def db() -> Session:
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture(scope="module")
def admin_de_prueba(db: Session):
    """Crea un usuario ADMINISTRADOR exclusivo para estas pruebas y lo
    elimina (junto con sus registros de auditoría) al terminar."""
    rol = db.query(Rol).filter(Rol.codigo == "ADMINISTRADOR").one_or_none()
    if rol is None:
        rol = Rol(
            codigo="ADMINISTRADOR",
            nombre="Administrador",
            descripcion="Acceso completo al sistema.",
        )
        db.add(rol)
        db.flush()

    usuario = Usuario(
        nombre="Test",
        apellidos="Auth",
        correo=CORREO_ADMIN,
        password_hash=hash_password(PASSWORD_ADMIN),
        activo=True,
    )
    db.add(usuario)
    db.flush()
    db.add(UsuarioRol(usuario_id=usuario.id, rol_id=rol.id))
    db.commit()

    yield usuario

    # --- limpieza ---
    db.query(Sesion).filter(Sesion.usuario_id == usuario.id).delete()
    db.query(HistorialLogin).filter(HistorialLogin.usuario_id == usuario.id).delete()
    db.query(Bitacora).filter(Bitacora.usuario_id == usuario.id).delete()
    db.query(UsuarioRol).filter(UsuarioRol.usuario_id == usuario.id).delete()
    db.query(Usuario).filter(Usuario.id == usuario.id).delete()
    db.commit()


def test_login_exitoso(admin_de_prueba):
    response = client.post(
        "/api/auth/login",
        json={"correo": CORREO_ADMIN, "password": PASSWORD_ADMIN},
    )
    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["token_type"] == "bearer"


def test_login_con_password_incorrecta(admin_de_prueba):
    response = client.post(
        "/api/auth/login",
        json={"correo": CORREO_ADMIN, "password": "password-incorrecta"},
    )
    assert response.status_code == 401


def test_login_con_correo_inexistente():
    response = client.post(
        "/api/auth/login",
        json={"correo": "no-existe@example.com", "password": "cualquiera"},
    )
    assert response.status_code == 401


def test_me_devuelve_datos_del_usuario_autenticado(admin_de_prueba):
    login = client.post(
        "/api/auth/login",
        json={"correo": CORREO_ADMIN, "password": PASSWORD_ADMIN},
    ).json()

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {login['access_token']}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["correo"] == CORREO_ADMIN
    assert "ADMINISTRADOR" in body["roles"]


def test_endpoint_protegido_sin_token_devuelve_401():
    response = client.get("/api/usuarios")
    assert response.status_code == 401


def test_endpoint_protegido_con_token_invalido_devuelve_401():
    response = client.get(
        "/api/usuarios", headers={"Authorization": "Bearer token-invalido"}
    )
    assert response.status_code == 401


def test_endpoint_protegido_con_rol_administrador_devuelve_200(admin_de_prueba):
    login = client.post(
        "/api/auth/login",
        json={"correo": CORREO_ADMIN, "password": PASSWORD_ADMIN},
    ).json()

    response = client.get(
        "/api/usuarios",
        headers={"Authorization": f"Bearer {login['access_token']}"},
    )
    assert response.status_code == 200
    assert any(u["correo"] == CORREO_ADMIN for u in response.json())


def test_refresh_devuelve_un_nuevo_access_token(admin_de_prueba):
    login = client.post(
        "/api/auth/login",
        json={"correo": CORREO_ADMIN, "password": PASSWORD_ADMIN},
    ).json()

    response = client.post(
        "/api/auth/refresh", json={"refresh_token": login["refresh_token"]}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_logout_revoca_la_sesion(admin_de_prueba):
    login = client.post(
        "/api/auth/login",
        json={"correo": CORREO_ADMIN, "password": PASSWORD_ADMIN},
    ).json()

    logout_response = client.post(
        "/api/auth/logout", json={"refresh_token": login["refresh_token"]}
    )
    assert logout_response.status_code == 204

    refresh_response = client.post(
        "/api/auth/refresh", json={"refresh_token": login["refresh_token"]}
    )
    assert refresh_response.status_code == 401
