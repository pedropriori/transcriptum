# Transcriptum Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** CLI tool for batch transcription of WhatsApp .OGG audio files via AssemblyAI, outputting individual and consolidated files in multiple formats (md, txt, json, docx, pdf).

**Architecture:** Typer CLI reads `config.yaml` + `.env`, collects `.ogg` files, calls AssemblyAI `transcribe_group()`, then routes results through isolated per-format `Exporter` classes. Each exporter writes individual files + a `FULL.<ext>` consolidado. A `transcriptions.json` is always written regardless of selected formats.

**Tech Stack:** Python 3.11+, assemblyai SDK, typer[all] (Rich included), pydantic v2, python-dotenv, pyyaml, python-docx, fpdf2, pytest, pytest-mock

---

## File Map

| File | Responsibility |
|---|---|
| `transcribe.py` | CLI entry point — Typer app, `run`, `languages`, `config show` commands |
| `src/__init__.py` | Package marker |
| `src/models.py` | `AudioFile`, `TranscriptionResult`, `TranscriptionStatus`, `WordTimestamp`, `Utterance` |
| `src/config.py` | `AppConfig` (Pydantic), `ExtrasConfig`, `load_config()`, `SUPPORTED_LANGUAGES` |
| `src/transcriber.py` | `collect_audio_files()`, `transcribe_batch()` |
| `src/exporters/__init__.py` | `EXPORTERS` registry, `get_exporters()` |
| `src/exporters/base.py` | Abstract `Exporter` with `export()`, `_write()` |
| `src/exporters/txt.py` | `TxtExporter` |
| `src/exporters/markdown.py` | `MarkdownExporter` |
| `src/exporters/json.py` | `JsonExporter` + `result_to_dict()` helper |
| `src/exporters/docx.py` | `DocxExporter` |
| `src/exporters/pdf.py` | `PdfExporter` |
| `tests/conftest.py` | Shared pytest fixtures |
| `tests/test_models.py` | Models unit tests |
| `tests/test_config.py` | Config loading and validation tests |
| `tests/exporters/test_txt.py` | TXT exporter + base `export()` integration |
| `tests/exporters/test_markdown.py` | Markdown exporter tests |
| `tests/exporters/test_json.py` | JSON exporter tests |
| `tests/exporters/test_docx.py` | DOCX exporter tests |
| `tests/exporters/test_pdf.py` | PDF exporter tests |
| `tests/test_transcriber.py` | Transcriber tests with mocked SDK |

---

## Task 1: Project Scaffold

**Files:**
- Create: `requirements.txt`
- Create: `.gitignore`
- Create: `.env.example`
- Create: `config.yaml`
- Create: `src/__init__.py`
- Create: `src/exporters/__init__.py` (empty placeholder)
- Create: `tests/__init__.py`
- Create: `tests/exporters/__init__.py`

- [ ] **Step 1: Create `requirements.txt`**

```
assemblyai>=0.28.0
typer[all]>=0.12.0
pydantic>=2.7.0
python-dotenv>=1.0.0
pyyaml>=6.0.1
python-docx>=1.1.0
fpdf2>=2.7.9
pytest>=8.0.0
pytest-mock>=3.12.0
```

- [ ] **Step 2: Create `.gitignore`**

```
.env
outputs/
__pycache__/
*.pyc
.pytest_cache/
*.egg-info/
dist/
.venv/
venv/
```

- [ ] **Step 3: Create `.env.example`**

```
ASSEMBLYAI_API_KEY=your_key_here
```

- [ ] **Step 4: Create `config.yaml`**

```yaml
input_dir: "./lincohn-vo"
output_dir: "./outputs"
language: "pt"
formats:
  - md
  - txt

extras:
  timestamps: false
  speaker_diarization: false
  confidence_scores: false
```

- [ ] **Step 5: Create package and test directories**

```bash
mkdir -p src/exporters tests/exporters
type nul > src/__init__.py
type nul > src/exporters/__init__.py
type nul > tests/__init__.py
type nul > tests/exporters/__init__.py
```

- [ ] **Step 6: Install dependencies**

```bash
pip install -r requirements.txt
```

Expected: all packages install without errors.

- [ ] **Step 7: Commit**

```bash
git init
git add requirements.txt .gitignore .env.example config.yaml src/__init__.py src/exporters/__init__.py tests/__init__.py tests/exporters/__init__.py
git commit -m "chore: project scaffold"
```

---

## Task 2: Data Models

**Files:**
- Create: `src/models.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_models.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_models.py -v
```

Expected: `ModuleNotFoundError` or `ImportError` — `src.models` does not exist yet.

- [ ] **Step 3: Implement `src/models.py`**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_models.py -v
```

Expected: 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/models.py tests/test_models.py
git commit -m "feat: add data models"
```

---

## Task 3: Config System

**Files:**
- Create: `src/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_config.py`:

