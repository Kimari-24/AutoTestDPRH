"""
Carga de una evaluación completa desde una definición declarativa
(un archivo JSON) — la forma concreta de cumplir el principio "una
nueva evaluación se incorpora por configuración y datos, sin tocar el
motor" (sección 4 de los requisitos).

Formato de la definición (todo lo marcado "opcional" puede omitirse):

    {
      "categoria": {"codigo": "HABILIDADES_OTROS", "nombre": "Habilidades / Otros"},
      "prueba": {
        "codigo": "MOSS", "nombre": "Prueba de Moss",
        "descripcion": "...",              # opcional
        "instrucciones": "...",            # opcional
        "tiempo_limite_minutos": 30,       # opcional (null = sin límite)
        "intentos_permitidos": 1           # opcional (por defecto 1)
      },
      "notas_version": "...",              # opcional
      "preguntas": [
        {
          "orden": 1,
          "tipo": "OPCION_UNICA",          # opcional (por defecto OPCION_UNICA)
          "enunciado": "...",
          "configuracion": {...},          # opcional: factor_codigo, clave, puntos, peso...
          "opciones": ["texto A", "texto B", ...]
                       # o bien [{"texto": "...", "valor": "..."}]
        }
      ],
      "algoritmo": {                       # opcional
        "nombre": "...", "tipo_calculo": "por_clave",
        "factores": [{"codigo": "F1", "nombre": "...",
                      "escalas": [{"codigo": "...", "nombre": "...",
                                   "valor_min": 0, "valor_max": 10,
                                   "descripcion": "..."}]}]
      }
    }

Este módulo NUNCA completa ni infiere claves, pesos, baremos ni
interpretaciones: carga únicamente lo que la definición trae. Una
evaluación cargada sin `algoritmo` queda sin calificación automática
hasta que DPRH aporte esos datos (ver docs/CARGA_DE_EVALUACIONES.md).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions.base import ConflictError, ValidationError
from app.engine.estrategias import ESTRATEGIAS_DISPONIBLES
from app.models.catalogo_prueba import (
    Algoritmo,
    CategoriaPrueba,
    Escala,
    Factor,
    Opcion,
    Pregunta,
    Prueba,
)
from app.models.catalogos import TipoPregunta
from app.repositories.auditoria_repository import BitacoraRepository
from app.repositories.catalogo_repository import CatalogoRepository
from app.repositories.prueba_repository import (
    CategoriaPruebaRepository,
    PruebaRepository,
    VersionPruebaRepository,
)

LETRAS = "ABCDEFGHIJ"
TIPOS_QUE_REQUIEREN_OPCIONES = {"OPCION_UNICA", "OPCION_MULTIPLE", "VERDADERO_FALSO"}


@dataclass
class ResumenCarga:
    prueba_codigo: str
    prueba_creada: bool
    numero_version: int
    total_preguntas: int
    total_opciones: int
    algoritmo_creado: bool
    avisos: list[str] = field(default_factory=list)


def _texto_valido(valor: Any) -> bool:
    return isinstance(valor, str) and valor.strip() != ""


def _largo_excedido(valor: Any, maximo: int) -> bool:
    return isinstance(valor, str) and len(valor.strip()) > maximo


def validar_definicion(d: Any) -> list[str]:
    """Devuelve la lista de problemas de la definición (vacía = válida).
    No toca la base de datos."""
    errores: list[str] = []
    if not isinstance(d, dict):
        return ["La definición debe ser un objeto JSON."]

    categoria = d.get("categoria")
    if not isinstance(categoria, dict) or not _texto_valido(categoria.get("codigo")) \
            or not _texto_valido(categoria.get("nombre")):
        errores.append("'categoria' requiere 'codigo' y 'nombre'.")
    elif _largo_excedido(categoria["codigo"], 50) or _largo_excedido(categoria["nombre"], 150):
        errores.append("'categoria': 'codigo' admite hasta 50 caracteres y 'nombre' hasta 150.")

    prueba = d.get("prueba")
    if not isinstance(prueba, dict) or not _texto_valido(prueba.get("codigo")) \
            or not _texto_valido(prueba.get("nombre")):
        errores.append("'prueba' requiere 'codigo' y 'nombre'.")
    else:
        if _largo_excedido(prueba["codigo"], 50) or _largo_excedido(prueba["nombre"], 150):
            errores.append("'prueba': 'codigo' admite hasta 50 caracteres y 'nombre' hasta 150.")
        tiempo = prueba.get("tiempo_limite_minutos")
        if tiempo is not None and (not isinstance(tiempo, int) or isinstance(tiempo, bool) or tiempo < 1):
            errores.append("'tiempo_limite_minutos' debe ser un entero >= 1 o null.")
        intentos = prueba.get("intentos_permitidos", 1)
        if not isinstance(intentos, int) or isinstance(intentos, bool) or intentos < 1:
            errores.append("'intentos_permitidos' debe ser un entero >= 1.")

    preguntas = d.get("preguntas")
    if not isinstance(preguntas, list) or not preguntas:
        errores.append("'preguntas' debe ser una lista con al menos una pregunta.")
        preguntas = []

    ordenes_vistos: set[int] = set()
    for posicion, p in enumerate(preguntas, start=1):
        etiqueta = f"Pregunta #{posicion}"
        if not isinstance(p, dict):
            errores.append(f"{etiqueta}: debe ser un objeto.")
            continue
        orden = p.get("orden")
        if not isinstance(orden, int) or isinstance(orden, bool) or orden < 1:
            errores.append(f"{etiqueta}: 'orden' debe ser un entero >= 1.")
        elif orden in ordenes_vistos:
            errores.append(f"{etiqueta}: el 'orden' {orden} está repetido.")
        else:
            ordenes_vistos.add(orden)
            etiqueta = f"Pregunta {orden}"
        if not _texto_valido(p.get("enunciado")):
            errores.append(f"{etiqueta}: falta el 'enunciado'.")

        tipo = p.get("tipo", "OPCION_UNICA")
        opciones = p.get("opciones", [])
        if not isinstance(opciones, list):
            errores.append(f"{etiqueta}: 'opciones' debe ser una lista.")
            continue
        if tipo in TIPOS_QUE_REQUIEREN_OPCIONES and len(opciones) < 2:
            errores.append(f"{etiqueta}: el tipo {tipo} requiere al menos 2 opciones.")
        if len(opciones) > len(LETRAS):
            errores.append(f"{etiqueta}: máximo {len(LETRAS)} opciones.")
        for i, o in enumerate(opciones):
            texto = o if isinstance(o, str) else (o.get("texto") if isinstance(o, dict) else None)
            if not _texto_valido(texto):
                errores.append(f"{etiqueta}: la opción {LETRAS[i] if i < len(LETRAS) else i + 1} no tiene texto.")

    algoritmo = d.get("algoritmo")
    if algoritmo is not None:
        if not isinstance(algoritmo, dict) or not _texto_valido(algoritmo.get("nombre")):
            errores.append("'algoritmo' requiere 'nombre'.")
        elif algoritmo.get("tipo_calculo") not in ESTRATEGIAS_DISPONIBLES:
            errores.append(
                f"'algoritmo.tipo_calculo' debe ser una de: {', '.join(ESTRATEGIAS_DISPONIBLES)}."
            )
        else:
            for f in algoritmo.get("factores", []):
                if not isinstance(f, dict) or not _texto_valido(f.get("codigo")) \
                        or not _texto_valido(f.get("nombre")):
                    errores.append("Cada factor requiere 'codigo' y 'nombre'.")
                    continue
                if _largo_excedido(f["codigo"], 50) or _largo_excedido(f["nombre"], 150):
                    errores.append(f"Factor {f['codigo'][:20]}: 'codigo' hasta 50 caracteres y 'nombre' hasta 150.")
                for e in f.get("escalas", []):
                    if not isinstance(e, dict) or not _texto_valido(e.get("codigo")) \
                            or not _texto_valido(e.get("nombre")):
                        errores.append(f"Factor {f['codigo']}: cada escala requiere 'codigo' y 'nombre'.")
                        continue
                    if _largo_excedido(e["codigo"], 50) or _largo_excedido(e["nombre"], 150):
                        errores.append(f"Escala {e['codigo'][:20]}: 'codigo' hasta 50 caracteres y 'nombre' hasta 150.")
                    vmin, vmax = e.get("valor_min"), e.get("valor_max")
                    if vmin is not None and vmax is not None and vmin > vmax:
                        errores.append(f"Escala {e['codigo']}: valor_min no puede ser mayor que valor_max.")
    return errores


class CargadorPruebaService:
    def __init__(self, db: Session):
        self.db = db
        self.categorias = CategoriaPruebaRepository(db)
        self.pruebas = PruebaRepository(db)
        self.versiones = VersionPruebaRepository(db)
        self.tipos_pregunta = CatalogoRepository(db, TipoPregunta)
        self.bitacora = BitacoraRepository(db)

    def cargar(self, definicion: dict[str, Any], version_nueva: bool = False) -> ResumenCarga:
        errores = validar_definicion(definicion)
        if errores:
            raise ValidationError("Definición inválida: " + " | ".join(errores))

        try:
            resumen = self._cargar_sin_commit(definicion, version_nueva)
            self.db.commit()
            return resumen
        except Exception:
            # Todo o nada: una carga a medias dejaría una evaluación
            # con preguntas faltantes, que es peor que no cargarla.
            self.db.rollback()
            raise

    def _cargar_sin_commit(self, d: dict[str, Any], version_nueva: bool) -> ResumenCarga:
        avisos: list[str] = []
        datos_prueba = d["prueba"]

        # Los tipos de pregunta se comprueban ANTES de escribir nada.
        codigos_tipo = {p.get("tipo", "OPCION_UNICA") for p in d["preguntas"]}
        tipos: dict[str, TipoPregunta] = {}
        for codigo in codigos_tipo:
            tipo = self.tipos_pregunta.get_by_codigo(codigo)
            if tipo is None:
                raise ValidationError(
                    f"El tipo de pregunta '{codigo}' no existe. Ejecuta scripts/seed_catalogos.py."
                )
            tipos[codigo] = tipo

        categoria = self.categorias.get_by_codigo(d["categoria"]["codigo"])
        if categoria is None:
            categoria = self.categorias.create(
                CategoriaPrueba(codigo=d["categoria"]["codigo"], nombre=d["categoria"]["nombre"])
            )
            avisos.append(f"Se creó la categoría '{categoria.codigo}'.")

        prueba = self.pruebas.get_by_codigo(datos_prueba["codigo"])
        prueba_creada = prueba is None
        if prueba is None:
            prueba = self.pruebas.create(
                Prueba(
                    categoria_id=categoria.id,
                    codigo=datos_prueba["codigo"],
                    nombre=datos_prueba["nombre"],
                    descripcion=datos_prueba.get("descripcion"),
                    instrucciones=datos_prueba.get("instrucciones"),
                    tiempo_limite_minutos=datos_prueba.get("tiempo_limite_minutos"),
                    intentos_permitidos=datos_prueba.get("intentos_permitidos", 1),
                    activa=True,
                )
            )
        elif not version_nueva:
            raise ConflictError(
                f"La evaluación '{prueba.codigo}' ya existe. Para cargar este contenido como una "
                "NUEVA VERSIÓN de ella usa la opción --version-nueva."
            )

        version = self.versiones.create(prueba.id, notas=d.get("notas_version"))

        total_opciones = 0
        for p in sorted(d["preguntas"], key=lambda x: x["orden"]):
            pregunta = Pregunta(
                version_prueba_id=version.id,
                tipo_pregunta_id=tipos[p.get("tipo", "OPCION_UNICA")].id,
                enunciado=" ".join(p["enunciado"].split()),
                imagen_url=p.get("imagen_url"),
                configuracion=p.get("configuracion"),
                orden=p["orden"],
                activa=True,
            )
            for i, o in enumerate(p.get("opciones", [])):
                if isinstance(o, str):
                    texto, valor, imagen = o, LETRAS[i], None
                else:
                    texto = o["texto"]
                    valor = o.get("valor", LETRAS[i])
                    imagen = o.get("imagen_url")
                pregunta.opciones.append(
                    Opcion(texto=" ".join(texto.split()), imagen_url=imagen, valor=valor, orden=i + 1)
                )
                total_opciones += 1
            self.db.add(pregunta)
        self.db.flush()

        algoritmo_creado = False
        if "algoritmo" in d:
            if prueba.algoritmos:
                avisos.append("La evaluación ya tenía un algoritmo; no se modificó.")
            else:
                self._crear_algoritmo(prueba, d["algoritmo"])
                algoritmo_creado = True
        elif prueba_creada:
            avisos.append(
                "La evaluación se cargó SIN algoritmo: no se calificará automáticamente "
                "hasta que se configure uno."
            )

        self.bitacora.registrar(
            usuario_id=None,
            accion="CARGAR_EVALUACION",
            entidad="pruebas",
            entidad_id=prueba.id,
            detalle=f"{prueba.codigo} v{version.numero_version}: {len(d['preguntas'])} preguntas",
        )
        return ResumenCarga(
            prueba_codigo=prueba.codigo,
            prueba_creada=prueba_creada,
            numero_version=version.numero_version,
            total_preguntas=len(d["preguntas"]),
            total_opciones=total_opciones,
            algoritmo_creado=algoritmo_creado,
            avisos=avisos,
        )

    def _crear_algoritmo(self, prueba: Prueba, datos: dict[str, Any]) -> None:
        algoritmo = Algoritmo(
            prueba_id=prueba.id,
            nombre=datos["nombre"],
            tipo_calculo=datos["tipo_calculo"],
            configuracion=datos.get("configuracion"),
            activo=True,
        )
        self.db.add(algoritmo)
        self.db.flush()
        for orden_f, f in enumerate(datos.get("factores", []), start=1):
            factor = Factor(
                algoritmo_id=algoritmo.id,
                codigo=f["codigo"],
                nombre=f["nombre"],
                descripcion=f.get("descripcion"),
                configuracion=f.get("configuracion"),
                orden=f.get("orden", orden_f),
            )
            self.db.add(factor)
            self.db.flush()
            for orden_e, e in enumerate(f.get("escalas", []), start=1):
                self.db.add(
                    Escala(
                        factor_id=factor.id,
                        codigo=e["codigo"],
                        nombre=e["nombre"],
                        valor_min=e.get("valor_min"),
                        valor_max=e.get("valor_max"),
                        descripcion=e.get("descripcion"),
                        orden=e.get("orden", orden_e),
                    )
                )
