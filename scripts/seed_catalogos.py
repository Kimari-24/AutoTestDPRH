#!/usr/bin/env python3
"""
Datos semilla de catálogos básicos.

Estos catálogos son configuración genérica del sistema (listas de
valores), no contenido psicométrico: no incluyen preguntas, claves,
baremos ni algoritmos de ninguna prueba.

- sexo, escolaridad: catálogos demográficos estándar usados en el
  expediente del evaluado (sección 16 de los requisitos).
- estatus_candidato: activo / inactivo, en línea con la bandera
  `activo` del propio evaluado.
- estatus_prueba: los 6 estados fijados explícitamente en la
  sección 7 de los requisitos (PENDIENTE, EN_PROCESO, COMPLETADA,
  CALIFICADA, CANCELADA, EXPIRADA).
- tipo_pregunta: los 9 tipos de pregunta que el motor debe soportar
  como mínimo, según la sección 5 de los requisitos (opción única,
  opción múltiple, verdadero/falso, escala, asociación, ordenamiento,
  imagen, texto, estímulo visual).

Uso (desde la raíz del proyecto):

    python3 scripts/seed_catalogos.py
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "backend"))

from app.db.session import SessionLocal  # noqa: E402
from app.models.catalogos import (  # noqa: E402
    CatalogoBase,
    Escolaridad,
    EstatusCandidato,
    EstatusPrueba,
    Sexo,
    TipoPregunta,
)

CATALOGOS: dict[type[CatalogoBase], list[tuple[str, str]]] = {
    Sexo: [
        ("MASCULINO", "Masculino"),
        ("FEMENINO", "Femenino"),
    ],
    Escolaridad: [
        ("PRIMARIA", "Primaria"),
        ("SECUNDARIA", "Secundaria"),
        ("PREPARATORIA", "Preparatoria / Bachillerato"),
        ("LICENCIATURA", "Licenciatura"),
        ("MAESTRIA", "Maestría"),
        ("DOCTORADO", "Doctorado"),
    ],
    EstatusCandidato: [
        ("ACTIVO", "Activo"),
        ("INACTIVO", "Inactivo"),
    ],
    EstatusPrueba: [
        ("PENDIENTE", "Pendiente"),
        ("EN_PROCESO", "En proceso"),
        ("COMPLETADA", "Completada"),
        ("CALIFICADA", "Calificada"),
        ("CANCELADA", "Cancelada"),
        ("EXPIRADA", "Expirada"),
    ],
    TipoPregunta: [
        ("OPCION_UNICA", "Opción única"),
        ("OPCION_MULTIPLE", "Opción múltiple"),
        ("VERDADERO_FALSO", "Verdadero / Falso"),
        ("ESCALA", "Escala"),
        ("ASOCIACION", "Asociación"),
        ("ORDENAMIENTO", "Ordenamiento"),
        ("IMAGEN", "Pregunta con imagen"),
        ("TEXTO", "Pregunta basada en texto"),
        ("ESTIMULO_VISUAL", "Pregunta con estímulo visual"),
    ],
}


def main() -> None:
    db = SessionLocal()
    try:
        for modelo, valores in CATALOGOS.items():
            print(f"Sembrando {modelo.__tablename__}...")
            for codigo, nombre in valores:
                existente = (
                    db.query(modelo).filter(modelo.codigo == codigo).one_or_none()
                )
                if existente is None:
                    db.add(modelo(codigo=codigo, nombre=nombre, activo=True))
                    print(f"  + {codigo}")
                else:
                    print(f"  = {codigo} ya existía")
        db.commit()
        print("\nListo.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
