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
