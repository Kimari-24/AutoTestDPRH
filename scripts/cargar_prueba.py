#!/usr/bin/env python3
"""
Carga una evaluación completa (categoría, evaluación, versión,
preguntas, opciones y —si la definición lo trae— algoritmo, factores y
escalas) desde un archivo JSON.

Uso (desde la raíz del proyecto, con migraciones y catálogos ya
sembrados — ver docs/INSTALACION.md):

    # solo validar el archivo, sin tocar la base de datos
    python3 scripts/cargar_prueba.py database/contenido/moss.json --validar

    # cargarla
    python3 scripts/cargar_prueba.py database/contenido/moss.json

    # la evaluación ya existe y quieres cargar este contenido como una
    # NUEVA VERSIÓN (p. ej. al agregar la clave de calificación)
    python3 scripts/cargar_prueba.py database/contenido/moss.json --version-nueva

Formato del archivo y reglas: docs/CARGA_DE_EVALUACIONES.md.
Este script nunca inventa claves, pesos ni baremos: carga solo lo que
el archivo contiene.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.exceptions.base import AppException  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.services.cargador_prueba_service import (  # noqa: E402
    CargadorPruebaService,
    validar_definicion,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Carga una evaluación desde un JSON.")
    parser.add_argument("archivo", type=Path, help="Ruta del archivo JSON de la evaluación.")
    parser.add_argument("--validar", action="store_true",
                        help="Solo valida el archivo; no escribe en la base de datos.")
    parser.add_argument("--version-nueva", action="store_true",
                        help="Si la evaluación ya existe, cargar el contenido como una nueva versión.")
    args = parser.parse_args()

    try:
        definicion = json.loads(args.archivo.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"No existe el archivo: {args.archivo}")
        return 2
    except json.JSONDecodeError as exc:
        print(f"El archivo no es un JSON válido: {exc}")
        return 2

    errores = validar_definicion(definicion)
    if errores:
        print("La definición tiene problemas:")
        for e in errores:
            print(f"  - {e}")
        return 1

    n_preguntas = len(definicion["preguntas"])
    n_opciones = sum(len(p.get("opciones", [])) for p in definicion["preguntas"])
    print(f"Definición válida: {definicion['prueba']['nombre']} — "
          f"{n_preguntas} preguntas, {n_opciones} opciones.")
    if args.validar:
        return 0

    db = SessionLocal()
    try:
        resumen = CargadorPruebaService(db).cargar(definicion, version_nueva=args.version_nueva)
    except AppException as exc:
        print(f"No se cargó nada: {exc.detail}")
        return 1
    finally:
        db.close()

    print(f"Listo: '{resumen.prueba_codigo}' versión {resumen.numero_version} "
          f"({'evaluación nueva' if resumen.prueba_creada else 'evaluación existente'}) — "
          f"{resumen.total_preguntas} preguntas, {resumen.total_opciones} opciones"
          f"{', algoritmo creado' if resumen.algoritmo_creado else ''}.")
    for aviso in resumen.avisos:
        print(f"  * {aviso}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
