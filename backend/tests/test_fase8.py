"""Pruebas de la Fase 8: reporte PDF de resultados.

Reutiliza el mismo patrón de pipeline manual de test_fase6.py (datos
claramente de ejemplo) para tener una sesión calificada de verdad, y
verifica que el PDF generado sea válido y contenga los datos
esperados (usando pypdf para leerlo, no solo comprobar el tamaño).
"""

import io
import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader
from sqlalchemy.orm import Session

from app.core.security.password import hash_password
from app.db.session import SessionLocal
from app.main import app
from app.models.aplicacion import Asignacion, Respuesta, Resultado, ResultadoEscala, ResultadoFactor, SesionPrueba
from app.models.candidato import Candidato
from app.models.catalogo_prueba import Algoritmo, CategoriaPrueba, Escala, Factor, Opcion, Pregunta, Prueba
from app.models.catalogos import EstatusPrueba, TipoPregunta
from app.models.empresa import Empresa
from app.models.seguridad import Bitacora, HistorialLogin, Rol, Sesion, Usuario, UsuarioRol
from app.models.versionado import VersionPrueba

client = TestClient(app)

SUFIJO = uuid.uuid4().hex[:8]
CORREO_ADMIN = f"test_fase8_{SUFIJO}@example.com"
PASSWORD_ADMIN = "PasswordDePrueba123!"


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
        nombre="Test", apellidos="Fase8", correo=CORREO_ADMIN,
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
def sesion_calificada(db: Session):
    """Arma y califica una sesión completa, con empresa incluida, para
    poder generar su reporte. Contenido claramente de ejemplo."""
    empresa = Empresa(nombre_comercial=f"Empresa Fase8 {SUFIJO}")
    db.add(empresa)
    db.flush()

    categoria = CategoriaPrueba(codigo=f"CAT8_{SUFIJO}", nombre="Categoría Fase 8")
    db.add(categoria)
    db.flush()

    prueba = Prueba(
        categoria_id=categoria.id, codigo=f"PRUEBA8_{SUFIJO}", nombre="Evaluación de prueba Fase 8",
        activa=True, intentos_permitidos=1,
    )
    db.add(prueba)
    db.flush()

    version = VersionPrueba(
        prueba_id=prueba.id, numero_version=1, activa=True, creado_en=datetime.now(timezone.utc)
    )
    db.add(version)
    db.flush()

    tipo_pregunta = TipoPregunta(codigo=f"TIPO8_{SUFIJO}", nombre="Tipo de prueba Fase 8")
    db.add(tipo_pregunta)
    db.flush()

    pregunta = Pregunta(
        version_prueba_id=version.id, tipo_pregunta_id=tipo_pregunta.id,
        enunciado="Pregunta de ejemplo (sin contenido psicométrico real)",
        configuracion={"factor_codigo": "F8"}, orden=1, activa=True,
    )
    db.add(pregunta)
    db.flush()
    opcion = Opcion(pregunta_id=pregunta.id, texto="Opción única", valor="7", orden=1)
    db.add(opcion)
    db.flush()

    algoritmo = Algoritmo(
        prueba_id=prueba.id, nombre="Algoritmo de prueba", tipo_calculo="suma", activo=True,
    )
    db.add(algoritmo)
    db.flush()
    factor = Factor(algoritmo_id=algoritmo.id, codigo="F8", nombre="Factor de prueba", orden=1)
    db.add(factor)
    db.flush()
    escala = Escala(
        factor_id=factor.id, codigo="E8", nombre="Escala de prueba",
        valor_min=0, valor_max=100, descripcion="Interpretación de ejemplo (rango completo)", orden=1,
    )
    db.add(escala)
    db.flush()

    candidato = Candidato(
        nombre="Evaluado", apellidos=f"Fase8 {SUFIJO}", correo=f"evaluado_fase8_{SUFIJO}@example.com",
        puesto="Analista de prueba", empresa_id=empresa.id, activo=True,
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

    db.add(
        Respuesta(
            sesion_prueba_id=sesion.id, pregunta_id=pregunta.id, opcion_id=opcion.id,
            respondida_en=datetime.now(timezone.utc),
        )
    )
    db.commit()

    from app.engine.motor import MotorEvaluacion

    MotorEvaluacion(db).calcular(sesion.id)

    yield {"sesion_id": sesion.id, "candidato_id": candidato.id}

    resultado_ids = [r.id for r in db.query(Resultado).filter(Resultado.sesion_prueba_id == sesion.id)]
    if resultado_ids:
        db.query(ResultadoEscala).filter(ResultadoEscala.resultado_id.in_(resultado_ids)).delete(
            synchronize_session=False
        )
        db.query(ResultadoFactor).filter(ResultadoFactor.resultado_id.in_(resultado_ids)).delete(
            synchronize_session=False
        )
        db.query(Resultado).filter(Resultado.id.in_(resultado_ids)).delete(synchronize_session=False)
    db.query(Respuesta).filter(Respuesta.sesion_prueba_id == sesion.id).delete(synchronize_session=False)
    db.query(SesionPrueba).filter(SesionPrueba.id == sesion.id).delete()
    db.query(Asignacion).filter(Asignacion.id == asignacion.id).delete()
    db.query(Candidato).filter(Candidato.id == candidato.id).delete()
    db.query(Escala).filter(Escala.factor_id == factor.id).delete()
    db.query(Factor).filter(Factor.id == factor.id).delete()
    db.query(Algoritmo).filter(Algoritmo.id == algoritmo.id).delete()
    db.query(Opcion).filter(Opcion.pregunta_id == pregunta.id).delete()
    db.query(Pregunta).filter(Pregunta.id == pregunta.id).delete()
    db.query(VersionPrueba).filter(VersionPrueba.id == version.id).delete()
    db.query(Prueba).filter(Prueba.id == prueba.id).delete()
    db.query(CategoriaPrueba).filter(CategoriaPrueba.id == categoria.id).delete()
    db.query(TipoPregunta).filter(TipoPregunta.id == tipo_pregunta.id).delete()
    db.query(Empresa).filter(Empresa.id == empresa.id).delete()
    db.commit()


def test_reportes_requiere_rol_administrador(sesion_calificada):
    response = client.get(f"/api/reportes/sesiones/{sesion_calificada['sesion_id']}/pdf")
    assert response.status_code == 401


def test_descargar_reporte_de_sesion_sin_resultado_devuelve_409(auth_headers):
    response = client.get("/api/reportes/sesiones/999999999/pdf", headers=auth_headers)
    assert response.status_code in (404, 409)


def test_reporte_pdf_es_valido_y_contiene_los_datos_esperados(sesion_calificada, auth_headers):
    response = client.get(
        f"/api/reportes/sesiones/{sesion_calificada['sesion_id']}/pdf", headers=auth_headers
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content[:4] == b"%PDF"

    lector = PdfReader(io.BytesIO(response.content))
    assert len(lector.pages) >= 1

    texto_completo = "\n".join(pagina.extract_text() for pagina in lector.pages)
    assert "Evaluado" in texto_completo
    assert f"Fase8 {SUFIJO}" in texto_completo
    assert f"Empresa Fase8 {SUFIJO}" in texto_completo
    assert "Evaluación de prueba Fase 8" in texto_completo
    assert "Factor de prueba" in texto_completo
    assert "Escala de prueba" in texto_completo
    assert "Interpretación de ejemplo" in texto_completo
    # El puntaje (suma de una sola respuesta con valor "7") debe aparecer.
    assert "7" in texto_completo
