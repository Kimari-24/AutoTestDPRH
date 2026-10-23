"""Pruebas del cargador de evaluaciones desde JSON y de la integridad
del archivo database/contenido/moss.json.

Las pruebas contra la base de datos usan códigos con sufijo único y se
limpian al terminar. Todo el contenido de ejemplo es ficticio.
"""

import copy
import json
import uuid
from pathlib import Path

import pytest
from sqlalchemy import text

from app.core.exceptions.base import ConflictError, ValidationError
from app.db.session import SessionLocal
from app.models.catalogo_prueba import Algoritmo, Opcion, Pregunta, Prueba
from app.models.versionado import VersionPrueba
from app.services.cargador_prueba_service import CargadorPruebaService, validar_definicion

RAIZ = Path(__file__).resolve().parents[2]
MOSS_JSON = RAIZ / "database" / "contenido" / "moss.json"
SUFIJO = uuid.uuid4().hex[:8]


# ---------------------------------------------------------------------------
# Integridad del archivo real del Moss (sin base de datos)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def moss() -> dict:
    return json.loads(MOSS_JSON.read_text(encoding="utf-8"))


def test_moss_es_una_definicion_valida(moss):
    assert validar_definicion(moss) == []


def test_moss_tiene_30_preguntas_numeradas_del_1_al_30(moss):
    assert [p["orden"] for p in moss["preguntas"]] == list(range(1, 31))


def test_moss_cada_pregunta_tiene_exactamente_4_opciones_con_texto(moss):
    for p in moss["preguntas"]:
        assert len(p["opciones"]) == 4, f"Pregunta {p['orden']}"
        assert all(isinstance(o, str) and o.strip() for o in p["opciones"]), f"Pregunta {p['orden']}"


def test_moss_no_repite_enunciados_ni_opciones_dentro_de_una_pregunta(moss):
    enunciados = [p["enunciado"] for p in moss["preguntas"]]
    assert len(set(enunciados)) == 30
    for p in moss["preguntas"]:
        assert len(set(p["opciones"])) == 4, f"Pregunta {p['orden']} repite opciones"


def test_moss_comprobaciones_puntuales_de_la_transcripcion(moss):
    p = {x["orden"]: x for x in moss["preguntas"]}
    assert p[1]["enunciado"].startswith("SE LE HA ASIGNADO UN PUESTO EN UNA EMPRESA")
    assert p[1]["opciones"][3].startswith("Pidiéndoles le permitan hacer los trabajos")
    assert "5:30" in p[17]["enunciado"]
    assert '"TODO LO SABEN"' in p[26]["enunciado"]
    assert p[30]["opciones"][3] == "Abogar por muchas formas"
    assert p[30]["opciones"][2] == "Ceder parcialmente en todas las cuestiones importantes"


def test_moss_no_trae_clave_ni_algoritmo_inventados(moss):
    """Las capturas no incluyen clave de calificación: el archivo no debe
    traer una inventada (reglas del proyecto, ver docs/CARGA_DE_EVALUACIONES.md)."""
    assert "algoritmo" not in moss
    assert all("configuracion" not in p for p in moss["preguntas"])


# ---------------------------------------------------------------------------
# Validación de definiciones
# ---------------------------------------------------------------------------


def _definicion_minima(codigo: str) -> dict:
    return {
        "categoria": {"codigo": f"CATC_{SUFIJO}", "nombre": "Categoría de prueba"},
        "prueba": {"codigo": codigo, "nombre": "Evaluación de prueba"},
        "preguntas": [
            {"orden": 1, "enunciado": "Pregunta de ejemplo uno", "opciones": ["Uno", "Dos", "Tres"]},
            {"orden": 2, "enunciado": "Pregunta de ejemplo dos", "opciones": ["Sí", "No"]},
        ],
    }


def test_validacion_detecta_problemas_comunes():
    d = _definicion_minima("X")
    d["preguntas"][0]["opciones"] = ["Solo una"]
    d["preguntas"][1]["orden"] = 1
    d["preguntas"].append({"orden": 3, "enunciado": "  ", "opciones": ["a", "b"]})
    d["prueba"]["tiempo_limite_minutos"] = 0
    errores = " | ".join(validar_definicion(d))
    assert "al menos 2 opciones" in errores
    assert "repetido" in errores
    assert "enunciado" in errores
    assert "tiempo_limite_minutos" in errores


