"""Pruebas de regresión de los hallazgos del reporte de QA.

Cada prueba reproduce los pasos del hallazgo (BUG-NN del reporte) y
verifica el comportamiento correcto. Todo el contenido es de ejemplo.
Los datos usan un sufijo único y se limpian al terminar el módulo.
"""

import time
import uuid
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.security.password import hash_password
from app.db.session import SessionLocal
from app.engine.estrategias import RespuestaCalculable, ejecutar_estrategia
from app.main import app
from app.models.seguridad import Rol, Usuario, UsuarioRol

client = TestClient(app)

SUFIJO = uuid.uuid4().hex[:8]
CORREO_ADMIN = f"qa_admin_{SUFIJO}@example.com"
PASSWORD_ADMIN = "PasswordDePrueba123!"


# ---------------------------------------------------------------------------
# Infraestructura
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def db() -> Session:
    session = SessionLocal()
    yield session
    session.close()


def _borrar_datos_del_modulo(db: Session) -> None:
    """Borra todo lo creado por este módulo (todo lleva SUFIJO)."""
    like = f"%{SUFIJO}%"
    pasos = [
        "DELETE FROM resultado_escalas WHERE resultado_id IN (SELECT r.id FROM resultados r JOIN sesiones_prueba sp ON r.sesion_prueba_id=sp.id JOIN asignaciones a ON sp.asignacion_id=a.id JOIN candidatos c ON a.candidato_id=c.id WHERE c.correo LIKE :l)",
        "DELETE FROM resultado_factores WHERE resultado_id IN (SELECT r.id FROM resultados r JOIN sesiones_prueba sp ON r.sesion_prueba_id=sp.id JOIN asignaciones a ON sp.asignacion_id=a.id JOIN candidatos c ON a.candidato_id=c.id WHERE c.correo LIKE :l)",
        "DELETE FROM resultados WHERE sesion_prueba_id IN (SELECT sp.id FROM sesiones_prueba sp JOIN asignaciones a ON sp.asignacion_id=a.id JOIN candidatos c ON a.candidato_id=c.id WHERE c.correo LIKE :l)",
        "DELETE FROM respuestas WHERE sesion_prueba_id IN (SELECT sp.id FROM sesiones_prueba sp JOIN asignaciones a ON sp.asignacion_id=a.id JOIN candidatos c ON a.candidato_id=c.id WHERE c.correo LIKE :l)",
        "DELETE FROM sesiones_prueba WHERE asignacion_id IN (SELECT a.id FROM asignaciones a JOIN candidatos c ON a.candidato_id=c.id WHERE c.correo LIKE :l)",
        "DELETE FROM asignaciones WHERE candidato_id IN (SELECT id FROM candidatos WHERE correo LIKE :l)",
        "DELETE FROM historial_login WHERE usuario_temporal_id IN (SELECT ut.id FROM usuarios_temporales ut JOIN candidatos c ON ut.candidato_id=c.id WHERE c.correo LIKE :l)",
        "DELETE FROM usuarios_temporales WHERE candidato_id IN (SELECT id FROM candidatos WHERE correo LIKE :l)",
        "DELETE FROM candidatos WHERE correo LIKE :l",
        "DELETE FROM empresas WHERE nombre_comercial LIKE :l",
        "DELETE FROM escalas WHERE factor_id IN (SELECT f.id FROM factores f JOIN algoritmos al ON f.algoritmo_id=al.id JOIN pruebas p ON al.prueba_id=p.id WHERE p.codigo LIKE :l)",
        "DELETE FROM factores WHERE algoritmo_id IN (SELECT al.id FROM algoritmos al JOIN pruebas p ON al.prueba_id=p.id WHERE p.codigo LIKE :l)",
        "DELETE FROM algoritmos WHERE prueba_id IN (SELECT id FROM pruebas WHERE codigo LIKE :l)",
        "DELETE FROM opciones WHERE pregunta_id IN (SELECT pr.id FROM preguntas pr JOIN version_prueba v ON pr.version_prueba_id=v.id JOIN pruebas p ON v.prueba_id=p.id WHERE p.codigo LIKE :l)",
        "DELETE FROM preguntas WHERE version_prueba_id IN (SELECT v.id FROM version_prueba v JOIN pruebas p ON v.prueba_id=p.id WHERE p.codigo LIKE :l)",
        "DELETE FROM version_prueba WHERE prueba_id IN (SELECT id FROM pruebas WHERE codigo LIKE :l)",
        "DELETE FROM pruebas WHERE codigo LIKE :l",
        "DELETE FROM categorias_prueba WHERE codigo LIKE :l",
        "DELETE FROM sesiones WHERE usuario_id IN (SELECT id FROM usuarios WHERE correo LIKE :l)",
        "DELETE FROM historial_login WHERE usuario_id IN (SELECT id FROM usuarios WHERE correo LIKE :l)",
        "DELETE FROM bitacora WHERE usuario_id IN (SELECT id FROM usuarios WHERE correo LIKE :l)",
        "DELETE FROM usuario_roles WHERE usuario_id IN (SELECT id FROM usuarios WHERE correo LIKE :l)",
        "DELETE FROM usuarios WHERE correo LIKE :l",
    ]
    for sql in pasos:
        db.execute(text(sql), {"l": like})
    db.commit()


