from datetime import datetime

from fpdf import FPDF

from .base import Exporter
from ..models import TranscriptionResult, TranscriptionStatus


class PdfExporter(Exporter):
    extension = "pdf"

    def _new_pdf(self) -> FPDF:
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        return pdf

    def render_individual(self, result: TranscriptionResult) -> bytes:
        pdf = self._new_pdf()

        pdf.set_font("Helvetica", "B", 14)
        pdf.multi_cell(0, 10, result.audio_file.path.name, new_x="LMARGIN", new_y="NEXT")

        pdf.set_font("Helvetica", "I", 10)
        pdf.multi_cell(
            0, 8,
            f"Duracao: {result.duration_str}  |  Idioma: {result.language}  |  Confianca: {result.confidence_pct}",
            new_x="LMARGIN", new_y="NEXT",
        )
        pdf.ln(4)

        pdf.set_font("Helvetica", "", 11)
        body = (
            "\n\n".join(self._body_lines(result))
            if result.status == TranscriptionStatus.COMPLETED
            else f"[FALHOU: {result.error}]"
        )
        pdf.multi_cell(0, 8, body, new_x="LMARGIN", new_y="NEXT")

        return bytes(pdf.output())

    def render_full(self, results: list[TranscriptionResult]) -> bytes:
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        folder = results[0].audio_file.path.parent.name if results else "-"
        lang = results[0].language if results else "-"

        pdf = self._new_pdf()

        pdf.set_font("Helvetica", "B", 16)
        pdf.multi_cell(0, 12, f"Transcricao - {folder}", new_x="LMARGIN", new_y="NEXT")

        pdf.set_font("Helvetica", "I", 10)
        pdf.multi_cell(0, 8, f"Gerado em {now}  |  {len(results)} audios  |  Idioma: {lang}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(6)

        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(0, 10, "Indice", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        for r in results:
            pdf.cell(
                0, 7,
                f"{r.id}. {r.audio_file.path.name} ({r.duration_str})",
                new_x="LMARGIN", new_y="NEXT",
            )

        pdf.add_page()

        for r in results:
            pdf.set_font("Helvetica", "B", 12)
            pdf.multi_cell(0, 9, f"{r.id} - {r.audio_file.path.name}", new_x="LMARGIN", new_y="NEXT")

            pdf.set_font("Helvetica", "I", 10)
            pdf.multi_cell(0, 7, f"Duracao: {r.duration_str}", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)

            pdf.set_font("Helvetica", "", 11)
            body = (
                "\n\n".join(self._body_lines(r))
                if r.status == TranscriptionStatus.COMPLETED
                else f"[FALHOU: {r.error}]"
            )
            pdf.multi_cell(0, 8, body, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(4)
            pdf.set_draw_color(180, 180, 180)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(4)

        return bytes(pdf.output())