```python
from pathlib import Path
import pytest
import yaml
from src.config import load_config, AppConfig, SUPPORTED_LANGUAGES


def write_config(tmp_path: Path, data: dict) -> Path:
    p = tmp_path / "config.yaml"
    with open(p, "w") as f:
        yaml.dump(data, f)
    return p


BASE = {
    "input_dir": "./lincohn-vo",
    "output_dir": "./outputs",
    "language": "pt",
    "formats": ["md", "txt"],
    "extras": {
        "timestamps": False,
        "speaker_diarization": False,
        "confidence_scores": False,
    },
}


def test_load_config_valid(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSEMBLYAI_API_KEY", "test-key")
    cfg_path = write_config(tmp_path, BASE)
    config = load_config(cfg_path)
    assert config.language == "pt"
    assert config.formats == ["md", "txt"]
    assert config.api_key == "test-key"
    assert config.extras.timestamps is False


def test_load_config_invalid_format(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSEMBLYAI_API_KEY", "test-key")
    data = {**BASE, "formats": ["md", "xlsx"]}
    cfg_path = write_config(tmp_path, data)
    with pytest.raises(Exception, match="Unsupported formats"):
        load_config(cfg_path)


def test_load_config_invalid_language(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSEMBLYAI_API_KEY", "test-key")
    data = {**BASE, "language": "klingon"}
    cfg_path = write_config(tmp_path, data)
    with pytest.raises(Exception, match="Unsupported language"):
        load_config(cfg_path)


def test_load_config_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_config(tmp_path / "nonexistent.yaml")


def test_load_config_format_override(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSEMBLYAI_API_KEY", "test-key")
    cfg_path = write_config(tmp_path, BASE)
    config = load_config(cfg_path, overrides={"formats": ["json"]})
    assert config.formats == ["json"]


def test_load_config_extras_merge(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSEMBLYAI_API_KEY", "test-key")
    cfg_path = write_config(tmp_path, BASE)
    config = load_config(cfg_path, overrides={"extras": {"timestamps": True}})
    assert config.extras.timestamps is True
    assert config.extras.speaker_diarization is False


def test_auto_language_is_supported():
    assert "auto" in SUPPORTED_LANGUAGES
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_config.py -v
```

Expected: `ModuleNotFoundError` for `src.config`.

- [ ] **Step 3: Implement `src/config.py`**

```python
import os
from pathlib import Path

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator

SUPPORTED_FORMATS = {"md", "txt", "json", "docx", "pdf"}

SUPPORTED_LANGUAGES: dict[str, str] = {
    "pt": "Português",
    "en": "English",
    "es": "Español",
    "fr": "Français",
    "de": "Deutsch",
    "it": "Italiano",
    "ja": "日本語",
    "ko": "한국어",
    "zh": "中文",
    "nl": "Nederlands",
    "hi": "Hindi",
    "auto": "Auto-detect",
}


class ExtrasConfig(BaseModel):
    timestamps: bool = False
    speaker_diarization: bool = False
    confidence_scores: bool = False


class AppConfig(BaseModel):
    input_dir: Path
    output_dir: Path = Path("./outputs")
    language: str = "pt"
    formats: list[str] = Field(default_factory=lambda: ["md", "txt"])
    extras: ExtrasConfig = Field(default_factory=ExtrasConfig)
    api_key: str

    @field_validator("formats")
    @classmethod
    def validate_formats(cls, v: list[str]) -> list[str]:
        invalid = set(v) - SUPPORTED_FORMATS
        if invalid:
            raise ValueError(
                f"Unsupported formats: {invalid}. Valid: {sorted(SUPPORTED_FORMATS)}"
            )
        return v

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: str) -> str:
        if v not in SUPPORTED_LANGUAGES:
            raise ValueError(
                f"Unsupported language: '{v}'. Run 'python transcribe.py languages' to see options."
            )
        return v


def load_config(
    config_path: Path = Path("config.yaml"),
    overrides: dict | None = None,
) -> AppConfig:
    load_dotenv()

    if not config_path.exists():
        raise FileNotFoundError(f"config.yaml not found at {config_path}")

    with open(config_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    data["api_key"] = os.environ.get("ASSEMBLYAI_API_KEY", "")

    if overrides:
        for key, value in overrides.items():
            if value is not None:
                if key == "extras" and isinstance(value, dict):
                    existing = data.get("extras") or {}
                    existing.update(value)
                    data["extras"] = existing
                else:
                    data[key] = value

    return AppConfig(**data)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_config.py -v
```

Expected: 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/config.py tests/test_config.py
git commit -m "feat: add config system with pydantic validation"
```

---

## Task 4: Base Exporter + TXT Exporter

**Files:**
- Create: `src/exporters/base.py`
- Create: `src/exporters/txt.py`
- Modify: `src/exporters/__init__.py`
- Create: `tests/conftest.py`
- Create: `tests/exporters/test_txt.py`

- [ ] **Step 1: Write shared test fixtures**

Create `tests/conftest.py`:

```python
from pathlib import Path
import pytest
from src.models import AudioFile, TranscriptionResult, TranscriptionStatus


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
```

- [ ] **Step 2: Write failing TXT tests**

Create `tests/exporters/test_txt.py`:

```python
from pathlib import Path
from src.exporters.txt import TxtExporter
from src.models import TranscriptionStatus