def _crear_admin(db: Session, correo: str) -> None:
    rol = db.query(Rol).filter(Rol.codigo == "ADMINISTRADOR").one_or_none()
    if rol is None:
        rol = Rol(codigo="ADMINISTRADOR", nombre="Administrador")
        db.add(rol)
        db.flush()
    usuario = Usuario(
        nombre="QA", apellidos="Regresion", correo=correo,
        password_hash=hash_password(PASSWORD_ADMIN), activo=True,
    )
    db.add(usuario)
    db.flush()
    db.add(UsuarioRol(usuario_id=usuario.id, rol_id=rol.id))
    db.commit()


def _login_admin(correo: str, password: str = PASSWORD_ADMIN) -> dict:
    respuesta = client.post("/api/auth/login", json={"correo": correo, "password": password})
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


@pytest.fixture(scope="module", autouse=True)
def entorno(db: Session):
    _crear_admin(db, CORREO_ADMIN)
    yield
    _borrar_datos_del_modulo(db)


@pytest.fixture(scope="module")
def h() -> dict:
    return {"Authorization": f"Bearer {_login_admin(CORREO_ADMIN)['access_token']}"}


def _n(prefijo: str) -> str:
    """Código/correo único dentro del módulo."""
    return f"{prefijo}_{SUFIJO}_{uuid.uuid4().hex[:5]}"


def _crear_prueba(h, *, con_pregunta=True, tipo_calculo="suma", clave=None, version=True) -> dict:
    """Crea categoría + prueba (+ versión + pregunta con 2 opciones +
    algoritmo con un factor F1) por la API. Devuelve ids útiles."""
    cat = client.post("/api/evaluaciones/categorias", headers=h,
                      json={"codigo": _n("CAT"), "nombre": "Categoría QA"}).json()
    prueba = client.post("/api/evaluaciones", headers=h, json={
        "categoria_codigo": cat["codigo"], "codigo": _n("PR"), "nombre": "Evaluación QA",
    }).json()
    info = {"prueba_id": prueba["id"]}

    algoritmo = client.post(f"/api/evaluaciones/{prueba['id']}/algoritmos", headers=h,
                            json={"nombre": "Algoritmo QA", "tipo_calculo": tipo_calculo})
    assert algoritmo.status_code == 201, algoritmo.text
    info["algoritmo_id"] = algoritmo.json()["id"]
    factor = client.post(f"/api/evaluaciones/algoritmos/{info['algoritmo_id']}/factores", headers=h,
                         json={"codigo": "F1", "nombre": "Factor QA"})
    assert factor.status_code == 201, factor.text
    info["factor_id"] = factor.json()["id"]

    if version:
        v = client.post(f"/api/evaluaciones/{prueba['id']}/versiones", headers=h, json={}).json()
        info["version_id"] = v["id"]
        if con_pregunta:
            configuracion = {"factor_codigo": "F1"}
            if clave is not None:
                configuracion.update({"clave": clave, "puntos": 5})
            p = client.post(f"/api/evaluaciones/versiones/{v['id']}/preguntas", headers=h, json={
                "tipo_pregunta_codigo": "OPCION_UNICA", "enunciado": "Pregunta de ejemplo QA",
                "orden": 1, "configuracion": configuracion,
                "opciones": [{"texto": "Uno", "valor": "1", "orden": 1},
                             {"texto": "Dos", "valor": "2", "orden": 2}],
            })
            assert p.status_code == 201, p.text
            info["pregunta_id"] = p.json()["id"]
    return info


