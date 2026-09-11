from datetime import datetime

from .base import Exporter
from ..models import TranscriptionResult, TranscriptionStatus


class MarkdownExporter(Exporter):
    extension = "md"

    def render_individual(self, result: TranscriptionResult) -> str:
        body = (
            "\n\n".join(self._body_lines(result))
            if result.status == TranscriptionStatus.COMPLETED
            else f"**[FALHOU: {result.error}]**"
        )
        return "\n".join([
            f"# {result.audio_file.path.name}",
            f"> Duração: {result.duration_str} | Idioma: {result.language} | Confiança: {result.confidence_pct}",
            "",
            body,
        ])

    def render_full(self, results: list[TranscriptionResult]) -> str:
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        folder = results[0].audio_file.path.parent.name if results else "—"
        lang = results[0].language if results else "—"

        lines: list[str] = [
            f"# Transcrição — {folder}",
            f"> Gerado em {now} · {len(results)} áudios · Idioma: {lang}",
            "",
            "---",
            "",
            "## Índice",
            "",
            "| # | Arquivo | Duração | Confiança |",
            "|---|---------|---------|-----------|",
        ]

        for r in results:
            lines.append(
                f"| {r.id} | {r.audio_file.path.name} | {r.duration_str} | {r.confidence_pct} |"
            )

        lines += ["", "---", ""]

        for r in results:
            body = (
                "\n\n".join(self._body_lines(r))
                if r.status == TranscriptionStatus.COMPLETED
                else f"**[FALHOU: {r.error}]**"
            )
            lines += [
                f"## {r.id} · {r.audio_file.path.name}",
                "",
                f"> Duração: {r.duration_str}",
                "",
                body,
                "",
                "---",
                "",
            ]

        return "\n".join(lines)
