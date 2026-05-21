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