def _crear_evaluado(h, prefijo="ev") -> dict:
    r = client.post("/api/evaluados", headers=h, json={
        "nombre": "Evaluado", "apellidos": "QA", "correo": f"{_n(prefijo)}@example.com",
    })
    assert r.status_code == 201, r.text
    return r.json()


def _acceso(h, candidato_id: int) -> dict:
    r = client.post(f"/api/evaluados/{candidato_id}/accesos-temporales", headers=h,
                    json={"horas_vigencia": 24})
    assert r.status_code == 201, r.text
    return r.json()


def _asignar(h, candidato_id: int, prueba_id: int, **extra):
    return client.post(f"/api/evaluados/{candidato_id}/asignaciones", headers=h,
                       json={"prueba_id": prueba_id, **extra})


def _login_evaluado(acceso: dict):
    return client.post("/api/portal/login",
                       json={"usuario": acceso["usuario"], "password": acceso["password_temporal"]})


def _headers_evaluado(acceso: dict) -> dict:
    r = _login_evaluado(acceso)
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# ---------------------------------------------------------------------------
# BUG-01 (crítico): por_clave nunca coincidía con claves numéricas
# ---------------------------------------------------------------------------


def _resp(numerico=None, texto=None):
    return RespuestaCalculable(pregunta_id=1, valor_numerico=numerico, valor_texto=texto,
                               configuracion_pregunta={"clave": "1", "puntos": 5})


def test_bug01_por_clave_unidad_clave_numerica():
    puntos, _ = ejecutar_estrategia("por_clave", [_resp(numerico=1.0)], {})
    assert puntos == 5


def test_bug01_por_clave_unidad_distingue_acierto_de_error():
    puntos, _ = ejecutar_estrategia("por_clave", [_resp(numerico=2.0)], {})
    assert puntos == 0


def test_bug01_por_clave_unidad_clave_de_texto_sigue_funcionando():
    r = RespuestaCalculable(1, None, "B", {"clave": "B", "puntos": 3})
    assert ejecutar_estrategia("por_clave", [r], {})[0] == 3


def test_bug01_por_clave_flujo_completo_califica_el_acierto(h):
    """El caso exacto del QA: opciones con valor "1"/"2", clave "1"."""
    info = _crear_prueba(h, tipo_calculo="por_clave", clave="1")
    ev = _crear_evaluado(h)
    assert _asignar(h, ev["id"], info["prueba_id"]).status_code == 201
    hp = _headers_evaluado(_acceso(h, ev["id"]))

    mis = client.get("/api/portal/mis-evaluaciones", headers=hp).json()
    sesion = client.post(f"/api/portal/evaluaciones/{mis[0]['asignacion_id']}/iniciar", headers=hp).json()
    preguntas = client.get(f"/api/portal/sesiones/{sesion['sesion_id']}/preguntas", headers=hp).json()
    opcion_uno = next(o for o in preguntas[0]["opciones"] if o["texto"] == "Uno")
    client.put(f"/api/portal/sesiones/{sesion['sesion_id']}/preguntas/{preguntas[0]['id']}/respuesta",
               headers=hp, json={"opcion_id": opcion_uno["id"]})
    fin = client.post(f"/api/portal/sesiones/{sesion['sesion_id']}/finalizar", headers=hp)
    assert fin.json()["estatus"] == "CALIFICADA"

    resultado = client.get(f"/api/resultados/sesiones/{sesion['sesion_id']}", headers=h).json()
    assert resultado["puntuacion_global"] == 5


