from __future__ import annotations

from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from ..models import Evidence, Tag


def export_case_pdf() -> bytes:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    y = 800
    pdf.setFont('Helvetica-Bold', 16)
    pdf.drawString(40, y, 'Forensisch Dossier Rapport')
    y -= 25
    pdf.setFont('Helvetica', 10)

    for evidence in Evidence.query.order_by(Evidence.created_at.asc()).all():
        tags = [t.label for t in Tag.query.filter_by(evidence_id=evidence.evidence_id).all()]
        line = (
            f'{evidence.evidence_id} | {evidence.filename} | {evidence.created_at:%Y-%m-%d} '
            f'| relevantie={evidence.legal_relevance} | sterkte={evidence.evidence_strength}'
        )
        pdf.drawString(40, y, line[:120])
        y -= 12
        pdf.drawString(40, y, f'Tags: {", ".join(tags) if tags else "-"}')
        y -= 14
        if y < 90:
            pdf.showPage()
            pdf.setFont('Helvetica', 10)
            y = 800

    pdf.showPage()
    pdf.save()
    return buffer.getvalue()
