"""Pruebas de la Fase 5: categorías, pruebas, versiones, preguntas,
opciones, algoritmo, factores y escalas.

Igual que las suites anteriores, usa códigos únicos por corrida y
limpia lo que crea al finalizar el módulo.
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security.password import hash_password
from app.db.session import SessionLocal
from app.main import app
from app.models.catalogo_prueba import Algoritmo, CategoriaPrueba, Opcion, Pregunta, Prueba
from app.models.catalogos import TipoPregunta
from app.models.seguridad import Bitacora, HistorialLogin, Rol, Sesion, Usuario, UsuarioRol
from app.models.versionado import VersionPrueba

client = TestClient(app)

SUFIJO = uuid.uuid4().hex[:8]
CORREO_ADMIN = f"test_fase5_{SUFIJO}@example.com"
PASSWORD_ADMIN = "PasswordDePrueba123!"
CATEGORIA_CODIGO = f"CAT_TEST_{SUFIJO}"
PRUEBA_CODIGO = f"PRUEBA_TEST_{SUFIJO}"
TIPO_PREGUNTA_CODIGO = f"TIPO_TEST_{SUFIJO}"


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
        apellidos="Fase5",
        correo=CORREO_ADMIN,
        password_hash=hash_password(PASSWORD_ADMIN),
        activo=True,
    )
    db.add(usuario)
    db.flush()
    db.add(UsuarioRol(usuario_id=usuario.id, rol_id=rol.id))

    # Tipo de pregunta propio de la prueba, para no depender de
    # scripts/seed_catalogos.py.
    db.add(TipoPregunta(codigo=TIPO_PREGUNTA_CODIGO, nombre="Tipo de prueba", activo=True))
    db.commit()

    yield usuario

    db.query(Sesion).filter(Sesion.usuario_id == usuario.id).delete()
    db.query(HistorialLogin).filter(HistorialLogin.usuario_id == usuario.id).delete()
    db.query(Bitacora).filter(Bitacora.usuario_id == usuario.id).delete()
    db.query(UsuarioRol).filter(UsuarioRol.usuario_id == usuario.id).delete()
    db.query(Usuario).filter(Usuario.id == usuario.id).delete()
    db.commit()


@pytest.fixture(scope="module")
def auth_headers(admin_de_prueba):
    login = client.post(
        "/api/auth/login", json={"correo": CORREO_ADMIN, "password": PASSWORD_ADMIN}
    ).json()
    return {"Authorization": f"Bearer {login['access_token']}"}


@pytest.fixture(scope="module", autouse=True)
def limpiar_datos_al_final(db: Session):
    yield
    prueba = db.query(Prueba).filter(Prueba.codigo == PRUEBA_CODIGO).one_or_none()
    if prueba is not None:
        version_ids = [
            v.id
            for v in db.query(VersionPrueba).filter(VersionPrueba.prueba_id == prueba.id)
        ]
        if version_ids:
            pregunta_ids = [
                p.id
                for p in db.query(Pregunta).filter(Pregunta.version_prueba_id.in_(version_ids))
            ]
            if pregunta_ids:
                db.query(Opcion).filter(Opcion.pregunta_id.in_(pregunta_ids)).delete(
                    synchronize_session=False
                )
                db.query(Pregunta).filter(Pregunta.id.in_(pregunta_ids)).delete(
                    synchronize_session=False
                )
        for algoritmo in db.query(Algoritmo).filter(Algoritmo.prueba_id == prueba.id):
            db.delete(algoritmo)
        for version in db.query(VersionPrueba).filter(VersionPrueba.prueba_id == prueba.id):
            db.delete(version)
        db.delete(prueba)
        db.flush()
    db.query(CategoriaPrueba).filter(CategoriaPrueba.codigo == CATEGORIA_CODIGO).delete()
    # El tipo de pregunta de prueba se borra al final, una vez que ya
    # no queda ninguna Pregunta que lo referencie.
    db.query(TipoPregunta).filter(TipoPregunta.codigo == TIPO_PREGUNTA_CODIGO).delete()
    db.commit()


@pytest.fixture(scope="module")
def categoria_de_prueba(auth_headers):
    response = client.post(
        "/api/evaluaciones/categorias",
        headers=auth_headers,
        json={"codigo": CATEGORIA_CODIGO, "nombre": "Categoría de prueba"},
    )
    assert response.status_code == 201
    return response.json()


@pytest.fixture(scope="module")
def prueba_de_prueba(categoria_de_prueba, auth_headers):
    response = client.post(
        "/api/evaluaciones",
        headers=auth_headers,
        json={
            "categoria_codigo": CATEGORIA_CODIGO,
            "codigo": PRUEBA_CODIGO,
            "nombre": "Evaluación de prueba",
            "tiempo_limite_minutos": 20,
        },
    )
    assert response.status_code == 201
    return response.json()


def test_evaluaciones_requiere_rol_administrador():
    response = client.get("/api/evaluaciones")
    assert response.status_code == 401


def test_crear_categoria_duplicada_devuelve_409(categoria_de_prueba, auth_headers):
    response = client.post(
        "/api/evaluaciones/categorias",
        headers=auth_headers,
        json={"codigo": CATEGORIA_CODIGO, "nombre": "Otra vez"},
    )
    assert response.status_code == 409


def test_crear_prueba_con_categoria_inexistente_devuelve_422(auth_headers):
    response = client.post(
        "/api/evaluaciones",
        headers=auth_headers,
        json={"categoria_codigo": "NO_EXISTE", "codigo": "X", "nombre": "X"},
    )
    assert response.status_code == 422


def test_crear_prueba_con_codigo_duplicado_devuelve_409(prueba_de_prueba, auth_headers):
    response = client.post(
        "/api/evaluaciones",
        headers=auth_headers,
        json={
            "categoria_codigo": CATEGORIA_CODIGO,
            "codigo": PRUEBA_CODIGO,
            "nombre": "Duplicada",
        },
    )
    assert response.status_code == 409


def test_activar_y_desactivar_prueba(prueba_de_prueba, auth_headers):
    prueba_id = prueba_de_prueba["id"]

    desactivar = client.delete(f"/api/evaluaciones/{prueba_id}", headers=auth_headers)
    assert desactivar.status_code == 200
    assert desactivar.json()["activa"] is False

    activar = client.post(f"/api/evaluaciones/{prueba_id}/activar", headers=auth_headers)
    assert activar.status_code == 200
    assert activar.json()["activa"] is True


def test_crear_version_y_preguntas(prueba_de_prueba, auth_headers):
    prueba_id = prueba_de_prueba["id"]

    version = client.post(
        f"/api/evaluaciones/{prueba_id}/versiones",
        headers=auth_headers,
        json={"notas": "Versión de prueba"},
    )
    assert version.status_code == 201
    version_id = version.json()["id"]
    assert version.json()["numero_version"] == 1
    assert version.json()["activa"] is True

    pregunta = client.post(
        f"/api/evaluaciones/versiones/{version_id}/preguntas",
        headers=auth_headers,
        json={
            "tipo_pregunta_codigo": TIPO_PREGUNTA_CODIGO,
            "enunciado": "¿Enunciado de prueba?",
            "orden": 1,
            "opciones": [{"texto": "A", "orden": 1}, {"texto": "B", "orden": 2}],
        },
    )
    assert pregunta.status_code == 201
    pregunta_body = pregunta.json()
    assert len(pregunta_body["opciones"]) == 2
    pregunta_id = pregunta_body["id"]
    opcion_id = pregunta_body["opciones"][0]["id"]

    listar = client.get(
        f"/api/evaluaciones/versiones/{version_id}/preguntas", headers=auth_headers
    )
    assert listar.status_code == 200
    assert len(listar.json()) == 1

    # La prueba ahora debe reportar 1 pregunta activa.
    detalle_prueba = client.get(f"/api/evaluaciones/{prueba_id}", headers=auth_headers)
    assert detalle_prueba.json()["total_preguntas_activas"] == 1

    # Eliminar una opción sin respuestas asociadas debe funcionar.
    eliminar_opcion = client.delete(
        f"/api/evaluaciones/opciones/{opcion_id}", headers=auth_headers
    )
    assert eliminar_opcion.status_code == 204

    # Desactivar la pregunta reduce el conteo de activas a 0.
    desactivar_pregunta = client.delete(
        f"/api/evaluaciones/preguntas/{pregunta_id}", headers=auth_headers
    )
    assert desactivar_pregunta.status_code == 200
    assert desactivar_pregunta.json()["activa"] is False


def test_crear_segunda_version_desactiva_la_anterior(prueba_de_prueba, auth_headers):
    prueba_id = prueba_de_prueba["id"]

    versiones_antes = client.get(
        f"/api/evaluaciones/{prueba_id}/versiones", headers=auth_headers
    ).json()
    assert len(versiones_antes) == 1

    nueva_version = client.post(
        f"/api/evaluaciones/{prueba_id}/versiones", headers=auth_headers, json={}
    )
    assert nueva_version.status_code == 201
    assert nueva_version.json()["numero_version"] == 2

    versiones_despues = client.get(
        f"/api/evaluaciones/{prueba_id}/versiones", headers=auth_headers
    ).json()
    assert len(versiones_despues) == 2
    activas = [v for v in versiones_despues if v["activa"]]
    assert len(activas) == 1
    assert activas[0]["numero_version"] == 2


def test_algoritmo_factor_y_escala(prueba_de_prueba, auth_headers):
    prueba_id = prueba_de_prueba["id"]

    algoritmo = client.post(
        f"/api/evaluaciones/{prueba_id}/algoritmos",
        headers=auth_headers,
        json={"nombre": "Algoritmo de prueba", "tipo_calculo": "suma"},
    )
    assert algoritmo.status_code == 201
    algoritmo_id = algoritmo.json()["id"]

    factor = client.post(
        f"/api/evaluaciones/algoritmos/{algoritmo_id}/factores",
        headers=auth_headers,
        json={"codigo": "F1", "nombre": "Factor de prueba"},
    )
    assert factor.status_code == 201
    factor_id = factor.json()["id"]

    escala = client.post(
        f"/api/evaluaciones/factores/{factor_id}/escalas",
        headers=auth_headers,
        json={"codigo": "E1", "nombre": "Escala de prueba", "valor_min": 0, "valor_max": 10},
    )
    assert escala.status_code == 201

    detalle = client.get(
        f"/api/evaluaciones/{prueba_id}/algoritmos", headers=auth_headers
    ).json()
    assert len(detalle) == 1
    assert len(detalle[0]["factores"]) == 1
    assert len(detalle[0]["factores"][0]["escalas"]) == 1

    eliminar_factor = client.delete(
        f"/api/evaluaciones/factores/{factor_id}", headers=auth_headers
    )
    assert eliminar_factor.status_code == 204
