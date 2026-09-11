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


def test_txt_individual_renders_speaker_labels(diarized_result):
    exporter = TxtExporter()
    output = exporter.render_individual(diarized_result)
    assert "[00:00] Speaker A: Fala, tudo bem?" in output
    assert "[00:02] Speaker B: Tudo, e você?" in output


def test_export_writes_individual_and_full_files(tmp_path, two_results):
    exporter = TxtExporter()
    written = exporter.export(two_results, tmp_path)
    individual_files = [p for p in written if p.parent.name == "individual"]
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
