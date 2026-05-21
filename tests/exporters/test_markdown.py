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
    assert sum(1 for p in written if p.parent.name == "individual") == 2
