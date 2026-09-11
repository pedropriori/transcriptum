from pathlib import Path
import pytest
from src.models import AudioFile, TranscriptionResult, TranscriptionStatus, WordTimestamp, Utterance


def make_audio_file(tmp_path: Path, name: str = "test.ogg", index: int = 1) -> AudioFile:
    f = tmp_path / name
    f.write_bytes(b"")
    return AudioFile(path=f, index=index)


def test_audio_file_safe_name(tmp_path):
    af = make_audio_file(tmp_path, "WhatsApp Audio 2026-05-21 at 11.14.53 (1).ogg")
    assert af.safe_name == "WhatsApp-Audio-2026-05-21-at-11.14.53-1"


def test_audio_file_safe_name_no_parens(tmp_path):
    af = make_audio_file(tmp_path, "WhatsApp Audio 2026-05-21 at 11.14.53.ogg")
    assert af.safe_name == "WhatsApp-Audio-2026-05-21-at-11.14.53"


def test_transcription_result_id(tmp_path):
    af = make_audio_file(tmp_path, index=3)
    result = TranscriptionResult(
        audio_file=af,
        status=TranscriptionStatus.COMPLETED,
        text="hello",
    )
    assert result.id == "03"


def test_transcription_result_duration_str(tmp_path):
    af = make_audio_file(tmp_path)
    result = TranscriptionResult(
        audio_file=af,
        status=TranscriptionStatus.COMPLETED,
        duration_seconds=95,
    )
    assert result.duration_str == "1:35"


def test_transcription_result_confidence_pct(tmp_path):
    af = make_audio_file(tmp_path)
    result = TranscriptionResult(
        audio_file=af,
        status=TranscriptionStatus.COMPLETED,
        confidence=0.963,
    )
    assert result.confidence_pct == "96%"


def test_transcription_result_defaults(tmp_path):
    af = make_audio_file(tmp_path)
    result = TranscriptionResult(audio_file=af, status=TranscriptionStatus.FAILED)
    assert result.text == ""
    assert result.words == []
    assert result.utterances == []
    assert result.error is None


def test_diarized_lines_empty_without_utterances(tmp_path):
    af = make_audio_file(tmp_path)
    result = TranscriptionResult(audio_file=af, status=TranscriptionStatus.COMPLETED, text="oi")
    assert result.diarized_lines == []


def test_diarized_lines_formats_speaker_and_timestamp(tmp_path):
    af = make_audio_file(tmp_path)
    result = TranscriptionResult(
        audio_file=af,
        status=TranscriptionStatus.COMPLETED,
        utterances=[
            Utterance(speaker="A", text="Fala, tudo bem?", start=34000, end=36000),
            Utterance(speaker="B", text="Tudo, e você?", start=52000, end=54000),
        ],
    )
    assert result.diarized_lines == [
        "[00:34] Speaker A: Fala, tudo bem?",
        "[00:52] Speaker B: Tudo, e você?",
    ]
