import shutil
import subprocess
import tempfile
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

# Models tried in order (per-request fallback list, not parallel execution) --
# universal-3-5-pro is the current flagship, universal-2 is the broadly-available
# fallback it drops to for anything outside its native language set. Set
# explicitly: the AssemblyAI API defaults to an older pair when this is omitted.
SPEECH_MODELS = ["universal-3-5-pro", "universal-2"]

# Video containers: audio is extracted locally via ffmpeg before upload (smaller,
# faster, and avoids depending on the API accepting the container directly).
# Anything else (.ogg, .wav, .mp3, .m4a, ...) is sent to AssemblyAI as-is.
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".mov", ".webm", ".avi", ".m4v"}


def collect_audio_files(input_path: Path) -> list[AudioFile]:
    if not input_path.exists():
        raise FileNotFoundError(f"Input path not found: {input_path}")

    if input_path.is_file():
        return [_prepare_single_file(input_path)]

    files = sorted(
        f for f in input_path.iterdir()
        if f.is_file() and f.suffix.lower() == ".ogg"
    )

    if not files:
        raise ValueError(f"No .ogg files found in {input_path}")

    return [AudioFile(path=f, index=i + 1) for i, f in enumerate(files)]


def _prepare_single_file(path: Path) -> AudioFile:
    """A single audio/video file passed directly as input -- e.g. a recorded meeting or call, as opposed to a batch folder of WhatsApp .ogg notes."""
    if path.suffix.lower() in VIDEO_EXTENSIONS:
        path = extract_audio(path)
    return AudioFile(path=path, index=1)


def extract_audio(video_path: Path) -> Path:
    """Extracts a mono 16kHz WAV track from a video file via ffmpeg, for upload instead of the full video container."""
    if not shutil.which("ffmpeg"):
        raise RuntimeError(
            "ffmpeg não encontrado no PATH -- necessário para extrair o áudio de "
            f"arquivos de vídeo (.{video_path.suffix.lstrip('.')}). Instale o ffmpeg e tente novamente."
        )

    output_path = Path(tempfile.gettempdir()) / f"{video_path.stem}_audio.wav"
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(video_path),
            "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le",
            str(output_path),
        ],
        check=True,
        capture_output=True,
    )
    return output_path


def _build_aai_config(config: AppConfig) -> aai.TranscriptionConfig:
    return aai.TranscriptionConfig(
        speech_models=SPEECH_MODELS,
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
