"""Pruebas de la Fase 6: motor universal de evaluaciones.

Construye manualmente un pipeline completo (candidato -> asignación ->
sesión -> respuestas) con datos claramente de ejemplo (nunca
contenido psicométrico real) para verificar que el motor calcula
correctamente cada estrategia genérica: suma, promedio, ponderación,
por_clave, percentil y regla_condicional; y que interpreta el
resultado contra las escalas configuradas.

La API para crear asignaciones/sesiones/respuestas se construye en la
Fase 7 (portal del evaluado); aquí se insertan directamente vía ORM,
como haría ese portal más adelante.
"""

import uuid
from datetime import datetime, timezone

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
from app.models.candidato import Candidato
from app.models.catalogo_prueba import (
    Algoritmo,
    CategoriaPrueba,
    Escala,
    Factor,
    Opcion,
    Pregunta,
    Prueba,
)
from app.models.catalogos import EstatusPrueba, TipoPregunta
from app.models.seguridad import Bitacora, HistorialLogin, Rol, Sesion, Usuario, UsuarioRol
from app.models.versionado import VersionPrueba
from app.engine.estrategias import RespuestaCalculable, ejecutar_estrategia

client = TestClient(app)

SUFIJO = uuid.uuid4().hex[:8]
CORREO_ADMIN = f"test_fase6_{SUFIJO}@example.com"
PASSWORD_ADMIN = "PasswordDePrueba123!"


# ---------------------------------------------------------------------------
# Pruebas unitarias de las estrategias (sin base de datos)
# ---------------------------------------------------------------------------


def _resp(valor_numerico=None, valor_texto=None, **config):
    return RespuestaCalculable(
        pregunta_id=1, valor_numerico=valor_numerico, valor_texto=valor_texto,
        configuracion_pregunta=config,
    )


def test_estrategia_suma():
    respuestas = [_resp(1), _resp(2), _resp(3)]
    puntuacion, interpretacion = ejecutar_estrategia("suma", respuestas, {})
    assert puntuacion == 6
    assert interpretacion is None


def test_estrategia_promedio():
    respuestas = [_resp(2), _resp(4)]
    puntuacion, _ = ejecutar_estrategia("promedio", respuestas, {})
    assert puntuacion == 3


def test_estrategia_ponderacion():
    respuestas = [_resp(2, peso=2), _resp(3, peso=1)]
    puntuacion, _ = ejecutar_estrategia("ponderacion", respuestas, {})
    assert puntuacion == 7  # 2*2 + 3*1


def test_estrategia_por_clave():
    respuestas = [
        _resp(valor_texto="B", clave="B", puntos=5),
        _resp(valor_texto="A", clave="B", puntos=5),
    ]
    puntuacion, _ = ejecutar_estrategia("por_clave", respuestas, {})
    assert puntuacion == 5  # solo la primera coincide con la clave


def test_estrategia_percentil_con_tabla():
    respuestas = [_resp(10)]
    configuracion = {"tabla_percentiles": [{"min": 0, "max": 20, "percentil": 50}]}
    puntuacion, _ = ejecutar_estrategia("percentil", respuestas, configuracion)
    assert puntuacion == 50


def test_estrategia_regla_condicional():
    respuestas = [_resp(15)]
    configuracion = {"reglas": [{"min": 10, "max": 20, "interpretacion": "Rango medio (ejemplo)"}]}
    puntuacion, interpretacion = ejecutar_estrategia("regla_condicional", respuestas, configuracion)
    assert puntuacion == 15
    assert interpretacion == "Rango medio (ejemplo)"


def test_estrategia_no_soportada_lanza_error():
    with pytest.raises(Exception):
        ejecutar_estrategia("formula_secreta", [], {})


