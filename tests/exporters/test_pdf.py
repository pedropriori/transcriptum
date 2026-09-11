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


def test_pdf_individual_with_speaker_labels_returns_bytes(diarized_result):
    exporter = PdfExporter()
    output = exporter.render_individual(diarized_result)
    assert isinstance(output, bytes)
    assert output[:4] == b"%PDF"


def test_export_writes_pdf_files(tmp_path, two_results):
    exporter = PdfExporter()
    written = exporter.export(two_results, tmp_path)
    assert any(p.suffix == ".pdf" and "FULL" in p.name for p in written)
    assert all(p.exists() for p in written)
    assert all(p.stat().st_size > 0 for p in written)