def test_txt_individual_contains_filename(one_result):
    exporter = TxtExporter()
    output = exporter.render_individual(one_result)
    assert "WhatsApp Audio 2026-05-21 at 11.14.53.ogg" in output


def test_txt_individual_contains_text(one_result):
    exporter = TxtExporter()
    output = exporter.render_individual(one_result)
    assert "Olá, como vai você?" in output


def test_txt_individual_contains_duration(one_result):
    exporter = TxtExporter()
    output = exporter.render_individual(one_result)
    assert "0:28" in output


def test_txt_full_contains_all_texts(two_results):
    exporter = TxtExporter()
    output = exporter.render_full(two_results)
    assert "Primeiro áudio." in output
    assert "Segundo áudio." in output


def test_txt_full_contains_index(two_results):
    exporter = TxtExporter()
    output = exporter.render_full(two_results)
    assert "01." in output or "01 " in output
    assert "02." in output or "02 " in output


def test_export_writes_individual_and_full_files(tmp_path, two_results):
    exporter = TxtExporter()
    written = exporter.export(two_results, tmp_path)
    individual_files = [p for p in written if "individual" in str(p)]
    full_files = [p for p in written if "FULL" in p.name]
    assert len(individual_files) == 2
    assert len(full_files) == 1
    assert full_files[0].name == "FULL.txt"
    assert all(p.exists() for p in written)


def test_export_individual_filename_format(tmp_path, two_results):
    exporter = TxtExporter()
    exporter.export(two_results, tmp_path)
    individual_dir = tmp_path / "individual"
    files = sorted(individual_dir.iterdir())
    assert files[0].name.startswith("01_")
    assert files[0].suffix == ".txt"
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
pytest tests/exporters/test_txt.py -v
```

Expected: `ModuleNotFoundError` for `src.exporters.txt`.

- [ ] **Step 4: Implement `src/exporters/base.py`**

```python
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
```

- [ ] **Step 5: Implement `src/exporters/txt.py`**

```python
from datetime import datetime

from .base import Exporter
from ..models import TranscriptionResult, TranscriptionStatus


