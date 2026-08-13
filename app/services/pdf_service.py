import os
import re
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    HRFlowable,
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def clean_markdown(text: str) -> str:
    """Removes basic markdown formatting characters for clean PDF display."""
    if not text:
        return ""
    text = re.sub(r"[#*`_~]", "", text)
    lines = [line.strip("- ").strip() for line in text.splitlines() if line.strip()]
    return "<br/>".join(f"• {line}" for line in lines)


def generate_turno_planilla_pdf(
    turno_id: str,
    ciudadano_nombre: str,
    ciudadano_dni: str,
    tramite_nombre: str,
    area_nombre: str,
    variantes_info: str,
    fecha_hora_inicio: str,
    fecha_hora_fin: str,
    documentacion_requerida: str,
    requerimientos_previos: str = "",
) -> bytes:
    """Compiles a PDF binary buffer for a appointment receipt ('Planilla de Turno')."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()

    header_subtitle_style = ParagraphStyle(
        "HeaderSubtitleWhite",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        textColor=colors.HexColor("#FFF8F0"),
        alignment=1,
    )
    section_heading = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        textColor=colors.HexColor("#FE8F00"),
        spaceBefore=10,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "BodyTextCustom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        textColor=colors.HexColor("#333333"),
        leading=14,
    )
    bold_label = ParagraphStyle(
        "BoldLabel",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        textColor=colors.HexColor("#333333"),
    )
    header_subtitle_style = ParagraphStyle(
        "HeaderSubtitleRight",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        textColor=colors.HexColor("#FFFFFF"),
        alignment=2,  # Alineado a la derecha
    )

    elements = []

    # Logo & Header Banner Section (Fondo Naranja Municipal #FE8F00 - 2 Columnas)
    logo_path = os.path.join(os.path.dirname(__file__), "..", "assets", "logo-muni.png")
    if not os.path.exists(logo_path):
        logo_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "turnero", "public", "images", "logo-muni.png")

    left_cell = []
    if os.path.exists(logo_path):
        try:
            logo_img = Image(logo_path, width=170, height=50)
            logo_img.hAlign = "LEFT"
            left_cell.append(logo_img)
        except Exception:
            pass

    right_cell = [
        Paragraph("Comprobante Oficial de Reserva de Turno", header_subtitle_style)
    ]

    header_table = Table([[left_cell, right_cell]], colWidths=[240, 290])
    header_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FE8F00")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                ("LEFTPADDING", (0, 0), (-1, -1), 16),
                ("RIGHTPADDING", (0, 0), (-1, -1), 16),
            ]
        )
    )
    elements.append(header_table)
    elements.append(Spacer(1, 15))



    # Turno & Citizen Data Table
    table_data = [
        [
            Paragraph("Código de Turno:", bold_label),
            Paragraph(f"<b>{turno_id}</b>", body_style),
        ],
        [
            Paragraph("Ciudadano / Titular:", bold_label),
            Paragraph(ciudadano_nombre, body_style),
        ],
        [
            Paragraph("DNI:", bold_label),
            Paragraph(ciudadano_dni, body_style),
        ],
        [
            Paragraph("Área Municipal:", bold_label),
            Paragraph(area_nombre, body_style),
        ],
        [
            Paragraph("Trámite:", bold_label),
            Paragraph(tramite_nombre, body_style),
        ],
        [
            Paragraph("Variantes / Detalle:", bold_label),
            Paragraph(variantes_info or "Atención General", body_style),
        ],
        [
            Paragraph("Fecha y Horario:", bold_label),
            Paragraph(f"<b>{fecha_hora_inicio} hs</b> (hasta {fecha_hora_fin} hs)", body_style),
        ],
    ]

    t = Table(table_data, colWidths=[140, 390])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F0F2F5")),
                ("PADDING", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E0E0E0")),
            ]
        )
    )
    elements.append(t)
    elements.append(Spacer(1, 15))

    # Requisitos & Documentación
    elements.append(Paragraph("Documentación Requerida a Presentar", section_heading))
    clean_doc = clean_markdown(documentacion_requerida) or "• Documento Nacional de Identidad (DNI) original."
    elements.append(Paragraph(clean_doc, body_style))
    elements.append(Spacer(1, 10))

    if requerimientos_previos:
        elements.append(Paragraph("Requerimientos y Pasos Previos", section_heading))
        clean_req = clean_markdown(requerimientos_previos)
        elements.append(Paragraph(clean_req, body_style))
        elements.append(Spacer(1, 10))

    # Footer note
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#CCCCCC"), spaceBefore=15, spaceAfter=10))
    footer_style = ParagraphStyle(
        "FooterNote",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=9,
        textColor=colors.HexColor("#666666"),
        alignment=1,
    )
    elements.append(
        Paragraph(
            "Por favor, recuerde asistir con 5 minutos de antelación y presentar este comprobante "
            "digital o impreso junto a su Documento Nacional de Identidad.",
            footer_style,
        )
    )

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
