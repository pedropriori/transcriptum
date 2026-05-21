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
