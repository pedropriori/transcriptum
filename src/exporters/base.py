from abc import ABC, abstractmethod
from pathlib import Path

from ..models import TranscriptionResult


class Exporter(ABC):
    @property
    @abstractmethod
    def extension(self) -> str: ...

    @abstractmethod
    def render_individual(self, result: TranscriptionResult) -> str | bytes: ...

    @abstractmethod
    def render_full(self, results: list[TranscriptionResult]) -> str | bytes: ...

    def export(
        self, results: list[TranscriptionResult], output_dir: Path
    ) -> list[Path]:
        individual_dir = output_dir / "individual"
        individual_dir.mkdir(parents=True, exist_ok=True)

        written: list[Path] = []

        for result in results:
            filename = f"{result.id}_{result.audio_file.safe_name}.{self.extension}"
            path = individual_dir / filename
            self._write(path, self.render_individual(result))
            written.append(path)

        full_path = output_dir / f"FULL.{self.extension}"
        self._write(full_path, self.render_full(results))
        written.append(full_path)

        return written

    def _write(self, path: Path, content: str | bytes) -> None:
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding="utf-8")
