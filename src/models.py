from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class TranscriptionStatus(str, Enum):
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class WordTimestamp:
    text: str
    start: int
    end: int
    confidence: float


@dataclass
class Utterance:
    speaker: str
    text: str
    start: int
    end: int


@dataclass
class AudioFile:
    path: Path
    index: int

    @property
    def safe_name(self) -> str:
        return (
            self.path.stem
            .replace(" ", "-")
            .replace("(", "")
            .replace(")", "")
        )


@dataclass
class TranscriptionResult:
    audio_file: AudioFile
    status: TranscriptionStatus
    text: str = ""
    language: str = ""
    confidence: float = 0.0
    duration_seconds: int = 0
    words: list[WordTimestamp] = field(default_factory=list)
    utterances: list[Utterance] = field(default_factory=list)
    error: str | None = None

    @property
    def id(self) -> str:
        return f"{self.audio_file.index:02d}"

    @property
    def duration_str(self) -> str:
        m, s = divmod(self.duration_seconds, 60)
        return f"{m}:{s:02d}"

    @property
    def confidence_pct(self) -> str:
        return f"{int(self.confidence * 100)}%"

    @property
    def diarized_lines(self) -> list[str]:
        """Speaker-labeled lines like '[00:34] Speaker A: texto', or [] when there's no diarization data (speaker_diarization was off, or the audio has a single speaker)."""
        lines = []
        for u in self.utterances:
            mm, ss = divmod(u.start // 1000, 60)
            lines.append(f"[{mm:02d}:{ss:02d}] Speaker {u.speaker}: {u.text}")
        return lines
