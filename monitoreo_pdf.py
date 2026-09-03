"""Reporte PDF de dispositivos caidos (por debajo de la meta de SLA), en el
mismo estilo del reporte ejecutivo de Analisis-Python.1-v3.0-BETA pero como
una tabla simple, sin graficos."""

from datetime import datetime
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from monitoreo_schema import COLUMNAS, SLA_OBJETIVO

BRAND_NAVY = "#0f172a"
BRAND_BLUE = "#2563eb"
BRAND_SLATE = "#64748b"
BRAND_BORDER = "#e2e8f0"
BRAND_SURFACE = "#f1f5f9"
STATUS_RED = "#dc2626"
STATUS_SLATE = "#64748b"


def _footer(canvas, document):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor(BRAND_BORDER))
    canvas.setLineWidth(0.6)
    canvas.line(0.35 * inch, 0.42 * inch, landscape(letter)[0] - 0.35 * inch, 0.42 * inch)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor(BRAND_SLATE))
    canvas.drawString(
        0.35 * inch, 0.26 * inch,
        f"Generado {datetime.now():%d/%m/%Y %H:%M} · Monitoreo de disponibilidad · Documento de uso interno",
    )
    canvas.drawRightString(landscape(letter)[0] - 0.35 * inch, 0.26 * inch, f"Pagina {document.page}")
    canvas.restoreState()


def build_pdf_dispositivos_caidos(
    caidos: dict, periodo: str, umbral: float = SLA_OBJETIVO
) -> bytes:
    """`caidos` es el resultado de `monitoreo_io.dispositivos_caidos()`:
    {'total': [...], 'ajustado': [...], 'excluidos': [...]}."""
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer, pagesize=landscape(letter), rightMargin=0.35 * inch,
        leftMargin=0.35 * inch, topMargin=0.3 * inch, bottomMargin=0.55 * inch,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "Title", parent=styles["Title"], fontName="Helvetica-Bold",
        fontSize=22, textColor=colors.white, leading=27,
    )
    subtitle_style = ParagraphStyle(
        "Subtitle", parent=styles["Normal"], fontSize=11, textColor=colors.HexColor(BRAND_SLATE)
    )
    body_style = ParagraphStyle("Body", parent=styles["Normal"], fontSize=9, leading=11)

    story = []
    header = Table(
        [[Paragraph("Dispositivos por debajo de la meta de SLA", title_style)],
         [Paragraph(f"Monitoreo de disponibilidad · {periodo} · Meta: {umbral:.0f}% o superior", subtitle_style)]],
        colWidths=[10.3 * inch],
    )
    header.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(BRAND_NAVY)),
        ("LEFTPADDING", (0, 0), (-1, -1), 16), ("RIGHTPADDING", (0, 0), (-1, -1), 16),
        ("TOPPADDING", (0, 0), (-1, 0), 13), ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("TOPPADDING", (0, 1), (-1, 1), 7), ("BOTTOMPADDING", (0, 1), (-1, 1), 12),
    ]))
    accent = Table([[""]], colWidths=[10.3 * inch], rowHeights=[0.06 * inch])
    accent.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(BRAND_BLUE))]))
    story.extend([header, accent, Spacer(1, 0.16 * inch)])

    total = caidos["total"]
    ajustado = caidos["ajustado"]
    excluidos = caidos["excluidos"]
    summary = [
        ["Caidos (total)", "Caidos (ajustado, excluye no controlados)", "Excluidos por causa externa"],
        [str(len(total)), str(len(ajustado)), str(len(excluidos))],
    ]
    summary_table = Table(summary, colWidths=[3.43 * inch] * 3, rowHeights=[0.42 * inch, 0.55 * inch])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(BRAND_SURFACE)),
        ("GRID", (0, 0), (-1, -1), 0.7, colors.HexColor(BRAND_BORDER)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor(BRAND_SLATE)),
        ("TEXTCOLOR", (0, 1), (-1, 1), colors.HexColor(BRAND_BLUE)),
        ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10), ("FONTSIZE", (0, 1), (-1, 1), 17),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.extend([summary_table, Spacer(1, 0.18 * inch)])

    def _tabla_dispositivos(titulo: str, lista: list[dict]) -> list:
        elementos = [Paragraph(titulo, ParagraphStyle(
            "H2", parent=styles["Heading2"], fontName="Helvetica-Bold",
            fontSize=13, textColor=colors.HexColor(BRAND_NAVY), spaceBefore=6, spaceAfter=6,
        ))]
        if not lista:
            elementos.append(Paragraph("Ninguno.", body_style))
            return elementos
        data = [["Categoria", "HOST_NAME", "% Up", "% Down", "Causa", "No controlado"]]
        for d in sorted(lista, key=lambda d: d.get(COLUMNAS["percent_up"], 0)):
            data.append([
                Paragraph(str(d.get(COLUMNAS["categoria"], "")), body_style),
                Paragraph(str(d.get(COLUMNAS["host_name"], "")), body_style),
                f"{d.get(COLUMNAS['percent_up'], 0):.2f}%",
                f"{d.get(COLUMNAS['percent_down'], 0):.2f}%",
                Paragraph(str(d.get(COLUMNAS["causa"], "") or "-"), body_style),
                str(d.get(COLUMNAS["no_controlado"], "NO")),
            ])
        tabla = Table(data, colWidths=[1.7 * inch, 2.3 * inch, 0.9 * inch, 0.9 * inch, 3.4 * inch, 1.1 * inch])
        tabla.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(BRAND_SURFACE)),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor(BRAND_NAVY)),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor(BRAND_BORDER)),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor(BRAND_SURFACE)]),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        elementos.append(tabla)
        return elementos

    story.extend(_tabla_dispositivos("Dispositivos caidos (cuentan contra el SLA)", ajustado))
    story.append(Spacer(1, 0.14 * inch))
    story.extend(_tabla_dispositivos("Excluidos del SLA (causa externa: electrica, proveedor, etc.)", excluidos))

    document.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()
