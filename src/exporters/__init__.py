from .base import Exporter
from .txt import TxtExporter

EXPORTERS: dict[str, type[Exporter]] = {
    "txt": TxtExporter,
}


def get_exporters(formats: list[str]) -> list[Exporter]:
    return [EXPORTERS[fmt]() for fmt in formats if fmt in EXPORTERS]
