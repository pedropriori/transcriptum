from datetime import datetime

from .base import Exporter
from ..models import TranscriptionResult, TranscriptionStatus


class TxtExporter(Exporter):
    extension = "txt"

    def render_individual(self, result: TranscriptionResult) -> str:
        body = (
            "\n\n".join(self._body_lines(result))
            if result.status == TranscriptionStatus.COMPLETED
            else f"[FALHOU: {result.error}]"
        )
        return "\n".join([
            result.audio_file.path.name,
            f"Duração: {result.duration_str} | Idioma: {result.language} | Confiança: {result.confidence_pct}",
            "",
            body,
        ])

    def render_full(self, results: list[TranscriptionResult]) -> str:
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        folder = results[0].audio_file.path.parent.name if results else "—"
        sep = "═" * 51

        index_lines = [f"  {r.id}. {r.audio_file.path.name} ({r.duration_str})" for r in results]

        header = [
            f"TRANSCRIÇÃO — {folder}",
            f"Gerado em {now} · {len(results)} áudios",
            sep,
            "",
            "ÍNDICE",
            *index_lines,
            "",
            sep,
        ]

        sections: list[str] = []
        for r in results:
            body = (
                "\n\n".join(self._body_lines(r))
                if r.status == TranscriptionStatus.COMPLETED
                else f"[FALHOU: {r.error}]"
            )
            sections += [
                "",
                f"[{r.id}] {r.audio_file.path.name}",
                f"Duração: {r.duration_str}",
                "",
                body,
                "",
                "─" * 51,
            ]

        return "\n".join(header + sections)