# ---------------------------------------------------------------------------
# BUG-02: evaluado desactivado seguía pudiendo entrar
# ---------------------------------------------------------------------------


def test_bug02_evaluado_desactivado_no_puede_iniciar_sesion(h):
    ev = _crear_evaluado(h)
    acceso = _acceso(h, ev["id"])
    assert client.delete(f"/api/evaluados/{ev['id']}", headers=h).status_code == 200
    assert _login_evaluado(acceso).status_code == 403


def test_bug02_desactivar_corta_tambien_una_sesion_ya_abierta(h):
    ev = _crear_evaluado(h)
    acceso = _acceso(h, ev["id"])
    hp = _headers_evaluado(acceso)
    assert client.get("/api/portal/mis-evaluaciones", headers=hp).status_code == 200
    client.delete(f"/api/evaluados/{ev['id']}", headers=h)
    assert client.get("/api/portal/mis-evaluaciones", headers=hp).status_code == 403


# ---------------------------------------------------------------------------
# BUG-03: fecha_limite no se respetaba
# ---------------------------------------------------------------------------


def test_bug03_no_se_puede_iniciar_despues_de_la_fecha_limite(h, db: Session):
    info = _crear_prueba(h)
    ev = _crear_evaluado(h)
    asignacion = _asignar(h, ev["id"], info["prueba_id"],
                          fecha_limite=(date.today() + timedelta(days=5)).isoformat() + "T12:00:00Z").json()
    hp = _headers_evaluado(_acceso(h, ev["id"]))

    # Simula que el plazo ya venció.
    db.execute(text("UPDATE asignaciones SET fecha_limite = now() - interval '1 day' WHERE id=:i"),
               {"i": asignacion["id"]})
    db.commit()

    mis = client.get("/api/portal/mis-evaluaciones", headers=hp).json()
    assert mis[0]["puede_iniciar"] is False
    iniciar = client.post(f"/api/portal/evaluaciones/{asignacion['id']}/iniciar", headers=hp)
    assert iniciar.status_code == 409


# ---------------------------------------------------------------------------
# BUG-04: cambiar contraseña no revocaba sesiones
# ---------------------------------------------------------------------------


