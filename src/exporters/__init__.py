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
