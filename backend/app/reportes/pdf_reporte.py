"""
Generador de reportes PDF (sección 21 de los requisitos).

Recibe únicamente datos ya calculados por el motor universal (Fase 6)
y configurados por DPRH en el catálogo de pruebas (Fase 5): nombres,
puntuaciones, interpretaciones de escalas/reglas. Este módulo NO
redacta interpretaciones psicométricas ni conclusiones propias —
solo compone y da formato a lo que ya existe en la base de datos.

Recibe diccionarios simples (no objetos ORM ni sesiones de base de
datos), para mantenerlo como una capa de presentación pura, fácil de
probar de forma aislada.
"""

from __future__ import annotations

import io
from datetime import datetime
from typing import Any

import matplotlib

matplotlib.use("Agg")  # backend sin interfaz gráfica, para renderizar en el servidor
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

COLOR_GUINDA = colors.HexColor("#6d1b3a")
COLOR_GRIS = colors.HexColor("#e8e6e2")


def _grafica_de_factores(factores: list[dict[str, Any]]) -> io.BytesIO | None:
    """Gráfica de barras con la puntuación de cada factor. Devuelve
    None si no hay factores que graficar (evita una imagen vacía)."""
    factores_con_puntuacion = [f for f in factores if f.get("puntuacion") is not None]
    if not factores_con_puntuacion:
        return None

    nombres = [f["nombre"] for f in factores_con_puntuacion]
    valores = [f["puntuacion"] for f in factores_con_puntuacion]

    figura, eje = plt.subplots(figsize=(6.5, 3), dpi=150)
    eje.bar(nombres, valores, color="#6d1b3a")
    eje.set_ylabel("Puntuación")
    eje.spines["top"].set_visible(False)
    eje.spines["right"].set_visible(False)
    plt.xticks(rotation=15, ha="right", fontsize=8)
    plt.tight_layout()

    buffer = io.BytesIO()
    figura.savefig(buffer, format="png")
    plt.close(figura)
    buffer.seek(0)
    return buffer


def _tabla(encabezados: list[str], filas: list[list[str]], anchos: list[float]) -> Table:
    datos = [encabezados] + filas
    tabla = Table(datos, colWidths=anchos, repeatRows=1)
    tabla.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), COLOR_GUINDA),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLOR_GRIS]),
                ("GRID", (0, 0), (-1, -1), 0.5, COLOR_GRIS),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return tabla


def generar_pdf_resultado(datos: dict[str, Any]) -> bytes:
    """Genera el PDF del reporte de resultados de una sesión.

    `datos` (todo ya calculado/configurado, nada se inventa aquí):
        candidato: {nombre, apellidos, correo, puesto}
        empresa: {nombre_comercial} | None
        prueba: {nombre, categoria}
        resultado: {calculado_en, puntuacion_global, puntuacion_normalizada, interpretacion_global}
        factores: [{nombre, codigo, puntuacion, interpretacion}]
        escalas: [{nombre, codigo, valor, interpretacion}]
    """
    estilos = getSampleStyleSheet()
    estilo_titulo = ParagraphStyle(
        "TituloReporte", parent=estilos["Title"], textColor=COLOR_GUINDA, fontSize=18
    )
    estilo_seccion = ParagraphStyle(
        "Seccion", parent=estilos["Heading2"], textColor=COLOR_GUINDA, spaceBefore=14
    )
    estilo_normal = estilos["Normal"]
    estilo_nota = ParagraphStyle(
        "Nota", parent=estilos["Normal"], fontSize=8, textColor=colors.grey, spaceBefore=16
    )

    story: list[Any] = []

    story.append(Paragraph("AutoTest DPRH — Reporte de resultados", estilo_titulo))
    story.append(Spacer(1, 4))
    story.append(
        Paragraph(
            f"Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            estilo_nota,
        )
    )
    story.append(Spacer(1, 12))

    candidato = datos["candidato"]
    empresa = datos.get("empresa")
    prueba = datos["prueba"]

    story.append(Paragraph("Datos generales", estilo_seccion))
    filas_generales = [
        ["Evaluado", f"{candidato['nombre']} {candidato['apellidos']}"],
        ["Correo", candidato.get("correo") or "—"],
        ["Puesto", candidato.get("puesto") or "—"],
        ["Empresa", empresa["nombre_comercial"] if empresa else "—"],
        ["Evaluación", prueba["nombre"]],
        ["Categoría", prueba.get("categoria") or "—"],
    ]
    story.append(
        _tabla(["Campo", "Valor"], filas_generales, anchos=[4 * cm, 11 * cm])
    )

    resultado = datos["resultado"]
    story.append(Paragraph("Resultado global", estilo_seccion))
    filas_resultado = [
        ["Puntuación global", _formatear_numero(resultado.get("puntuacion_global"))],
        ["Puntuación normalizada", _formatear_numero(resultado.get("puntuacion_normalizada"))],
        ["Calculado el", resultado["calculado_en"].strftime("%d/%m/%Y %H:%M")],
    ]
    story.append(_tabla(["Campo", "Valor"], filas_resultado, anchos=[4 * cm, 11 * cm]))
    if resultado.get("interpretacion_global"):
        story.append(Spacer(1, 6))
        story.append(Paragraph(resultado["interpretacion_global"], estilo_normal))

    factores = datos.get("factores", [])
    if factores:
        story.append(Paragraph("Resultados por factor", estilo_seccion))
        grafica = _grafica_de_factores(factores)
        if grafica is not None:
            story.append(Image(grafica, width=15 * cm, height=15 * cm * 3 / 6.5))
            story.append(Spacer(1, 8))
        story.append(
            _tabla(
                ["Factor", "Puntuación", "Interpretación"],
                [
                    [f["nombre"], _formatear_numero(f.get("puntuacion")), f.get("interpretacion") or "—"]
                    for f in factores
                ],
                anchos=[4 * cm, 3 * cm, 8 * cm],
            )
        )

    escalas = datos.get("escalas", [])
    if escalas:
        story.append(Paragraph("Escalas alcanzadas", estilo_seccion))
        story.append(
            _tabla(
                ["Escala", "Valor", "Interpretación"],
                [
                    [e["nombre"], _formatear_numero(e.get("valor")), e.get("interpretacion") or "—"]
                    for e in escalas
                ],
                anchos=[4 * cm, 3 * cm, 8 * cm],
            )
        )

    story.append(
        Paragraph(
            "Este reporte se generó automáticamente a partir de la configuración del "
            "algoritmo, los factores y las escalas definidos para esta evaluación. "
            "No incluye ninguna interpretación adicional a la configurada por DPRH.",
            estilo_nota,
        )
    )

    buffer = io.BytesIO()
    documento = SimpleDocTemplate(
        buffer, pagesize=letter, topMargin=2 * cm, bottomMargin=2 * cm,
        leftMargin=2 * cm, rightMargin=2 * cm,
    )
    documento.build(story)
    return buffer.getvalue()


def _formatear_numero(valor: float | None) -> str:
    if valor is None:
        return "—"
    if float(valor).is_integer():
        return str(int(valor))
    return f"{valor:.2f}"
