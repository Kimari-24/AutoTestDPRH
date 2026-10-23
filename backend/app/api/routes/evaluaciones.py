"""
Endpoints de administración del catálogo de evaluaciones (sección 18
de los requisitos).

Todo el módulo está restringido al rol ADMINISTRADOR. Ninguna ruta
aquí crea, valida o expone contenido psicométrico real: solo
administra la estructura genérica (categorías, pruebas, versiones,
preguntas, opciones, algoritmo, factores, escalas) que el motor
universal (Fase 6) usará para ejecutar cualquier evaluación
configurada con datos.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_usuario, require_roles
from app.db.session import get_db
from app.models.catalogo_prueba import Algoritmo, CategoriaPrueba, Escala, Factor, Prueba
from app.models.catalogo_prueba import Opcion, Pregunta
from app.models.seguridad import Usuario
from app.models.versionado import VersionPrueba
from app.schemas.algoritmo import (
    AlgoritmoCreate,
    AlgoritmoOut,
    AlgoritmoUpdate,
    EscalaCreate,
    EscalaOut,
    EscalaUpdate,
    FactorCreate,
    FactorOut,
    FactorUpdate,
    TipoEscalaRef,
    TipoFactorRef,
)
from app.schemas.pregunta import (
    OpcionCreate,
    OpcionOut,
    OpcionUpdate,
    PreguntaCreate,
    PreguntaOut,
    PreguntaUpdate,
    TipoPreguntaRef,
)
from app.schemas.prueba import (
    CategoriaPruebaCreate,
    CategoriaPruebaOut,
    PruebaCreate,
    PruebaOut,
    PruebaUpdate,
    VersionPruebaCreate,
    VersionPruebaOut,
)
from app.services.algoritmo_service import AlgoritmoService
from app.services.pregunta_service import PreguntaService
from app.services.prueba_service import CategoriaPruebaService, PruebaService

router = APIRouter(
    prefix="/evaluaciones",
    tags=["Evaluaciones"],
    dependencies=[Depends(require_roles("ADMINISTRADOR"))],
)


# ---------------------------------------------------------------------------
# Mapeadores a schemas de salida
# ---------------------------------------------------------------------------


def _categoria_out(categoria: CategoriaPrueba) -> CategoriaPruebaOut:
    return CategoriaPruebaOut(
        id=categoria.id,
        codigo=categoria.codigo,
        nombre=categoria.nombre,
        descripcion=categoria.descripcion,
        orden=categoria.orden,
    )


def _prueba_out(prueba: Prueba, total_preguntas_activas: int = 0) -> PruebaOut:
    return PruebaOut(
        id=prueba.id,
        codigo=prueba.codigo,
        nombre=prueba.nombre,
        descripcion=prueba.descripcion,
        instrucciones=prueba.instrucciones,
        tiempo_limite_minutos=prueba.tiempo_limite_minutos,
        intentos_permitidos=prueba.intentos_permitidos,
        activa=prueba.activa,
        categoria=_categoria_out(prueba.categoria),
        total_preguntas_activas=total_preguntas_activas,
        creado_en=prueba.creado_en,
    )


def _version_out(version: VersionPrueba, total_preguntas: int = 0) -> VersionPruebaOut:
    return VersionPruebaOut(
        id=version.id,
        prueba_id=version.prueba_id,
        numero_version=version.numero_version,
        activa=version.activa,
        notas=version.notas,
        creado_en=version.creado_en,
        total_preguntas=total_preguntas,
    )


def _opcion_out(opcion: Opcion) -> OpcionOut:
    return OpcionOut(
        id=opcion.id, texto=opcion.texto, imagen_url=opcion.imagen_url,
        valor=opcion.valor, orden=opcion.orden,
    )


def _pregunta_out(pregunta: Pregunta) -> PreguntaOut:
    return PreguntaOut(
        id=pregunta.id,
        version_prueba_id=pregunta.version_prueba_id,
        tipo_pregunta=TipoPreguntaRef(
            id=pregunta.tipo_pregunta.id,
            codigo=pregunta.tipo_pregunta.codigo,
            nombre=pregunta.tipo_pregunta.nombre,
        ),
        enunciado=pregunta.enunciado,
        imagen_url=pregunta.imagen_url,
        configuracion=pregunta.configuracion,
        orden=pregunta.orden,
        activa=pregunta.activa,
        opciones=[_opcion_out(o) for o in sorted(pregunta.opciones, key=lambda o: o.orden)],
    )


def _escala_out(escala: Escala) -> EscalaOut:
    return EscalaOut(
        id=escala.id,
        factor_id=escala.factor_id,
        tipo_escala=(
            TipoEscalaRef(id=escala.tipo_escala.id, codigo=escala.tipo_escala.codigo, nombre=escala.tipo_escala.nombre)
            if escala.tipo_escala
            else None
        ),
        codigo=escala.codigo,
        nombre=escala.nombre,
        valor_min=escala.valor_min,
        valor_max=escala.valor_max,
        descripcion=escala.descripcion,
        orden=escala.orden,
    )


def _factor_out(factor: Factor) -> FactorOut:
    return FactorOut(
        id=factor.id,
        algoritmo_id=factor.algoritmo_id,
        tipo_factor=(
            TipoFactorRef(id=factor.tipo_factor.id, codigo=factor.tipo_factor.codigo, nombre=factor.tipo_factor.nombre)
            if factor.tipo_factor
            else None
        ),
        codigo=factor.codigo,
        nombre=factor.nombre,
        descripcion=factor.descripcion,
        configuracion=factor.configuracion,
        orden=factor.orden,
        escalas=[_escala_out(e) for e in sorted(factor.escalas, key=lambda e: e.orden)],
    )


def _algoritmo_out(algoritmo: Algoritmo) -> AlgoritmoOut:
    return AlgoritmoOut(
        id=algoritmo.id,
        prueba_id=algoritmo.prueba_id,
        nombre=algoritmo.nombre,
        tipo_calculo=algoritmo.tipo_calculo,
        configuracion=algoritmo.configuracion,
        activo=algoritmo.activo,
        factores=[_factor_out(f) for f in sorted(algoritmo.factores, key=lambda f: f.orden)],
    )


# ---------------------------------------------------------------------------
# Categorías
# ---------------------------------------------------------------------------


@router.get("/categorias", response_model=list[CategoriaPruebaOut])
def listar_categorias(db: Session = Depends(get_db)):
    """Lista las categorías de evaluación (p. ej. INTELIGENCIA, PERSONALIDAD)."""
    service = CategoriaPruebaService(db)
    return [_categoria_out(c) for c in service.listar()]


@router.post("/categorias", response_model=CategoriaPruebaOut, status_code=201)
def crear_categoria(data: CategoriaPruebaCreate, db: Session = Depends(get_db)):
    """Crea una categoría de evaluación."""
    service = CategoriaPruebaService(db)
    return _categoria_out(service.crear(data))


# ---------------------------------------------------------------------------
# Pruebas (evaluaciones)
# ---------------------------------------------------------------------------


@router.get("", response_model=list[PruebaOut])
def listar_pruebas(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    categoria_id: int | None = None,
    solo_activas: bool = False,
    db: Session = Depends(get_db),
):
    """Lista las evaluaciones configuradas."""
    service = PruebaService(db)
    pruebas = service.listar(
        skip=skip, limit=limit, categoria_id=categoria_id, solo_activas=solo_activas
    )
    return [_prueba_out(p, service.contar_preguntas_activas(p.id)) for p in pruebas]


@router.get("/{prueba_id}", response_model=PruebaOut)
def obtener_prueba(prueba_id: int, db: Session = Depends(get_db)):
    """Obtiene el detalle de una evaluación."""
    service = PruebaService(db)
    prueba = service.obtener(prueba_id)
    return _prueba_out(prueba, service.contar_preguntas_activas(prueba_id))


@router.post("", response_model=PruebaOut, status_code=201)
def crear_prueba(
    data: PruebaCreate,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(get_current_usuario),
):
    """Crea una nueva evaluación (estructura vacía, sin preguntas todavía)."""
    service = PruebaService(db)
    prueba = service.crear(data, creado_por_usuario_id=usuario_actual.id)
    return _prueba_out(prueba)


@router.put("/{prueba_id}", response_model=PruebaOut)
def actualizar_prueba(
    prueba_id: int,
    data: PruebaUpdate,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(get_current_usuario),
):
    """Actualiza nombre, descripción, instrucciones, tiempo o intentos de una evaluación."""
    service = PruebaService(db)
    prueba = service.actualizar(prueba_id, data, actualizado_por_usuario_id=usuario_actual.id)
    return _prueba_out(prueba, service.contar_preguntas_activas(prueba_id))


@router.post("/{prueba_id}/activar", response_model=PruebaOut)
def activar_prueba(
    prueba_id: int,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(get_current_usuario),
):
    """Activa una evaluación previamente desactivada."""
    service = PruebaService(db)
    prueba = service.cambiar_estado(prueba_id, activa=True, usuario_id=usuario_actual.id)
    return _prueba_out(prueba, service.contar_preguntas_activas(prueba_id))


@router.delete("/{prueba_id}", response_model=PruebaOut)
def desactivar_prueba(
    prueba_id: int,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(get_current_usuario),
):
    """Desactiva una evaluación (no se elimina físicamente)."""
    service = PruebaService(db)
    prueba = service.cambiar_estado(prueba_id, activa=False, usuario_id=usuario_actual.id)
    return _prueba_out(prueba, service.contar_preguntas_activas(prueba_id))


# ---------------------------------------------------------------------------
# Versiones
# ---------------------------------------------------------------------------


@router.get("/{prueba_id}/versiones", response_model=list[VersionPruebaOut])
def listar_versiones(prueba_id: int, db: Session = Depends(get_db)):
    """Lista las versiones de una evaluación."""
    prueba_service = PruebaService(db)
    pregunta_service = PreguntaService(db)
    versiones = prueba_service.listar_versiones(prueba_id)
    return [
        _version_out(v, len(pregunta_service.listar_por_version(v.id))) for v in versiones
    ]


@router.post("/{prueba_id}/versiones", response_model=VersionPruebaOut, status_code=201)
def crear_version(
    prueba_id: int,
    data: VersionPruebaCreate,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(get_current_usuario),
):
    """Crea una nueva versión de la evaluación (queda activa; desactiva las anteriores)."""
    service = PruebaService(db)
    version = service.crear_version(prueba_id, notas=data.notas, usuario_id=usuario_actual.id)
    return _version_out(version)


@router.post(
    "/{prueba_id}/versiones/{version_id}/activar", response_model=VersionPruebaOut
)
def activar_version(
    prueba_id: int,
    version_id: int,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(get_current_usuario),
):
    """Marca una versión como la vigente (desactiva las demás de la misma evaluación)."""
    service = PruebaService(db)
    version = service.activar_version(prueba_id, version_id, usuario_id=usuario_actual.id)
    return _version_out(version)


# ---------------------------------------------------------------------------
# Preguntas y opciones
# ---------------------------------------------------------------------------


@router.get("/versiones/{version_id}/preguntas", response_model=list[PreguntaOut])
def listar_preguntas(version_id: int, db: Session = Depends(get_db)):
    """Lista las preguntas de una versión de evaluación."""
    service = PreguntaService(db)
    return [_pregunta_out(p) for p in service.listar_por_version(version_id)]


@router.post(
    "/versiones/{version_id}/preguntas", response_model=PreguntaOut, status_code=201
)
def crear_pregunta(
    version_id: int,
    data: PreguntaCreate,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(get_current_usuario),
):
    """Crea una pregunta (con sus opciones, si se envían) en una versión."""
    service = PreguntaService(db)
    pregunta = service.crear(version_id, data, usuario_id=usuario_actual.id)
    return _pregunta_out(pregunta)


@router.put("/preguntas/{pregunta_id}", response_model=PreguntaOut)
def actualizar_pregunta(
    pregunta_id: int,
    data: PreguntaUpdate,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(get_current_usuario),
):
    """Actualiza el enunciado, tipo, configuración u orden de una pregunta."""
    service = PreguntaService(db)
    pregunta = service.actualizar(pregunta_id, data, usuario_id=usuario_actual.id)
    return _pregunta_out(pregunta)


@router.delete("/preguntas/{pregunta_id}", response_model=PreguntaOut)
def desactivar_pregunta(
    pregunta_id: int,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(get_current_usuario),
):
    """Desactiva una pregunta (no se elimina físicamente)."""
    service = PreguntaService(db)
    pregunta = service.desactivar(pregunta_id, usuario_id=usuario_actual.id)
    return _pregunta_out(pregunta)


@router.post(
    "/preguntas/{pregunta_id}/opciones", response_model=OpcionOut, status_code=201
)
def agregar_opcion(
    pregunta_id: int,
    data: OpcionCreate,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(get_current_usuario),
):
    """Agrega una opción de respuesta a una pregunta."""
    service = PreguntaService(db)
    return _opcion_out(service.agregar_opcion(pregunta_id, data, usuario_id=usuario_actual.id))


@router.put("/opciones/{opcion_id}", response_model=OpcionOut)
def actualizar_opcion(
    opcion_id: int,
    data: OpcionUpdate,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(get_current_usuario),
):
    """Actualiza una opción de respuesta."""
    service = PreguntaService(db)
    return _opcion_out(service.actualizar_opcion(opcion_id, data, usuario_id=usuario_actual.id))


@router.delete("/opciones/{opcion_id}", status_code=204)
def eliminar_opcion(
    opcion_id: int,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(get_current_usuario),
):
    """Elimina una opción de respuesta (solo si nadie la ha respondido todavía)."""
    service = PreguntaService(db)
    service.eliminar_opcion(opcion_id, usuario_id=usuario_actual.id)


# ---------------------------------------------------------------------------
# Algoritmo, factores y escalas
# ---------------------------------------------------------------------------


@router.get("/{prueba_id}/algoritmos", response_model=list[AlgoritmoOut])
def listar_algoritmos(prueba_id: int, db: Session = Depends(get_db)):
    """Lista los algoritmos configurados para una evaluación."""
    service = AlgoritmoService(db)
    return [_algoritmo_out(a) for a in service.listar_por_prueba(prueba_id)]


@router.post("/{prueba_id}/algoritmos", response_model=AlgoritmoOut, status_code=201)
def crear_algoritmo(
    prueba_id: int,
    data: AlgoritmoCreate,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(get_current_usuario),
):
    """Crea un algoritmo de calificación para una evaluación."""
    service = AlgoritmoService(db)
    return _algoritmo_out(service.crear(prueba_id, data, usuario_id=usuario_actual.id))


@router.put("/algoritmos/{algoritmo_id}", response_model=AlgoritmoOut)
def actualizar_algoritmo(
    algoritmo_id: int,
    data: AlgoritmoUpdate,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(get_current_usuario),
):
    """Actualiza la configuración de un algoritmo."""
    service = AlgoritmoService(db)
    return _algoritmo_out(service.actualizar(algoritmo_id, data, usuario_id=usuario_actual.id))


@router.post("/algoritmos/{algoritmo_id}/factores", response_model=FactorOut, status_code=201)
def agregar_factor(
    algoritmo_id: int,
    data: FactorCreate,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(get_current_usuario),
):
    """Agrega un factor/dimensión a un algoritmo."""
    service = AlgoritmoService(db)
    return _factor_out(service.agregar_factor(algoritmo_id, data, usuario_id=usuario_actual.id))


@router.put("/factores/{factor_id}", response_model=FactorOut)
def actualizar_factor(
    factor_id: int,
    data: FactorUpdate,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(get_current_usuario),
):
    """Actualiza un factor."""
    service = AlgoritmoService(db)
    return _factor_out(service.actualizar_factor(factor_id, data, usuario_id=usuario_actual.id))


@router.delete("/factores/{factor_id}", status_code=204)
def eliminar_factor(
    factor_id: int,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(get_current_usuario),
):
    """Elimina un factor (y sus escalas)."""
    service = AlgoritmoService(db)
    service.eliminar_factor(factor_id, usuario_id=usuario_actual.id)


@router.post("/factores/{factor_id}/escalas", response_model=EscalaOut, status_code=201)
def agregar_escala(
    factor_id: int,
    data: EscalaCreate,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(get_current_usuario),
):
    """Agrega una escala de interpretación a un factor."""
    service = AlgoritmoService(db)
    return _escala_out(service.agregar_escala(factor_id, data, usuario_id=usuario_actual.id))


@router.put("/escalas/{escala_id}", response_model=EscalaOut)
def actualizar_escala(
    escala_id: int,
    data: EscalaUpdate,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(get_current_usuario),
):
    """Actualiza una escala."""
    service = AlgoritmoService(db)
    return _escala_out(service.actualizar_escala(escala_id, data, usuario_id=usuario_actual.id))


@router.delete("/escalas/{escala_id}", status_code=204)
def eliminar_escala(
    escala_id: int,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(get_current_usuario),
):
    """Elimina una escala."""
    service = AlgoritmoService(db)
    service.eliminar_escala(escala_id, usuario_id=usuario_actual.id)