def test_validacion_rechaza_algoritmo_con_estrategia_desconocida():
    d = _definicion_minima("X")
    d["algoritmo"] = {"nombre": "A", "tipo_calculo": "formula_inventada"}
    assert any("tipo_calculo" in e for e in validar_definicion(d))


# ---------------------------------------------------------------------------
# Carga contra la base de datos
# ---------------------------------------------------------------------------


@pytest.fixture()
def db():
    session = SessionLocal()
    yield session
    session.rollback()
    session.close()


@pytest.fixture(scope="module", autouse=True)
def limpiar_al_final():
    yield
    s = SessionLocal()
    like = f"%{SUFIJO}%"
    for sql in [
        "DELETE FROM bitacora WHERE entidad='pruebas' AND detalle LIKE :l",
        "DELETE FROM escalas WHERE factor_id IN (SELECT f.id FROM factores f JOIN algoritmos al ON f.algoritmo_id=al.id JOIN pruebas p ON al.prueba_id=p.id WHERE p.codigo LIKE :l)",
        "DELETE FROM factores WHERE algoritmo_id IN (SELECT al.id FROM algoritmos al JOIN pruebas p ON al.prueba_id=p.id WHERE p.codigo LIKE :l)",
        "DELETE FROM algoritmos WHERE prueba_id IN (SELECT id FROM pruebas WHERE codigo LIKE :l)",
        "DELETE FROM opciones WHERE pregunta_id IN (SELECT pr.id FROM preguntas pr JOIN version_prueba v ON pr.version_prueba_id=v.id JOIN pruebas p ON v.prueba_id=p.id WHERE p.codigo LIKE :l)",
        "DELETE FROM preguntas WHERE version_prueba_id IN (SELECT v.id FROM version_prueba v JOIN pruebas p ON v.prueba_id=p.id WHERE p.codigo LIKE :l)",
        "DELETE FROM version_prueba WHERE prueba_id IN (SELECT id FROM pruebas WHERE codigo LIKE :l)",
        "DELETE FROM pruebas WHERE codigo LIKE :l",
        "DELETE FROM categorias_prueba WHERE codigo LIKE :l",
    ]:
        s.execute(text(sql), {"l": like})
    s.commit()
    s.close()


def _n(prefijo: str) -> str:
    return f"{prefijo}_{SUFIJO}_{uuid.uuid4().hex[:5]}"


def test_carga_crea_evaluacion_version_preguntas_y_opciones(db):
    codigo = _n("CARGA")
    resumen = CargadorPruebaService(db).cargar(_definicion_minima(codigo))

    assert resumen.prueba_creada and resumen.numero_version == 1
    assert (resumen.total_preguntas, resumen.total_opciones) == (2, 5)
    assert not resumen.algoritmo_creado
    assert any("SIN algoritmo" in a for a in resumen.avisos)

    prueba = db.query(Prueba).filter(Prueba.codigo == codigo).one()
    version = db.query(VersionPrueba).filter(VersionPrueba.prueba_id == prueba.id).one()
    assert version.activa
    preguntas = db.query(Pregunta).filter(Pregunta.version_prueba_id == version.id).order_by(Pregunta.orden).all()
    assert [p.orden for p in preguntas] == [1, 2]
    # Las opciones llevan su letra como valor y su orden de aparición.
    opciones = db.query(Opcion).filter(Opcion.pregunta_id == preguntas[0].id).order_by(Opcion.orden).all()
    assert [(o.orden, o.valor, o.texto) for o in opciones] == [(1, "A", "Uno"), (2, "B", "Dos"), (3, "C", "Tres")]
    assert db.query(Algoritmo).filter(Algoritmo.prueba_id == prueba.id).count() == 0


def test_cargar_dos_veces_sin_pedirlo_se_rechaza_y_no_duplica(db):
    codigo = _n("DUP")
    servicio = CargadorPruebaService(db)
    servicio.cargar(_definicion_minima(codigo))
    with pytest.raises(ConflictError):
        servicio.cargar(_definicion_minima(codigo))
    prueba = db.query(Prueba).filter(Prueba.codigo == codigo).one()
    assert db.query(VersionPrueba).filter(VersionPrueba.prueba_id == prueba.id).count() == 1


def test_version_nueva_deja_activa_solo_la_ultima(db):
    codigo = _n("VER")
    servicio = CargadorPruebaService(db)
    servicio.cargar(_definicion_minima(codigo))
    resumen = servicio.cargar(_definicion_minima(codigo), version_nueva=True)

    assert not resumen.prueba_creada and resumen.numero_version == 2
    prueba = db.query(Prueba).filter(Prueba.codigo == codigo).one()
    versiones = db.query(VersionPrueba).filter(VersionPrueba.prueba_id == prueba.id).order_by(VersionPrueba.numero_version).all()
    assert [(v.numero_version, v.activa) for v in versiones] == [(1, False), (2, True)]


