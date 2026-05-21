from pathlib import Path
from typing import Callable

import assemblyai as aai

from .config import AppConfig
from .models import (
    AudioFile,
    TranscriptionResult,
    TranscriptionStatus,
    WordTimestamp,
    Utterance,
)


def collect_audio_files(input_dir: Path) -> list[AudioFile]:
    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")

    files = sorted(
        f for f in input_dir.iterdir()
        if f.is_file() and f.suffix.lower() == ".ogg"
    )

    if not files:
        raise ValueError(f"No .ogg files found in {input_dir}")

    return [AudioFile(path=f, index=i + 1) for i, f in enumerate(files)]


def _build_aai_config(config: AppConfig) -> aai.TranscriptionConfig:
    return aai.TranscriptionConfig(
        language_code=config.language if config.language != "auto" else None,
        language_detection=config.language == "auto",
        speaker_labels=config.extras.speaker_diarization,
        punctuate=True,
        format_text=True,
    )


def _map_transcript(
    transcript: aai.Transcript, audio_file: AudioFile
) -> TranscriptionResult:
    if transcript.status == aai.TranscriptStatus.error:
        return TranscriptionResult(
            audio_file=audio_file,
            status=TranscriptionStatus.FAILED,
            error=getattr(transcript, "error", "Unknown error"),
        )

    words = [
        WordTimestamp(
            text=w.text, start=w.start, end=w.end, confidence=w.confidence
        )
        for w in (transcript.words or [])
    ]
    utterances = [
        Utterance(speaker=u.speaker, text=u.text, start=u.start, end=u.end)
        for u in (transcript.utterances or [])
    ]

    raw = transcript.json_response or {}
    return TranscriptionResult(
        audio_file=audio_file,
        status=TranscriptionStatus.COMPLETED,
        text=transcript.text or "",
        language=raw.get("language_code") or "",
        confidence=transcript.confidence or 0.0,
        duration_seconds=int(transcript.audio_duration or 0),
        words=words,
        utterances=utterances,
    )


def transcribe_batch(
    audio_files: list[AudioFile],
    config: AppConfig,
    on_result: Callable[[TranscriptionResult], None] | None = None,
) -> list[TranscriptionResult]:
    aai.settings.api_key = config.api_key

    transcription_config = _build_aai_config(config)
    transcriber = aai.Transcriber(config=transcription_config)
    file_paths = [str(af.path) for af in audio_files]

    transcript_group = transcriber.transcribe_group(file_paths)

    results: list[TranscriptionResult] = []
    for audio_file, transcript in zip(audio_files, transcript_group):
        result = _map_transcript(transcript, audio_file)
        results.append(result)
        if on_result:
            on_result(result)

    return results
