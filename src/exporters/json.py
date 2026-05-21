import json as json_lib

from .base import Exporter
from ..models import TranscriptionResult


def result_to_dict(result: TranscriptionResult) -> dict:
    return {
        "id": result.id,
        "filename": result.audio_file.path.name,
        "duration_seconds": result.duration_seconds,
        "language": result.language,
        "confidence": round(result.confidence, 4),
        "text": result.text,
        "words": [
            {"text": w.text, "start": w.start, "end": w.end, "confidence": w.confidence}
            for w in result.words
        ],
        "utterances": [
            {"speaker": u.speaker, "text": u.text, "start": u.start, "end": u.end}
            for u in result.utterances
        ],
        "status": result.status.value,
        "error": result.error,
    }


class JsonExporter(Exporter):
    extension = "json"

    def render_individual(self, result: TranscriptionResult) -> str:
        return json_lib.dumps(result_to_dict(result), ensure_ascii=False, indent=2)

    def render_full(self, results: list[TranscriptionResult]) -> str:
        return json_lib.dumps(
            [result_to_dict(r) for r in results],
            ensure_ascii=False,
            indent=2,
        )