def test_carga_es_todo_o_nada_si_hay_un_tipo_de_pregunta_inexistente(db):
    codigo = _n("ATOMICA")
    d = _definicion_minima(codigo)
    d["preguntas"][1]["tipo"] = "TIPO_QUE_NO_EXISTE"
    with pytest.raises(ValidationError):
        CargadorPruebaService(db).cargar(d)
    assert db.query(Prueba).filter(Prueba.codigo == codigo).count() == 0


def test_un_fallo_a_mitad_de_la_escritura_revierte_todo(db, monkeypatch):
    """El rollback de verdad: para cuando el fallo llega, ya se escribieron la
    evaluación, la versión y las preguntas. Nada de eso debe quedar."""
    codigo = _n("ROLLBACK")
    d = _definicion_minima(codigo)
    d["algoritmo"] = {"nombre": "A", "tipo_calculo": "suma"}

    def _falla(self, prueba, datos):
        raise RuntimeError("fallo simulado a mitad de la carga")

    monkeypatch.setattr(CargadorPruebaService, "_crear_algoritmo", _falla)
    with pytest.raises(RuntimeError):
        CargadorPruebaService(db).cargar(d)

    verificador = SessionLocal()
    try:
        assert verificador.query(Prueba).filter(Prueba.codigo == codigo).count() == 0
        assert verificador.query(Pregunta).join(VersionPrueba).join(Prueba).filter(Prueba.codigo == codigo).count() == 0
    finally:
        verificador.close()


def test_validacion_rechaza_codigos_y_nombres_demasiado_largos():
    d = _definicion_minima("X" * 51)
    assert any("'prueba'" in e for e in validar_definicion(d))
    d = _definicion_minima("OK")
    d["categoria"]["nombre"] = "N" * 151
    assert any("'categoria'" in e for e in validar_definicion(d))


def test_definicion_invalida_no_escribe_nada(db):
    codigo = _n("INVALIDA")
    d = _definicion_minima(codigo)
    d["preguntas"][0]["opciones"] = ["Solo una"]
    with pytest.raises(ValidationError):
        CargadorPruebaService(db).cargar(d)
    assert db.query(Prueba).filter(Prueba.codigo == codigo).count() == 0


def test_carga_con_algoritmo_factores_y_escalas(db):
    codigo = _n("ALGO")
    d = _definicion_minima(codigo)
    d["algoritmo"] = {
        "nombre": "Algoritmo de ejemplo", "tipo_calculo": "suma",
        "factores": [{"codigo": "F1", "nombre": "Factor de ejemplo",
                      "escalas": [{"codigo": "E1", "nombre": "Escala de ejemplo",
                                   "valor_min": 0, "valor_max": 10, "descripcion": "Ejemplo"}]}],
    }
    resumen = CargadorPruebaService(db).cargar(d)
    assert resumen.algoritmo_creado

    prueba = db.query(Prueba).filter(Prueba.codigo == codigo).one()
    algoritmo = db.query(Algoritmo).filter(Algoritmo.prueba_id == prueba.id).one()
    assert algoritmo.tipo_calculo == "suma"
    assert [f.codigo for f in algoritmo.factores] == ["F1"]
    assert [e.codigo for e in algoritmo.factores[0].escalas] == ["E1"]


def test_nueva_version_no_pisa_un_algoritmo_ya_configurado(db):
    codigo = _n("NOPISA")
    d = _definicion_minima(codigo)
    d["algoritmo"] = {"nombre": "Original", "tipo_calculo": "suma"}
    servicio = CargadorPruebaService(db)
    servicio.cargar(d)

    d2 = copy.deepcopy(d)
    d2["algoritmo"] = {"nombre": "Otro", "tipo_calculo": "promedio"}
    resumen = servicio.cargar(d2, version_nueva=True)

    assert not resumen.algoritmo_creado
    assert any("ya tenía un algoritmo" in a for a in resumen.avisos)
    prueba = db.query(Prueba).filter(Prueba.codigo == codigo).one()
    algoritmo = db.query(Algoritmo).filter(Algoritmo.prueba_id == prueba.id).one()
    assert (algoritmo.nombre, algoritmo.tipo_calculo) == ("Original", "suma")
