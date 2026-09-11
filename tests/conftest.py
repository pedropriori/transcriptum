from pathlib import Path
import pytest
from src.models import AudioFile, TranscriptionResult, TranscriptionStatus, Utterance


def _make_result(tmp_path: Path, name: str, index: int, text: str) -> TranscriptionResult:
    f = tmp_path / name
    f.write_bytes(b"")
    return TranscriptionResult(
        audio_file=AudioFile(path=f, index=index),
        status=TranscriptionStatus.COMPLETED,
        text=text,
        language="pt",
        confidence=0.96,
        duration_seconds=28,
    )


@pytest.fixture
def one_result(tmp_path):
    return _make_result(
        tmp_path,
        "WhatsApp Audio 2026-05-21 at 11.14.53.ogg",
        index=1,
        text="Olá, como vai você?",
    )


@pytest.fixture
def diarized_result(tmp_path):
    f = tmp_path / "meeting.wav"
    f.write_bytes(b"")
    return TranscriptionResult(
        audio_file=AudioFile(path=f, index=1),
        status=TranscriptionStatus.COMPLETED,
        text="Fala, tudo bem? Tudo, e você?",
        language="pt",
        confidence=0.97,
        duration_seconds=58,
        utterances=[
            Utterance(speaker="A", text="Fala, tudo bem?", start=0, end=2000),
            Utterance(speaker="B", text="Tudo, e você?", start=2000, end=4000),
        ],
    )


@pytest.fixture
def two_results(tmp_path):
    return [
        _make_result(
            tmp_path,
            "WhatsApp Audio 2026-05-21 at 11.14.53.ogg",
            index=1,
            text="Primeiro áudio.",
        ),
        _make_result(
            tmp_path,
            "WhatsApp Audio 2026-05-21 at 11.14.54.ogg",
            index=2,
            text="Segundo áudio.",
        ),
    ]