# ---------------------------------------------------------------------------
# Prueba de integración: pipeline completo contra PostgreSQL real
# ---------------------------------------------------------------------------


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
        nombre="Test", apellidos="Fase6", correo=CORREO_ADMIN,
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
def pipeline_de_prueba(db: Session):
    """Arma manualmente: categoría -> prueba -> versión -> 2 preguntas
    (una de opción única con clave/puntos configurados, para probar
    "por_clave" en las pruebas unitarias; otra numérica) -> algoritmo
    con 1 factor (hereda "ponderacion" del algoritmo) y 2 escalas ->
    candidato -> asignación -> sesión COMPLETADA -> respuestas.

    Todo el contenido (enunciados, claves, pesos, escalas) es
    claramente de ejemplo, para probar el motor mecánicamente.
    """
    categoria = CategoriaPrueba(codigo=f"CAT6_{SUFIJO}", nombre="Categoría de prueba Fase 6")
    db.add(categoria)
    db.flush()

    prueba = Prueba(
        categoria_id=categoria.id, codigo=f"PRUEBA6_{SUFIJO}", nombre="Evaluación de prueba Fase 6",
        activa=True, intentos_permitidos=1,
    )
    db.add(prueba)
    db.flush()

    version = VersionPrueba(
        prueba_id=prueba.id, numero_version=1, activa=True,
        creado_en=datetime.now(timezone.utc),
    )
    db.add(version)
    db.flush()

    tipo_pregunta = TipoPregunta(codigo=f"TIPO6_{SUFIJO}", nombre="Tipo de prueba Fase 6")
    db.add(tipo_pregunta)
    db.flush()

    # Pregunta 1: opción única, calificada "por_clave" (clave = "B", 5 puntos).
    pregunta_1 = Pregunta(
        version_prueba_id=version.id, tipo_pregunta_id=tipo_pregunta.id,
        enunciado="Pregunta de ejemplo 1 (sin contenido psicométrico real)",
        configuracion={"factor_codigo": "F6", "clave": "B", "puntos": 5},
        orden=1, activa=True,
    )
    db.add(pregunta_1)
    db.flush()
    opcion_a = Opcion(pregunta_id=pregunta_1.id, texto="Opción A", valor="A", orden=1)
    opcion_b = Opcion(pregunta_id=pregunta_1.id, texto="Opción B", valor="B", orden=2)
    db.add_all([opcion_a, opcion_b])
    db.flush()

    # Pregunta 2: numérica, pondera x2 dentro del mismo factor.
    pregunta_2 = Pregunta(
        version_prueba_id=version.id, tipo_pregunta_id=tipo_pregunta.id,
        enunciado="Pregunta de ejemplo 2 (sin contenido psicométrico real)",
        configuracion={"factor_codigo": "F6", "peso": 2},
        orden=2, activa=True,
    )
    db.add(pregunta_2)
    db.flush()

    algoritmo = Algoritmo(
        prueba_id=prueba.id, nombre="Algoritmo de prueba", tipo_calculo="ponderacion", activo=True,
    )
    db.add(algoritmo)
    db.flush()

    factor = Factor(algoritmo_id=algoritmo.id, codigo="F6", nombre="Factor de prueba", orden=1)
    db.add(factor)
    db.flush()

    escala_baja = Escala(
        factor_id=factor.id, codigo="BAJA", nombre="Rango bajo (ejemplo)",
        valor_min=0, valor_max=9, descripcion="Interpretación de ejemplo: rango bajo", orden=1,
    )
    escala_alta = Escala(
        factor_id=factor.id, codigo="ALTA", nombre="Rango alto (ejemplo)",
        valor_min=10, valor_max=100, descripcion="Interpretación de ejemplo: rango alto", orden=2,
    )
    db.add_all([escala_baja, escala_alta])
    db.flush()

    candidato = Candidato(
        nombre="Evaluado", apellidos=f"Fase6 {SUFIJO}", correo=f"evaluado_fase6_{SUFIJO}@example.com",
        activo=True,
    )
    db.add(candidato)
    db.flush()

    estatus_completada = db.query(EstatusPrueba).filter(EstatusPrueba.codigo == "COMPLETADA").one()

    asignacion = Asignacion(
        candidato_id=candidato.id, prueba_id=prueba.id, version_prueba_id=version.id,
        estatus_prueba_id=estatus_completada.id, fecha_asignacion=datetime.now(timezone.utc),
    )
    db.add(asignacion)
    db.flush()

    sesion = SesionPrueba(
        asignacion_id=asignacion.id, estatus_prueba_id=estatus_completada.id,
        iniciada_en=datetime.now(timezone.utc), finalizada_en=datetime.now(timezone.utc),
    )
    db.add(sesion)
    db.flush()

    # Respuesta 1: eligió la opción B (coincide con la clave) -> 5 puntos por_clave.
    db.add(
        Respuesta(
            sesion_prueba_id=sesion.id, pregunta_id=pregunta_1.id, opcion_id=opcion_b.id,
            respondida_en=datetime.now(timezone.utc),
        )
    )
    # Respuesta 2: valor libre "3", peso 2 -> aporta 6 a la ponderación.
    db.add(
        Respuesta(
            sesion_prueba_id=sesion.id, pregunta_id=pregunta_2.id, valor="3",
            respondida_en=datetime.now(timezone.utc),
        )
    )
    db.commit()

    yield {"sesion_id": sesion.id, "factor": factor, "prueba_codigo": prueba.codigo}

    # --- limpieza ---
    resultado_ids = [
        r.id for r in db.query(Resultado).filter(Resultado.sesion_prueba_id == sesion.id)
    ]
    if resultado_ids:
        db.query(ResultadoEscala).filter(ResultadoEscala.resultado_id.in_(resultado_ids)).delete(
            synchronize_session=False
        )
        db.query(ResultadoFactor).filter(ResultadoFactor.resultado_id.in_(resultado_ids)).delete(
            synchronize_session=False
        )
        db.query(Resultado).filter(Resultado.id.in_(resultado_ids)).delete(
            synchronize_session=False
        )
    db.query(Respuesta).filter(Respuesta.sesion_prueba_id == sesion.id).delete(
        synchronize_session=False
    )
    db.query(SesionPrueba).filter(SesionPrueba.id == sesion.id).delete()
    db.query(Asignacion).filter(Asignacion.id == asignacion.id).delete()
    db.query(Candidato).filter(Candidato.id == candidato.id).delete()
    db.query(Escala).filter(Escala.factor_id == factor.id).delete()
    db.query(Factor).filter(Factor.id == factor.id).delete()
    db.query(Algoritmo).filter(Algoritmo.id == algoritmo.id).delete()
    db.query(Opcion).filter(Opcion.pregunta_id.in_([pregunta_1.id])).delete(
        synchronize_session=False
    )
    db.query(Pregunta).filter(Pregunta.id.in_([pregunta_1.id, pregunta_2.id])).delete(
        synchronize_session=False
    )
    db.query(VersionPrueba).filter(VersionPrueba.id == version.id).delete()
    db.query(Prueba).filter(Prueba.id == prueba.id).delete()
    db.query(CategoriaPrueba).filter(CategoriaPrueba.id == categoria.id).delete()
    db.query(TipoPregunta).filter(TipoPregunta.id == tipo_pregunta.id).delete()
    db.commit()


