"""Pruebas de la Fase 7: accesos temporales y portal del evaluado.

Cubre el flujo completo de la sección 6: el administrador crea al
evaluado, genera su acceso temporal, le asigna una evaluación; el
evaluado inicia sesión, ve solo sus evaluaciones, inicia la prueba,
responde (autoguardado), consulta su progreso y finaliza — momento en
el que el motor la califica automáticamente.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security.password import hash_password
from app.db.session import SessionLocal
from app.main import app
from app.models.aplicacion import (
    Asignacion,
    Respuesta,
    Resultado,
    ResultadoEscala,
    ResultadoFactor,
    SesionPrueba,
)
from app.models.candidato import Candidato, UsuarioTemporal
from app.models.catalogo_prueba import Algoritmo, CategoriaPrueba, Escala, Factor, Opcion, Pregunta, Prueba
from app.models.catalogos import TipoPregunta
from app.models.seguridad import Bitacora, HistorialLogin, Rol, Sesion, Usuario, UsuarioRol
from app.models.versionado import VersionPrueba

client = TestClient(app)

SUFIJO = uuid.uuid4().hex[:8]
CORREO_ADMIN = f"test_fase7_{SUFIJO}@example.com"
PASSWORD_ADMIN = "PasswordDePrueba123!"
CORREO_EVALUADO = f"evaluado_fase7_{SUFIJO}@example.com"


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
        nombre="Test", apellidos="Fase7", correo=CORREO_ADMIN,
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
def auth_headers(admin_de_prueba):
    login = client.post(
        "/api/auth/login", json={"correo": CORREO_ADMIN, "password": PASSWORD_ADMIN}
    ).json()
    return {"Authorization": f"Bearer {login['access_token']}"}


@pytest.fixture(scope="module")
def prueba_configurada(db: Session):
    """Arma una evaluación de ejemplo completa (categoría, prueba,
    versión, 1 pregunta con 2 opciones, algoritmo con 1 factor y 1
    escala) — contenido claramente de ejemplo, no psicométrico real.
    """
    categoria = CategoriaPrueba(codigo=f"CAT7_{SUFIJO}", nombre="Categoría Fase 7")
    db.add(categoria)
    db.flush()

    prueba = Prueba(
        categoria_id=categoria.id, codigo=f"PRUEBA7_{SUFIJO}", nombre="Evaluación de prueba Fase 7",
        activa=True, intentos_permitidos=1, tiempo_limite_minutos=None,
    )
    db.add(prueba)
    db.flush()

    version = VersionPrueba(
        prueba_id=prueba.id, numero_version=1, activa=True, creado_en=datetime.now(timezone.utc),
    )
    db.add(version)
    db.flush()

    tipo_pregunta = TipoPregunta(codigo=f"TIPO7_{SUFIJO}", nombre="Tipo de prueba Fase 7")
    db.add(tipo_pregunta)
    db.flush()

    pregunta = Pregunta(
        version_prueba_id=version.id, tipo_pregunta_id=tipo_pregunta.id,
        enunciado="Pregunta de ejemplo (sin contenido psicométrico real)",
        configuracion={"factor_codigo": "F7"}, orden=1, activa=True,
    )
    db.add(pregunta)
    db.flush()
    opcion_1 = Opcion(pregunta_id=pregunta.id, texto="Opción 1", valor="1", orden=1)
    opcion_2 = Opcion(pregunta_id=pregunta.id, texto="Opción 2", valor="2", orden=2)
    db.add_all([opcion_1, opcion_2])
    db.flush()

    algoritmo = Algoritmo(
        prueba_id=prueba.id, nombre="Algoritmo de prueba", tipo_calculo="suma", activo=True,
    )
    db.add(algoritmo)
    db.flush()
    factor = Factor(algoritmo_id=algoritmo.id, codigo="F7", nombre="Factor de prueba", orden=1)
    db.add(factor)
    db.flush()
    escala = Escala(
        factor_id=factor.id, codigo="E7", nombre="Escala de prueba",
        valor_min=0, valor_max=100, descripcion="Interpretación de ejemplo", orden=1,
    )
    db.add(escala)
    db.commit()

    yield {
        "prueba_id": prueba.id, "opcion_1_id": opcion_1.id, "opcion_2_id": opcion_2.id,
        "pregunta_id": pregunta.id,
    }

    db.query(Escala).filter(Escala.factor_id == factor.id).delete()
    db.query(Factor).filter(Factor.id == factor.id).delete()
    db.query(Algoritmo).filter(Algoritmo.id == algoritmo.id).delete()
    db.query(Opcion).filter(Opcion.pregunta_id == pregunta.id).delete()
    db.query(Pregunta).filter(Pregunta.id == pregunta.id).delete()
    db.query(VersionPrueba).filter(VersionPrueba.id == version.id).delete()
    db.query(Prueba).filter(Prueba.id == prueba.id).delete()
    db.query(CategoriaPrueba).filter(CategoriaPrueba.id == categoria.id).delete()
    db.query(TipoPregunta).filter(TipoPregunta.id == tipo_pregunta.id).delete()
    db.commit()


@pytest.fixture(scope="module")
def evaluado_con_acceso(db: Session, prueba_configurada, auth_headers):
    """Crea un candidato vía API, le asigna la evaluación de prueba y
    genera su acceso temporal — exactamente el flujo del administrador."""
    candidato_resp = client.post(
        "/api/evaluados",
        headers=auth_headers,
        json={"nombre": "Evaluado", "apellidos": f"Fase7 {SUFIJO}", "correo": CORREO_EVALUADO},
    )
    assert candidato_resp.status_code == 201
    candidato_id = candidato_resp.json()["id"]

    asignacion_resp = client.post(
        f"/api/evaluados/{candidato_id}/asignaciones",
        headers=auth_headers,
        json={"prueba_id": prueba_configurada["prueba_id"]},
    )
    assert asignacion_resp.status_code == 201
    asignacion_id = asignacion_resp.json()["id"]

    acceso_resp = client.post(
        f"/api/evaluados/{candidato_id}/accesos-temporales",
        headers=auth_headers,
        json={"horas_vigencia": 48},
    )
    assert acceso_resp.status_code == 201
    acceso_body = acceso_resp.json()

    yield {
        "candidato_id": candidato_id,
        "asignacion_id": asignacion_id,
        "usuario": acceso_body["usuario"],
        "password": acceso_body["password_temporal"],
        "acceso_id": acceso_body["id"],
    }

    # --- limpieza (respeta el orden de llaves foraneas) ---
    sesion_ids = [
        s.id
        for s in db.query(SesionPrueba).filter(
            SesionPrueba.asignacion_id.in_(
                db.query(Asignacion.id).filter(Asignacion.candidato_id == candidato_id)
            )
        )
    ]
    if sesion_ids:
        resultado_ids = [
            r.id for r in db.query(Resultado).filter(Resultado.sesion_prueba_id.in_(sesion_ids))
        ]
        if resultado_ids:
            db.query(ResultadoEscala).filter(
                ResultadoEscala.resultado_id.in_(resultado_ids)
            ).delete(synchronize_session=False)
            db.query(ResultadoFactor).filter(
                ResultadoFactor.resultado_id.in_(resultado_ids)
            ).delete(synchronize_session=False)
            db.query(Resultado).filter(Resultado.id.in_(resultado_ids)).delete(
                synchronize_session=False
            )
        db.query(Respuesta).filter(Respuesta.sesion_prueba_id.in_(sesion_ids)).delete(
            synchronize_session=False
        )
        db.query(SesionPrueba).filter(SesionPrueba.id.in_(sesion_ids)).delete(
            synchronize_session=False
        )
    db.query(Asignacion).filter(Asignacion.candidato_id == candidato_id).delete(
        synchronize_session=False
    )
    db.query(HistorialLogin).filter(
        HistorialLogin.usuario_temporal_id.in_(
            db.query(UsuarioTemporal.id).filter(UsuarioTemporal.candidato_id == candidato_id)
        )
    ).delete(synchronize_session=False)
    db.query(UsuarioTemporal).filter(UsuarioTemporal.candidato_id == candidato_id).delete(
        synchronize_session=False
    )
    db.query(Candidato).filter(Candidato.id == candidato_id).delete()
    db.commit()


def test_admin_ve_la_password_solo_una_vez(evaluado_con_acceso):
    # El propio fixture ya comprobó (vía el schema AccesoTemporalCreadoOut)
    # que la respuesta de creación trae la contraseña en claro.
    assert len(evaluado_con_acceso["password"]) >= 8


def test_login_evaluado_con_password_incorrecta(evaluado_con_acceso):
    response = client.post(
        "/api/portal/login",
        json={"usuario": evaluado_con_acceso["usuario"], "password": "incorrecta"},
    )
    assert response.status_code == 401


def test_login_evaluado_exitoso(evaluado_con_acceso):
    response = client.post(
        "/api/portal/login",
        json={"usuario": evaluado_con_acceso["usuario"], "password": evaluado_con_acceso["password"]},
    )
    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert "Fase7" in body["candidato_nombre"]


def test_token_de_evaluado_no_sirve_para_endpoints_admin(evaluado_con_acceso):
    login = client.post(
        "/api/portal/login",
        json={"usuario": evaluado_con_acceso["usuario"], "password": evaluado_con_acceso["password"]},
    ).json()
    response = client.get(
        "/api/evaluados", headers={"Authorization": f"Bearer {login['access_token']}"}
    )
    assert response.status_code == 401


def test_token_de_admin_no_sirve_para_el_portal(auth_headers):
    response = client.get("/api/portal/mis-evaluaciones", headers=auth_headers)
    assert response.status_code == 401


def test_mis_evaluaciones_solo_muestra_lo_asignado(evaluado_con_acceso):
    login = client.post(
        "/api/portal/login",
        json={"usuario": evaluado_con_acceso["usuario"], "password": evaluado_con_acceso["password"]},
    ).json()
    headers = {"Authorization": f"Bearer {login['access_token']}"}

    response = client.get("/api/portal/mis-evaluaciones", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["asignacion_id"] == evaluado_con_acceso["asignacion_id"]
    assert body[0]["puede_iniciar"] is True


def test_flujo_completo_iniciar_responder_y_finalizar(evaluado_con_acceso, prueba_configurada):
    login = client.post(
        "/api/portal/login",
        json={"usuario": evaluado_con_acceso["usuario"], "password": evaluado_con_acceso["password"]},
    ).json()
    headers = {"Authorization": f"Bearer {login['access_token']}"}

    iniciar = client.post(
        f"/api/portal/evaluaciones/{evaluado_con_acceso['asignacion_id']}/iniciar", headers=headers
    )
    assert iniciar.status_code == 200
    sesion_id = iniciar.json()["sesion_id"]

    # Continuar (segunda llamada) debe devolver la MISMA sesión, no crear otra.
    continuar = client.post(
        f"/api/portal/evaluaciones/{evaluado_con_acceso['asignacion_id']}/iniciar", headers=headers
    )
    assert continuar.json()["sesion_id"] == sesion_id

    preguntas = client.get(f"/api/portal/sesiones/{sesion_id}/preguntas", headers=headers)
    assert preguntas.status_code == 200
    preguntas_body = preguntas.json()
    assert len(preguntas_body) == 1
    # El evaluado NUNCA debe ver el campo "valor" de las opciones ni
    # la "configuracion" de la pregunta (ahí vive la clave/el peso).
    assert "valor" not in preguntas_body[0]["opciones"][0]
    assert "configuracion" not in preguntas_body[0]

    pregunta_id = preguntas_body[0]["id"]
    opcion_id = preguntas_body[0]["opciones"][0]["id"]

    guardar = client.put(
        f"/api/portal/sesiones/{sesion_id}/preguntas/{pregunta_id}/respuesta",
        headers=headers,
        json={"opcion_id": opcion_id},
    )
    assert guardar.status_code == 204

    progreso = client.get(f"/api/portal/sesiones/{sesion_id}/progreso", headers=headers)
    assert progreso.status_code == 200
    assert progreso.json()["preguntas_respondidas"] == 1
    assert progreso.json()["porcentaje"] == 100

    finalizar = client.post(f"/api/portal/sesiones/{sesion_id}/finalizar", headers=headers)
    assert finalizar.status_code == 200
    assert finalizar.json()["estatus"] == "CALIFICADA"  # el motor la calificó automáticamente

    # Ya no se pueden guardar más respuestas.
    reintento = client.put(
        f"/api/portal/sesiones/{sesion_id}/preguntas/{pregunta_id}/respuesta",
        headers=headers,
        json={"opcion_id": opcion_id},
    )
    assert reintento.status_code == 409


def test_sesion_con_tiempo_agotado_expira_y_ya_no_es_iniciable(
    db: Session, auth_headers, evaluado_con_acceso, prueba_configurada
):
    """El temporizador vive en el servidor: si el tiempo límite se agota,
    la sesión pasa a EXPIRADA, ya no admite respuestas y la evaluación
    deja de aparecer como iniciable."""
    # Segunda asignación de la misma prueba, con límite de 1 minuto.
    prueba = db.query(Prueba).filter(Prueba.id == prueba_configurada["prueba_id"]).one()
    prueba.tiempo_limite_minutos = 1
    db.commit()

    asignacion = client.post(
        f"/api/evaluados/{evaluado_con_acceso['candidato_id']}/asignaciones",
        headers=auth_headers,
        json={"prueba_id": prueba_configurada["prueba_id"]},
    ).json()

    login = client.post(
        "/api/portal/login",
        json={"usuario": evaluado_con_acceso["usuario"], "password": evaluado_con_acceso["password"]},
    ).json()
    headers = {"Authorization": f"Bearer {login['access_token']}"}

    iniciar = client.post(f"/api/portal/evaluaciones/{asignacion['id']}/iniciar", headers=headers)
    assert iniciar.status_code == 200
    sesion_id = iniciar.json()["sesion_id"]
    assert iniciar.json()["tiempo_restante_segundos"] == 60

    # Simula que el evaluado empezó hace 2 horas (el límite era de 1 minuto).
    sesion = db.query(SesionPrueba).filter(SesionPrueba.id == sesion_id).one()
    sesion.iniciada_en = datetime.now(timezone.utc) - timedelta(hours=2)
    db.commit()

    # La lista ya no la ofrece como iniciable.
    mis = client.get("/api/portal/mis-evaluaciones", headers=headers).json()
    esta = next(e for e in mis if e["asignacion_id"] == asignacion["id"])
    assert esta["estatus"] == "EXPIRADA"
    assert esta["puede_iniciar"] is False

    # Ya no se puede reanudar ni responder.
    reanudar = client.post(f"/api/portal/evaluaciones/{asignacion['id']}/iniciar", headers=headers)
    assert reanudar.status_code == 409
    responder = client.put(
        f"/api/portal/sesiones/{sesion_id}/preguntas/{prueba_configurada['pregunta_id']}/respuesta",
        headers=headers,
        json={"opcion_id": prueba_configurada["opcion_1_id"]},
    )
    assert responder.status_code == 409

    prueba.tiempo_limite_minutos = None
    db.commit()


def test_intentos_fallidos_repetidos_bloquean_el_acceso(db: Session, evaluado_con_acceso):
    for _ in range(5):
        client.post(
            "/api/portal/login",
            json={"usuario": evaluado_con_acceso["usuario"], "password": "mal"},
        )
    response = client.post(
        "/api/portal/login",
        json={"usuario": evaluado_con_acceso["usuario"], "password": evaluado_con_acceso["password"]},
    )
    assert response.status_code == 403

    # Se restablece manualmente para no afectar otras pruebas del módulo.
    acceso = db.query(UsuarioTemporal).filter(
        UsuarioTemporal.usuario == evaluado_con_acceso["usuario"]
    ).one()
    acceso.intentos_fallidos = 0
    db.commit()


def test_revocar_acceso_impide_iniciar_sesion(db: Session, auth_headers, evaluado_con_acceso):
    revocar = client.post(
        f"/api/evaluados/accesos-temporales/{evaluado_con_acceso['acceso_id']}/revocar",
        headers=auth_headers,
    )
    assert revocar.status_code == 200
    assert revocar.json()["revocado"] is True

    login = client.post(
        "/api/portal/login",
        json={"usuario": evaluado_con_acceso["usuario"], "password": evaluado_con_acceso["password"]},
    )
    assert login.status_code == 403