class TxtExporter(Exporter):
    extension = "txt"

    def render_individual(self, result: TranscriptionResult) -> str:
        body = (
            result.text
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
                r.text
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
```

- [ ] **Step 6: Update `src/exporters/__init__.py`**

```python
from .base import Exporter
from .txt import TxtExporter

EXPORTERS: dict[str, type[Exporter]] = {
    "txt": TxtExporter,
}


def get_exporters(formats: list[str]) -> list[Exporter]:
    return [EXPORTERS[fmt]() for fmt in formats if fmt in EXPORTERS]
```

- [ ] **Step 7: Run tests to verify they pass**

```bash
pytest tests/exporters/test_txt.py tests/test_models.py tests/test_config.py -v
```

Expected: all tests PASS.

- [ ] **Step 8: Commit**

```bash
git add src/exporters/base.py src/exporters/txt.py src/exporters/__init__.py tests/conftest.py tests/exporters/test_txt.py
git commit -m "feat: add base exporter and TXT exporter"
```

---

## Task 5: Markdown Exporter

**Files:**
- Create: `src/exporters/markdown.py`
- Create: `tests/exporters/test_markdown.py`
- Modify: `src/exporters/__init__.py`

- [ ] **Step 1: Write failing tests**

Create `tests/exporters/test_markdown.py`:

```python
from src.exporters.markdown import MarkdownExporter


def test_md_individual_has_h1(one_result):
    exporter = MarkdownExporter()
    output = exporter.render_individual(one_result)
    assert output.startswith("# WhatsApp Audio")


def test_md_individual_has_blockquote_meta(one_result):
    exporter = MarkdownExporter()
    output = exporter.render_individual(one_result)
    assert "> Duração:" in output


def test_md_individual_contains_text(one_result):
    exporter = MarkdownExporter()
    output = exporter.render_individual(one_result)
    assert "Olá, como vai você?" in output


def test_md_full_has_h1(two_results):
    exporter = MarkdownExporter()
    output = exporter.render_full(two_results)
    assert output.startswith("# Transcrição")


def test_md_full_has_index_table(two_results):
    exporter = MarkdownExporter()
    output = exporter.render_full(two_results)
    assert "| # | Arquivo |" in output
    assert "| 01 |" in output
    assert "| 02 |" in output


def test_md_full_has_h2_sections(two_results):
    exporter = MarkdownExporter()
    output = exporter.render_full(two_results)
    assert "## 01 ·" in output
    assert "## 02 ·" in output


def test_md_full_contains_all_texts(two_results):
    exporter = MarkdownExporter()
    output = exporter.render_full(two_results)
    assert "Primeiro áudio." in output
    assert "Segundo áudio." in output


def test_export_writes_md_files(tmp_path, two_results):
    exporter = MarkdownExporter()
    written = exporter.export(two_results, tmp_path)
    assert any(p.suffix == ".md" and "FULL" in p.name for p in written)
    assert sum(1 for p in written if "individual" in str(p)) == 2
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/exporters/test_markdown.py -v
```

Expected: `ModuleNotFoundError` for `src.exporters.markdown`.

- [ ] **Step 3: Implement `src/exporters/markdown.py`**

```python
from datetime import datetime

from .base import Exporter
from ..models import TranscriptionResult, TranscriptionStatus


class MarkdownExporter(Exporter):
    extension = "md"

    def render_individual(self, result: TranscriptionResult) -> str:
        body = (
            result.text
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
                r.text
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
```

- [ ] **Step 4: Update `src/exporters/__init__.py`**

```python
from .base import Exporter
from .txt import TxtExporter
from .markdown import MarkdownExporter

EXPORTERS: dict[str, type[Exporter]] = {
    "txt": TxtExporter,
    "md": MarkdownExporter,
}


def get_exporters(formats: list[str]) -> list[Exporter]:
    return [EXPORTERS[fmt]() for fmt in formats if fmt in EXPORTERS]
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/exporters/test_markdown.py -v
```

Expected: 8 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add src/exporters/markdown.py src/exporters/__init__.py tests/exporters/test_markdown.py
git commit -m "feat: add markdown exporter"
```

---

## Task 6: JSON Exporter

**Files:**
- Create: `src/exporters/json.py`
- Create: `tests/exporters/test_json.py`
- Modify: `src/exporters/__init__.py`

- [ ] **Step 1: Write failing tests**

Create `tests/exporters/test_json.py`:

```python
import json
from src.exporters.json import JsonExporter, result_to_dict
from src.models import TranscriptionStatus


def test_result_to_dict_keys(one_result):
    d = result_to_dict(one_result)
    for key in ("id", "filename", "duration_seconds", "language", "confidence", "text", "words", "utterances", "status"):
        assert key in d


def test_result_to_dict_values(one_result):
    d = result_to_dict(one_result)
    assert d["id"] == "01"
    assert d["status"] == "completed"
    assert d["text"] == "Olá, como vai você?"
    assert d["language"] == "pt"
    assert d["confidence"] == 0.96


def test_json_individual_is_valid_json(one_result):
    exporter = JsonExporter()
    output = exporter.render_individual(one_result)
    data = json.loads(output)
    assert data["text"] == "Olá, como vai você?"


def test_json_full_is_valid_json_array(two_results):
    exporter = JsonExporter()
    output = exporter.render_full(two_results)
    data = json.loads(output)
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]["id"] == "01"
    assert data[1]["id"] == "02"


def test_json_full_preserves_unicode(two_results):
    exporter = JsonExporter()
    output = exporter.render_full(two_results)
    assert "Primeiro" in output
    assert "Segundo" in output


def test_export_writes_transcriptions_json(tmp_path, two_results):
    exporter = JsonExporter()
    written = exporter.export(two_results, tmp_path)
    full = next(p for p in written if p.name == "FULL.json")
    data = json.loads(full.read_text(encoding="utf-8"))
    assert len(data) == 2
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/exporters/test_json.py -v
```

Expected: `ModuleNotFoundError` for `src.exporters.json`.

- [ ] **Step 3: Implement `src/exporters/json.py`**

```python
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
```

- [ ] **Step 4: Update `src/exporters/__init__.py`**

```python
from .base import Exporter
from .txt import TxtExporter
from .markdown import MarkdownExporter
from .json import JsonExporter

EXPORTERS: dict[str, type[Exporter]] = {
    "txt": TxtExporter,
    "md": MarkdownExporter,
    "json": JsonExporter,
}


def get_exporters(formats: list[str]) -> list[Exporter]:
    return [EXPORTERS[fmt]() for fmt in formats if fmt in EXPORTERS]
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/exporters/test_json.py -v
```

Expected: 6 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add src/exporters/json.py src/exporters/__init__.py tests/exporters/test_json.py
git commit -m "feat: add JSON exporter"
```

---

## Task 7: DOCX Exporter

**Files:**
- Create: `src/exporters/docx.py`
- Create: `tests/exporters/test_docx.py`
- Modify: `src/exporters/__init__.py`

- [ ] **Step 1: Write failing tests**

Create `tests/exporters/test_docx.py`:

```python
from io import BytesIO
from docx import Document
from src.exporters.docx import DocxExporter


def test_docx_individual_returns_bytes(one_result):
    exporter = DocxExporter()
    output = exporter.render_individual(one_result)
    assert isinstance(output, bytes)
    assert len(output) > 0


def test_docx_individual_is_valid_docx(one_result):
    exporter = DocxExporter()
    output = exporter.render_individual(one_result)
    doc = Document(BytesIO(output))
    full_text = "\n".join(p.text for p in doc.paragraphs)
    assert "Olá, como vai você?" in full_text


def test_docx_individual_has_filename_heading(one_result):
    exporter = DocxExporter()
    output = exporter.render_individual(one_result)
    doc = Document(BytesIO(output))
    headings = [p.text for p in doc.paragraphs if p.style.name.startswith("Heading")]
    assert any("WhatsApp Audio" in h for h in headings)


def test_docx_full_returns_bytes(two_results):
    exporter = DocxExporter()
    output = exporter.render_full(two_results)
    assert isinstance(output, bytes)


def test_docx_full_contains_all_texts(two_results):
    exporter = DocxExporter()
    output = exporter.render_full(two_results)
    doc = Document(BytesIO(output))
    full_text = "\n".join(p.text for p in doc.paragraphs)
    assert "Primeiro áudio." in full_text
    assert "Segundo áudio." in full_text


def test_export_writes_docx_files(tmp_path, two_results):
    exporter = DocxExporter()
    written = exporter.export(two_results, tmp_path)
    assert any(p.suffix == ".docx" and "FULL" in p.name for p in written)
    assert all(p.exists() for p in written)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/exporters/test_docx.py -v
```

Expected: `ModuleNotFoundError` for `src.exporters.docx`.

- [ ] **Step 3: Implement `src/exporters/docx.py`**

```python
from datetime import datetime
from io import BytesIO

from docx import Document

from .base import Exporter
from ..models import TranscriptionResult, TranscriptionStatus


class DocxExporter(Exporter):
    extension = "docx"

    def render_individual(self, result: TranscriptionResult) -> bytes:
        doc = Document()
        doc.add_heading(result.audio_file.path.name, level=1)

        meta = doc.add_paragraph()
        run = meta.add_run(
            f"Duração: {result.duration_str}  |  Idioma: {result.language}  |  Confiança: {result.confidence_pct}"
        )
        run.italic = True

        doc.add_paragraph()
        body = (
            result.text
            if result.status == TranscriptionStatus.COMPLETED
            else f"[FALHOU: {result.error}]"
        )
        doc.add_paragraph(body)

        buf = BytesIO()
        doc.save(buf)
        return buf.getvalue()

    def render_full(self, results: list[TranscriptionResult]) -> bytes:
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        folder = results[0].audio_file.path.parent.name if results else "—"
        lang = results[0].language if results else "—"

        doc = Document()
        doc.add_heading(f"Transcrição — {folder}", level=1)

        meta = doc.add_paragraph()
        run = meta.add_run(f"Gerado em {now}  ·  {len(results)} áudios  ·  Idioma: {lang}")
        run.italic = True

        doc.add_heading("Índice", level=2)
        for r in results:
            doc.add_paragraph(f"{r.id}. {r.audio_file.path.name} ({r.duration_str})")

        doc.add_page_break()

        for r in results:
            doc.add_heading(f"{r.id} · {r.audio_file.path.name}", level=2)

            dur_p = doc.add_paragraph()
            dur_p.add_run(f"Duração: {r.duration_str}").italic = True

            body = (
                r.text
                if r.status == TranscriptionStatus.COMPLETED
                else f"[FALHOU: {r.error}]"
            )
            doc.add_paragraph(body)
            doc.add_paragraph("─" * 30)

        buf = BytesIO()
        doc.save(buf)
        return buf.getvalue()
```

- [ ] **Step 4: Update `src/exporters/__init__.py`**

```python
from .base import Exporter
from .txt import TxtExporter
from .markdown import MarkdownExporter
from .json import JsonExporter
from .docx import DocxExporter

EXPORTERS: dict[str, type[Exporter]] = {
    "txt": TxtExporter,
    "md": MarkdownExporter,
    "json": JsonExporter,
    "docx": DocxExporter,
}


def get_exporters(formats: list[str]) -> list[Exporter]:
    return [EXPORTERS[fmt]() for fmt in formats if fmt in EXPORTERS]
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/exporters/test_docx.py -v
```

Expected: 6 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add src/exporters/docx.py src/exporters/__init__.py tests/exporters/test_docx.py
git commit -m "feat: add DOCX exporter"
```

---

## Task 8: PDF Exporter

**Files:**
- Create: `src/exporters/pdf.py`
- Create: `tests/exporters/test_pdf.py`
- Modify: `src/exporters/__init__.py`

- [ ] **Step 1: Write failing tests**

Create `tests/exporters/test_pdf.py`:

```python
from src.exporters.pdf import PdfExporter


def test_pdf_individual_returns_bytes(one_result):
    exporter = PdfExporter()
    output = exporter.render_individual(one_result)
    assert isinstance(output, bytes)
    assert output[:4] == b"%PDF"


def test_pdf_full_returns_bytes(two_results):
    exporter = PdfExporter()
    output = exporter.render_full(two_results)
    assert isinstance(output, bytes)
    assert output[:4] == b"%PDF"


def test_export_writes_pdf_files(tmp_path, two_results):
    exporter = PdfExporter()
    written = exporter.export(two_results, tmp_path)
    assert any(p.suffix == ".pdf" and "FULL" in p.name for p in written)
    assert all(p.exists() for p in written)
    assert all(p.stat().st_size > 0 for p in written)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/exporters/test_pdf.py -v
```

Expected: `ModuleNotFoundError` for `src.exporters.pdf`.

- [ ] **Step 3: Implement `src/exporters/pdf.py`**

Note: fpdf2 built-in fonts (Helvetica) support Latin-1, which covers all Portuguese accented characters. For languages outside Latin-1 (e.g. Japanese), a Unicode TTF font would need to be added.

```python
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
        pdf.multi_cell(0, 10, result.audio_file.path.name)

        pdf.set_font("Helvetica", "I", 10)
        pdf.multi_cell(
            0, 8,
            f"Duração: {result.duration_str}  |  Idioma: {result.language}  |  Confiança: {result.confidence_pct}",
        )
        pdf.ln(4)

        pdf.set_font("Helvetica", "", 11)
        body = (
            result.text
            if result.status == TranscriptionStatus.COMPLETED
            else f"[FALHOU: {result.error}]"
        )
        pdf.multi_cell(0, 8, body)

        return bytes(pdf.output())

    def render_full(self, results: list[TranscriptionResult]) -> bytes:
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        folder = results[0].audio_file.path.parent.name if results else "—"
        lang = results[0].language if results else "—"

        pdf = self._new_pdf()

        pdf.set_font("Helvetica", "B", 16)
        pdf.multi_cell(0, 12, f"Transcricao - {folder}")

        pdf.set_font("Helvetica", "I", 10)
        pdf.multi_cell(0, 8, f"Gerado em {now}  |  {len(results)} audios  |  Idioma: {lang}")
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
            pdf.multi_cell(0, 9, f"{r.id} - {r.audio_file.path.name}")

            pdf.set_font("Helvetica", "I", 10)
            pdf.multi_cell(0, 7, f"Duracao: {r.duration_str}")
            pdf.ln(2)

            pdf.set_font("Helvetica", "", 11)
            body = (
                r.text
                if r.status == TranscriptionStatus.COMPLETED
                else f"[FALHOU: {r.error}]"
            )
            pdf.multi_cell(0, 8, body)
            pdf.ln(4)
            pdf.set_draw_color(180, 180, 180)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(4)

        return bytes(pdf.output())
```

Note: PDF text is ASCII-safe (no accented chars in headings) to avoid encoding issues with Helvetica. The transcription body text may contain accented Portuguese chars — fpdf2 handles Latin-1 automatically for Helvetica. If PDF shows garbled text for body content, see `fpdf2` docs on adding a Unicode TTF font.

- [ ] **Step 4: Update `src/exporters/__init__.py`**

```python
from .base import Exporter
from .txt import TxtExporter
from .markdown import MarkdownExporter
from .json import JsonExporter
from .docx import DocxExporter
from .pdf import PdfExporter

EXPORTERS: dict[str, type[Exporter]] = {
    "txt": TxtExporter,
    "md": MarkdownExporter,
    "json": JsonExporter,
    "docx": DocxExporter,
    "pdf": PdfExporter,
}


def get_exporters(formats: list[str]) -> list[Exporter]:
    return [EXPORTERS[fmt]() for fmt in formats if fmt in EXPORTERS]
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/exporters/test_pdf.py -v
```

Expected: 3 tests PASS.

- [ ] **Step 6: Run the full test suite to confirm no regressions**

```bash
pytest -v
```

Expected: all tests PASS.

- [ ] **Step 7: Commit**

```bash
git add src/exporters/pdf.py src/exporters/__init__.py tests/exporters/test_pdf.py
git commit -m "feat: add PDF exporter"
```

---

## Task 9: Transcriber

**Files:**
- Create: `src/transcriber.py`
- Create: `tests/test_transcriber.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_transcriber.py`:

```python
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from src.transcriber import collect_audio_files, transcribe_batch
from src.models import TranscriptionStatus
from src.config import AppConfig, ExtrasConfig


def make_config(api_key: str = "test-key", language: str = "pt") -> AppConfig:
    return AppConfig(
        input_dir=Path("./lincohn-vo"),
        output_dir=Path("./outputs"),
        language=language,
        formats=["md"],
        extras=ExtrasConfig(),
        api_key=api_key,
    )


def test_collect_audio_files(tmp_path):
    (tmp_path / "audio_b.ogg").write_bytes(b"")
    (tmp_path / "audio_a.ogg").write_bytes(b"")
    (tmp_path / "ignore.mp3").write_bytes(b"")
    files = collect_audio_files(tmp_path)
    assert len(files) == 2
    assert files[0].path.name == "audio_a.ogg"
    assert files[0].index == 1
    assert files[1].index == 2


def test_collect_audio_files_sorted(tmp_path):
    for name in ["c.ogg", "a.ogg", "b.ogg"]:
        (tmp_path / name).write_bytes(b"")
    files = collect_audio_files(tmp_path)
    names = [f.path.name for f in files]
    assert names == ["a.ogg", "b.ogg", "c.ogg"]


def test_collect_audio_files_missing_dir():
    with pytest.raises(FileNotFoundError):
        collect_audio_files(Path("/nonexistent/path"))


def test_collect_audio_files_empty_dir(tmp_path):
    with pytest.raises(ValueError, match="No .ogg files found"):
        collect_audio_files(tmp_path)


@patch("src.transcriber.aai")
def test_transcribe_batch_completed(mock_aai, tmp_path):
    f = tmp_path / "test.ogg"
    f.write_bytes(b"")
    from src.models import AudioFile
    audio_files = [AudioFile(path=f, index=1)]

    mock_transcript = MagicMock()
    mock_transcript.status = mock_aai.TranscriptStatus.completed
    mock_transcript.text = "Olá mundo"
    mock_transcript.language_code = "pt"
    mock_transcript.confidence = 0.95
    mock_transcript.audio_duration = 10.0
    mock_transcript.words = []
    mock_transcript.utterances = []

    mock_transcriber = MagicMock()
    mock_transcriber.transcribe_group.return_value = [mock_transcript]
    mock_aai.Transcriber.return_value = mock_transcriber

    config = make_config()
    results = transcribe_batch(audio_files, config)

    assert len(results) == 1
    assert results[0].status == TranscriptionStatus.COMPLETED
    assert results[0].text == "Olá mundo"
    assert results[0].duration_seconds == 10


@patch("src.transcriber.aai")
def test_transcribe_batch_failed(mock_aai, tmp_path):
    f = tmp_path / "test.ogg"
    f.write_bytes(b"")
    from src.models import AudioFile
    audio_files = [AudioFile(path=f, index=1)]

    mock_transcript = MagicMock()
    mock_transcript.status = mock_aai.TranscriptStatus.error
    mock_transcript.error = "Audio too short"

    mock_transcriber = MagicMock()
    mock_transcriber.transcribe_group.return_value = [mock_transcript]
    mock_aai.Transcriber.return_value = mock_transcriber

    config = make_config()
    results = transcribe_batch(audio_files, config)

    assert results[0].status == TranscriptionStatus.FAILED
    assert results[0].error == "Audio too short"


@patch("src.transcriber.aai")
def test_transcribe_batch_sets_api_key(mock_aai, tmp_path):
    f = tmp_path / "test.ogg"
    f.write_bytes(b"")
    from src.models import AudioFile
    audio_files = [AudioFile(path=f, index=1)]

    mock_transcript = MagicMock()
    mock_transcript.status = mock_aai.TranscriptStatus.completed
    mock_transcript.text = ""
    mock_transcript.language_code = "pt"
    mock_transcript.confidence = 0.0
    mock_transcript.audio_duration = 0.0
    mock_transcript.words = []
    mock_transcript.utterances = []
    mock_aai.Transcriber.return_value.transcribe_group.return_value = [mock_transcript]

    config = make_config(api_key="my-secret-key")
    transcribe_batch(audio_files, config)

    assert mock_aai.settings.api_key == "my-secret-key"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_transcriber.py -v
```

Expected: `ModuleNotFoundError` for `src.transcriber`.

- [ ] **Step 3: Implement `src/transcriber.py`**

```python
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

    return TranscriptionResult(
        audio_file=audio_file,
        status=TranscriptionStatus.COMPLETED,
        text=transcript.text or "",
        language=transcript.language_code or "",
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_transcriber.py -v
```

Expected: 7 tests PASS.

- [ ] **Step 5: Run the full test suite**

```bash
pytest -v
```

Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add src/transcriber.py tests/test_transcriber.py
git commit -m "feat: add transcriber with AssemblyAI batch support"
```

---

## Task 10: CLI

**Files:**
- Create: `transcribe.py`

- [ ] **Step 1: Implement `transcribe.py`**

```python
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich import print as rprint

from src.config import load_config, SUPPORTED_LANGUAGES, AppConfig
from src.transcriber import collect_audio_files, transcribe_batch
from src.exporters import get_exporters, JsonExporter
from src.models import TranscriptionStatus
from src.exporters.json import result_to_dict

app = typer.Typer(help="Transcriptum — batch WhatsApp audio transcription")
config_app = typer.Typer(help="Config commands")
app.add_typer(config_app, name="config")

console = Console()


@app.command()
def run(
    input: Optional[str] = typer.Option(None, "--input", "-i", help="Input directory (overrides config.yaml)"),
    formats: Optional[str] = typer.Option(None, "--formats", "-f", help="Comma-separated formats: md,txt,json,docx,pdf"),
    timestamps: bool = typer.Option(False, "--timestamps", help="Include word-level timestamps"),
    speakers: bool = typer.Option(False, "--speakers", help="Enable speaker diarization"),
    confidence: bool = typer.Option(False, "--confidence", help="Include confidence scores per word"),
) -> None:
    """Transcribe all .ogg files in the configured input directory."""
    overrides: dict = {}
    if input:
        overrides["input_dir"] = Path(input)
    if formats:
        overrides["formats"] = [f.strip() for f in formats.split(",")]

    extras: dict = {}
    if timestamps:
        extras["timestamps"] = True
    if speakers:
        extras["speaker_diarization"] = True
    if confidence:
        extras["confidence_scores"] = True
    if extras:
        overrides["extras"] = extras

    try:
        config = load_config(overrides=overrides)
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Config error:[/red] {e}")
        raise typer.Exit(1)

    if not config.api_key:
        console.print("[red]Error:[/red] ASSEMBLYAI_API_KEY not set. Add it to your .env file.")
        raise typer.Exit(1)

    try:
        audio_files = collect_audio_files(config.input_dir)
    except (FileNotFoundError, ValueError) as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    console.rule("Transcriptum")
    console.print(f"Pasta:    {config.input_dir}  ({len(audio_files)} arquivos .ogg)")
    console.print(f"Idioma:   {config.language}")
    console.print(f"Formatos: {', '.join(config.formats)}")
    console.rule()

    completed = 0
    failed = 0

    def on_result(result):
        nonlocal completed, failed
        if result.status == TranscriptionStatus.COMPLETED:
            completed += 1
            console.print(f"  [green]✓[/green] {result.audio_file.path.name}  [{result.duration_str}]")
        else:
            failed += 1
            console.print(f"  [red]✗[/red] {result.audio_file.path.name}  [red]{result.error}[/red]")

    # console.status() would suppress per-file output — print header then let on_result update live
    console.print("Transcrevendo via AssemblyAI...")
    all_results = transcribe_batch(audio_files, config, on_result=on_result)

    run_id = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    output_dir = config.output_dir / config.input_dir.name / run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    # Always write transcriptions.json
    transcriptions_path = output_dir / "transcriptions.json"
    transcriptions_path.write_text(
        json.dumps([result_to_dict(r) for r in all_results], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    console.rule()
    console.print("Exportando outputs...")

    exporters = get_exporters(config.formats)
    for exporter in exporters:
        written = exporter.export(all_results, output_dir)
        ind = sum(1 for p in written if "individual" in str(p))
        full = [p for p in written if "FULL" in p.name]
        console.print(f"  [green]✓[/green] {ind} individuais + {full[0].name}")

    console.rule()
    console.print(f"[bold green]Concluído[/bold green]  •  {completed}/{len(all_results)} ok  •  {output_dir}")
    if failed:
        console.print(f"[yellow]Atenção:[/yellow] {failed} arquivo(s) falharam — verifique transcriptions.json")


@app.command()
def languages() -> None:
    """List all supported transcription languages."""
    table = Table(title="Idiomas suportados pelo AssemblyAI")
    table.add_column("Código", style="cyan")
    table.add_column("Idioma")
    for code, name in SUPPORTED_LANGUAGES.items():
        table.add_row(code, name)
    console.print(table)


@config_app.command("show")
def config_show() -> None:
    """Display the resolved configuration."""
    try:
        config = load_config()
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    table = Table(title="Configuração atual")
    table.add_column("Chave", style="cyan")
    table.add_column("Valor")
    table.add_row("input_dir", str(config.input_dir))
    table.add_row("output_dir", str(config.output_dir))
    table.add_row("language", config.language)
    table.add_row("formats", ", ".join(config.formats))
    table.add_row("extras.timestamps", str(config.extras.timestamps))
    table.add_row("extras.speaker_diarization", str(config.extras.speaker_diarization))
    table.add_row("extras.confidence_scores", str(config.extras.confidence_scores))
    table.add_row("api_key", "***" if config.api_key else "[red]NOT SET[/red]")
    console.print(table)


if __name__ == "__main__":
    app()
```

- [ ] **Step 2: Smoke test — verify CLI help works**

```bash
python transcribe.py --help
```

Expected output includes: `run`, `languages`, `config` commands listed.

```bash
python transcribe.py languages
```

Expected: table with language codes and names including `pt` and `auto`.

```bash
python transcribe.py config show
```

Expected: table showing `input_dir: lincohn-vo`, `language: pt`, `formats: md, txt`.

- [ ] **Step 3: End-to-end test with real API**

Add your key to `.env`:
```
ASSEMBLYAI_API_KEY=<your_real_key>
```

Run:
```bash
python transcribe.py run
```

Expected:
- Per-file `✓` lines appear as transcriptions complete
- `outputs/lincohn-vo/<timestamp>/` created
- `individual/` folder with 50 `.md` and `.txt` files
- `FULL.md`, `FULL.txt`, `transcriptions.json` at the run root
- Final summary line shows `50/50 ok`

- [ ] **Step 4: Test format override**

```bash
python transcribe.py run --formats md,json,docx
```

Expected: `FULL.md`, `FULL.json`, `FULL.docx` and individual files for all three formats in the new run folder.

- [ ] **Step 5: Commit**

```bash
git add transcribe.py
git commit -m "feat: add Typer CLI with run, languages, and config show commands"
```

---

## Final Checks

- [ ] Run the full test suite one last time

```bash
pytest -v
```

Expected: all tests PASS, no warnings about missing fixtures or imports.

- [ ] Verify `.env` is gitignored and `outputs/` is gitignored

```bash
git status
```

Expected: `.env` and `outputs/` do NOT appear as untracked files.