def test_bug04_cambiar_password_invalida_los_refresh_tokens(db: Session):
    correo = f"qa_pw_{SUFIJO}@example.com"
    _crear_admin(db, correo)
    tokens = _login_admin(correo)

    cambio = client.put("/api/usuarios/me/password",
                        headers={"Authorization": f"Bearer {tokens['access_token']}"},
                        json={"password_actual": PASSWORD_ADMIN, "password_nueva": "OtraPasswordSegura1!"})
    assert cambio.status_code == 204

    refresh = client.post("/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refresh.status_code == 401


# ---------------------------------------------------------------------------
# BUG-05: el refresh token no rotaba
# ---------------------------------------------------------------------------


def test_bug05_refresh_rota_y_el_token_usado_deja_de_servir(db: Session):
    correo = f"qa_rot_{SUFIJO}@example.com"
    _crear_admin(db, correo)
    original = _login_admin(correo)["refresh_token"]

    primero = client.post("/api/auth/refresh", json={"refresh_token": original})
    assert primero.status_code == 200
    nuevo = primero.json()["refresh_token"]
    assert nuevo != original

    assert client.post("/api/auth/refresh", json={"refresh_token": original}).status_code == 401
    assert client.post("/api/auth/refresh", json={"refresh_token": nuevo}).status_code == 200


# ---------------------------------------------------------------------------
# BUG-06: el token del evaluado seguía sirviendo tras logout / nuevo login
# ---------------------------------------------------------------------------


def test_bug06_token_de_evaluado_muere_con_el_logout(h):
    ev = _crear_evaluado(h)
    acceso = _acceso(h, ev["id"])
    hp = _headers_evaluado(acceso)
    assert client.post("/api/portal/logout", headers=hp).status_code == 204
    assert client.get("/api/portal/mis-evaluaciones", headers=hp).status_code == 401


def test_bug06_un_nuevo_login_invalida_el_token_anterior(h):
    ev = _crear_evaluado(h)
    acceso = _acceso(h, ev["id"])
    primero = _headers_evaluado(acceso)
    time.sleep(0.01)
    segundo = _headers_evaluado(acceso)

    assert client.get("/api/portal/mis-evaluaciones", headers=primero).status_code == 401
    assert client.get("/api/portal/mis-evaluaciones", headers=segundo).status_code == 200


def test_bug06_escenario_exacto_logout_y_luego_nuevo_login(h):
    """Caso literal del QA: tras un logout, un nuevo login reactivaba los
    tokens anteriores (antes bastaba con que `sesion_activa` volviera a
    ser True)."""
    ev = _crear_evaluado(h)
    acceso = _acceso(h, ev["id"])
    viejo = _headers_evaluado(acceso)
    assert client.post("/api/portal/logout", headers=viejo).status_code == 204
    time.sleep(0.01)
    nuevo = _headers_evaluado(acceso)

    assert client.get("/api/portal/mis-evaluaciones", headers=viejo).status_code == 401
    assert client.get("/api/portal/mis-evaluaciones", headers=nuevo).status_code == 200


# ---------------------------------------------------------------------------
# BUG-07 / BUG-13: paginación sin límites
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("ruta", ["/api/evaluados", "/api/empresas", "/api/usuarios", "/api/evaluaciones"])
def test_bug07_y_13_paginacion_con_limites(ruta, h):
    assert client.get(f"{ruta}?skip=-1", headers=h).status_code == 422
    assert client.get(f"{ruta}?limit=0", headers=h).status_code == 422
    assert client.get(f"{ruta}?limit=-5", headers=h).status_code == 422
    assert client.get(f"{ruta}?limit=100000", headers=h).status_code == 422
    assert client.get(f"{ruta}?skip=0&limit=200", headers=h).status_code == 200


# ---------------------------------------------------------------------------
# BUG-08: null en campos obligatorios daba 500
# ---------------------------------------------------------------------------


def test_bug08_null_en_campos_obligatorios_devuelve_422_no_500(h):
    empresa = client.post("/api/empresas", headers=h,
                          json={"nombre_comercial": f"Empresa {SUFIJO}"}).json()
    assert client.put(f"/api/empresas/{empresa['id']}", headers=h,
                      json={"nombre_comercial": None}).status_code == 422

    info = _crear_prueba(h)
    assert client.put(f"/api/evaluaciones/{info['prueba_id']}", headers=h,
                      json={"nombre": None}).status_code == 422
    assert client.put(f"/api/evaluaciones/{info['prueba_id']}", headers=h,
                      json={"intentos_permitidos": None}).status_code == 422
    assert client.put(f"/api/evaluaciones/algoritmos/{info['algoritmo_id']}", headers=h,
                      json={"nombre": None}).status_code == 422

    opcion_id = client.get(f"/api/evaluaciones/versiones/{info['version_id']}/preguntas",
                           headers=h).json()[0]["opciones"][0]["id"]
    assert client.put(f"/api/evaluaciones/opciones/{opcion_id}", headers=h,
                      json={"orden": None}).status_code == 422


def test_bug08_omitir_un_campo_sigue_siendo_valido(h):
    empresa = client.post("/api/empresas", headers=h,
                          json={"nombre_comercial": f"Empresa {SUFIJO} B"}).json()
    r = client.put(f"/api/empresas/{empresa['id']}", headers=h, json={"telefono_contacto": "555"})
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# BUG-09: un administrador podía quedarse sin acceso
# ---------------------------------------------------------------------------


def test_bug09_un_admin_no_puede_desactivarse_a_si_mismo(db: Session):
    correo = f"qa_self_{SUFIJO}@example.com"
    _crear_admin(db, correo)
    hh = {"Authorization": f"Bearer {_login_admin(correo)['access_token']}"}
    mi_id = client.get("/api/auth/me", headers=hh).json()["id"]

    assert client.delete(f"/api/usuarios/{mi_id}", headers=hh).status_code == 409
    quitar_rol = client.put(f"/api/usuarios/{mi_id}", headers=hh, json={"roles": ["EVALUADO"]})
    assert quitar_rol.status_code == 409
    # Sigue pudiendo operar.
    assert client.get("/api/auth/me", headers=hh).status_code == 200


# ---------------------------------------------------------------------------
# BUG-10 / BUG-11: asignaciones inválidas
# ---------------------------------------------------------------------------


def test_bug10_no_se_asigna_a_un_evaluado_desactivado(h):
    info = _crear_prueba(h)
    ev = _crear_evaluado(h)
    client.delete(f"/api/evaluados/{ev['id']}", headers=h)
    assert _asignar(h, ev["id"], info["prueba_id"]).status_code == 409


def test_bug10_no_se_asigna_una_evaluacion_desactivada(h):
    info = _crear_prueba(h)
    ev = _crear_evaluado(h)
    client.delete(f"/api/evaluaciones/{info['prueba_id']}", headers=h)
    assert _asignar(h, ev["id"], info["prueba_id"]).status_code == 409


def test_bug11_no_se_asigna_una_evaluacion_sin_version_vigente(h):
    info = _crear_prueba(h, version=False)
    ev = _crear_evaluado(h)
    assert _asignar(h, ev["id"], info["prueba_id"]).status_code == 422


def test_bug11_no_se_inicia_una_evaluacion_sin_preguntas_ni_se_gasta_el_intento(h):
    info = _crear_prueba(h, con_pregunta=False)  # versión vacía
    ev = _crear_evaluado(h)
    asignacion = _asignar(h, ev["id"], info["prueba_id"]).json()
    hp = _headers_evaluado(_acceso(h, ev["id"]))

    for _ in range(3):  # aunque insista, nunca se consume el intento
        r = client.post(f"/api/portal/evaluaciones/{asignacion['id']}/iniciar", headers=hp)
        assert r.status_code == 409

    # Al agregar una pregunta, la evaluación ya se puede iniciar.
    client.post(f"/api/evaluaciones/versiones/{info['version_id']}/preguntas", headers=h, json={
        "tipo_pregunta_codigo": "OPCION_UNICA", "enunciado": "Pregunta de ejemplo QA",
        "orden": 1, "opciones": [{"texto": "Uno", "valor": "1", "orden": 1}],
    })
    r = client.post(f"/api/portal/evaluaciones/{asignacion['id']}/iniciar", headers=hp)
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# BUG-12: tipo_calculo inválido se aceptaba
# ---------------------------------------------------------------------------


def test_bug12_tipo_calculo_invalido_se_rechaza_al_crear_y_al_actualizar(h):
    info = _crear_prueba(h)
    crear = client.post(f"/api/evaluaciones/{info['prueba_id']}/algoritmos", headers=h,
                        json={"nombre": "X", "tipo_calculo": "formula_inventada"})
    assert crear.status_code == 422
    actualizar = client.put(f"/api/evaluaciones/algoritmos/{info['algoritmo_id']}", headers=h,
                            json={"tipo_calculo": "formula_inventada"})
    assert actualizar.status_code == 422
    factor = client.post(f"/api/evaluaciones/algoritmos/{info['algoritmo_id']}/factores", headers=h,
                         json={"codigo": "F2", "nombre": "F2", "configuracion": {"tipo_calculo": "nope"}})
    assert factor.status_code == 422


def test_bug12_todas_las_estrategias_soportadas_se_aceptan(h):
    info = _crear_prueba(h)
    for estrategia in ("suma", "puntuacion_directa", "promedio", "ponderacion",
                       "por_clave", "percentil", "regla_condicional"):
        r = client.put(f"/api/evaluaciones/algoritmos/{info['algoritmo_id']}", headers=h,
                       json={"tipo_calculo": estrategia})
        assert r.status_code == 200, estrategia


# ---------------------------------------------------------------------------
# BUG-14: correos sensibles a mayúsculas
# ---------------------------------------------------------------------------


def test_bug14_login_no_distingue_mayusculas_en_el_correo():
    r = client.post("/api/auth/login",
                    json={"correo": CORREO_ADMIN.upper(), "password": PASSWORD_ADMIN})
    assert r.status_code == 200


def test_bug14_no_se_duplican_usuarios_ni_evaluados_por_mayusculas(h):
    correo = f"Mixto_{SUFIJO}@Example.com"
    crear = client.post("/api/usuarios", headers=h, json={
        "nombre": "A", "apellidos": "B", "correo": correo,
        "password": "PasswordDePrueba123!", "roles": ["ADMINISTRADOR"],
    })
    assert crear.status_code == 201
    assert crear.json()["correo"] == correo.lower()
    duplicado = client.post("/api/usuarios", headers=h, json={
        "nombre": "A", "apellidos": "B", "correo": correo.lower(),
        "password": "PasswordDePrueba123!", "roles": ["ADMINISTRADOR"],
    })
    assert duplicado.status_code == 409

    ev = {"nombre": "A", "apellidos": "B", "correo": f"Ev_{SUFIJO}@Example.com"}
    assert client.post("/api/evaluados", headers=h, json=ev).status_code == 201
    ev["correo"] = ev["correo"].lower()
    assert client.post("/api/evaluados", headers=h, json=ev).status_code == 409


# ---------------------------------------------------------------------------
# BUG-15: fechas imposibles
# ---------------------------------------------------------------------------


def test_bug15_fecha_de_nacimiento_futura_se_rechaza(h):
    futura = (date.today() + timedelta(days=30)).isoformat()
    r = client.post("/api/evaluados", headers=h, json={
        "nombre": "A", "apellidos": "B", "correo": f"{_n('fut')}@example.com",
        "fecha_nacimiento": futura,
    })
    assert r.status_code == 422


def test_bug15_fecha_limite_en_el_pasado_se_rechaza(h):
    info = _crear_prueba(h)
    ev = _crear_evaluado(h)
    r = _asignar(h, ev["id"], info["prueba_id"], fecha_limite="2000-01-01T00:00:00Z")
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# BUG-16: escala con rango invertido
# ---------------------------------------------------------------------------


def test_bug16_escala_con_rango_invertido_se_rechaza_al_crear_y_al_actualizar(h):
    info = _crear_prueba(h)
    invertida = client.post(f"/api/evaluaciones/factores/{info['factor_id']}/escalas", headers=h,
                            json={"codigo": "E1", "nombre": "E1", "valor_min": 10, "valor_max": 1})
    assert invertida.status_code == 422

    valida = client.post(f"/api/evaluaciones/factores/{info['factor_id']}/escalas", headers=h,
                         json={"codigo": "E2", "nombre": "E2", "valor_min": 0, "valor_max": 10})
    assert valida.status_code == 201
    escala_id = valida.json()["id"]
    # Solo se sube el mínimo por encima del máximo ya guardado.
    r = client.put(f"/api/evaluaciones/escalas/{escala_id}", headers=h, json={"valor_min": 50})
    assert r.status_code == 422
    # Y la escala conserva su rango original.
    guardada = client.get(f"/api/evaluaciones/{info['prueba_id']}/algoritmos", headers=h).json()
    escala = guardada[0]["factores"][0]["escalas"][0]
    assert (escala["valor_min"], escala["valor_max"]) == (0, 10)
