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
