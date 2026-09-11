from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from src.transcriber import collect_audio_files, extract_audio, transcribe_batch
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


def test_collect_single_audio_file(tmp_path):
    f = tmp_path / "call-recording.wav"
    f.write_bytes(b"")
    files = collect_audio_files(f)
    assert len(files) == 1
    assert files[0].path == f
    assert files[0].index == 1


@patch("src.transcriber.subprocess.run")
@patch("src.transcriber.shutil.which", return_value="/usr/bin/ffmpeg")
def test_collect_single_video_file_extracts_audio(mock_which, mock_run, tmp_path):
    f = tmp_path / "meeting.mkv"
    f.write_bytes(b"")
    files = collect_audio_files(f)
    assert len(files) == 1
    assert files[0].path.suffix == ".wav"
    assert files[0].path.name == "meeting_audio.wav"
    mock_run.assert_called_once()
    ffmpeg_args = mock_run.call_args[0][0]
    assert ffmpeg_args[0] == "ffmpeg"
    assert str(f) in ffmpeg_args


@patch("src.transcriber.shutil.which", return_value=None)
def test_extract_audio_missing_ffmpeg(mock_which, tmp_path):
    f = tmp_path / "meeting.mp4"
    f.write_bytes(b"")
    with pytest.raises(RuntimeError, match="ffmpeg"):
        extract_audio(f)


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
def test_transcribe_batch_sets_speech_models(mock_aai, tmp_path):
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

    config = make_config()
    transcribe_batch(audio_files, config)

    _, kwargs = mock_aai.TranscriptionConfig.call_args
    assert kwargs["speech_models"] == ["universal-3-5-pro", "universal-2"]


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