def test_calcular_resultado_via_api(pipeline_de_prueba, auth_headers):
    sesion_id = pipeline_de_prueba["sesion_id"]

    response = client.post(
        f"/api/resultados/sesiones/{sesion_id}/calcular",
        headers=auth_headers,
        json={},
    )
    assert response.status_code == 201
    body = response.json()

    # El factor F6 no define su propio tipo_calculo, así que hereda
    # "ponderacion" del algoritmo. Esa estrategia solo suma valores
    # numéricos * peso: la respuesta de la pregunta 1 (opción "B", un
    # valor de texto) no aporta nada bajo "ponderacion" -- su
    # configuración de "clave"/"puntos" quedaría lista para un factor
    # que sí use la estrategia "por_clave" (probada por separado más
    # arriba). La pregunta 2 vale 3, con peso 2 => 3 * 2 = 6.
    assert body["puntuacion_global"] == 6
    assert len(body["factores"]) == 1
    assert body["factores"][0]["factor_codigo"] == "F6"
    assert body["factores"][0]["puntuacion"] == 6

    # 6 cae en el rango de la escala "BAJA" (0-9).
    assert len(body["escalas"]) == 1
    assert body["escalas"][0]["escala_codigo"] == "BAJA"


def test_no_se_puede_calcular_dos_veces_sin_forzar(pipeline_de_prueba, auth_headers):
    sesion_id = pipeline_de_prueba["sesion_id"]
    response = client.post(
        f"/api/resultados/sesiones/{sesion_id}/calcular", headers=auth_headers, json={}
    )
    assert response.status_code == 409


def test_recalcular_forzado_funciona(pipeline_de_prueba, auth_headers):
    sesion_id = pipeline_de_prueba["sesion_id"]
    response = client.post(
        f"/api/resultados/sesiones/{sesion_id}/calcular",
        headers=auth_headers,
        json={"forzar_recalculo": True},
    )
    assert response.status_code == 201


def test_obtener_resultado_ya_calculado(pipeline_de_prueba, auth_headers):
    sesion_id = pipeline_de_prueba["sesion_id"]
    response = client.get(f"/api/resultados/sesiones/{sesion_id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["puntuacion_global"] == 6


def test_calcular_sesion_inexistente_devuelve_404(auth_headers):
    response = client.post(
        "/api/resultados/sesiones/999999999/calcular", headers=auth_headers, json={}
    )
    assert response.status_code == 404


def test_resultados_requiere_rol_administrador():
    response = client.get("/api/resultados/sesiones/1")
    assert response.status_code == 401
