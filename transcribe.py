from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich import print as rprint

from src.config import load_config, SUPPORTED_LANGUAGES, AppConfig
from src.transcriber import collect_audio_files, transcribe_batch
from src.exporters import get_exporters, JsonExporter
from src.models import TranscriptionStatus
from src.exporters.json import result_to_dict

app = typer.Typer(help="Transcriptum — batch WhatsApp audio transcription")
config_app = typer.Typer(help="Config commands")
app.add_typer(config_app, name="config")

console = Console()


@app.command()
def run(
    input: Optional[str] = typer.Option(None, "--input", "-i", help="Input directory (overrides config.yaml)"),
    formats: Optional[str] = typer.Option(None, "--formats", "-f", help="Comma-separated formats: md,txt,json,docx,pdf"),
    timestamps: bool = typer.Option(False, "--timestamps", help="Include word-level timestamps"),
    speakers: bool = typer.Option(False, "--speakers", help="Enable speaker diarization"),
    confidence: bool = typer.Option(False, "--confidence", help="Include confidence scores per word"),
) -> None:
    """Transcribe all .ogg files in the configured input directory."""
    overrides: dict = {}
    if input:
        overrides["input_dir"] = Path(input)
    if formats:
        overrides["formats"] = [f.strip() for f in formats.split(",")]

    extras: dict = {}
    if timestamps:
        extras["timestamps"] = True
    if speakers:
        extras["speaker_diarization"] = True
    if confidence:
        extras["confidence_scores"] = True
    if extras:
        overrides["extras"] = extras

    try:
        config = load_config(overrides=overrides)
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Config error:[/red] {e}")
        raise typer.Exit(1)

    if not config.api_key:
        console.print("[red]Error:[/red] ASSEMBLYAI_API_KEY not set. Add it to your .env file.")
        raise typer.Exit(1)

    try:
        audio_files = collect_audio_files(config.input_dir)
    except (FileNotFoundError, ValueError) as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    console.rule("Transcriptum")
    console.print(f"Pasta:    {config.input_dir}  ({len(audio_files)} arquivos .ogg)")
    console.print(f"Idioma:   {config.language}")
    console.print(f"Formatos: {', '.join(config.formats)}")
    console.rule()

    completed = 0
    failed = 0

    def on_result(result):
        nonlocal completed, failed
        if result.status == TranscriptionStatus.COMPLETED:
            completed += 1
            console.print(f"  [green]✓[/green] {result.audio_file.path.name}  [{result.duration_str}]")
        else:
            failed += 1
            console.print(f"  [red]✗[/red] {result.audio_file.path.name}  [red]{result.error}[/red]")

    console.print("Transcrevendo via AssemblyAI...")
    all_results = transcribe_batch(audio_files, config, on_result=on_result)

    run_id = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    output_dir = config.output_dir / config.input_dir.name / run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    # Always write transcriptions.json
    transcriptions_path = output_dir / "transcriptions.json"
    transcriptions_path.write_text(
        json.dumps([result_to_dict(r) for r in all_results], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    console.rule()
    console.print("Exportando outputs...")

    exporters = get_exporters(config.formats)
    for exporter in exporters:
        written = exporter.export(all_results, output_dir)
        ind = sum(1 for p in written if p.parent.name == "individual")
        full = [p for p in written if "FULL" in p.name]
        console.print(f"  [green]✓[/green] {ind} individuais + {full[0].name}")

    console.rule()
    console.print(f"[bold green]Concluído[/bold green]  •  {completed}/{len(all_results)} ok  •  {output_dir}")
    if failed:
        console.print(f"[yellow]Atenção:[/yellow] {failed} arquivo(s) falharam — verifique transcriptions.json")


@app.command()
def languages() -> None:
    """List all supported transcription languages."""
    table = Table(title="Idiomas suportados pelo AssemblyAI")
    table.add_column("Código", style="cyan")
    table.add_column("Idioma")
    for code, name in SUPPORTED_LANGUAGES.items():
        table.add_row(code, name)
    console.print(table)


@config_app.command("show")
def config_show() -> None:
    """Display the resolved configuration."""
    try:
        config = load_config()
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    table = Table(title="Configuração atual")
    table.add_column("Chave", style="cyan")
    table.add_column("Valor")
    table.add_row("input_dir", str(config.input_dir))
    table.add_row("output_dir", str(config.output_dir))
    table.add_row("language", config.language)
    table.add_row("formats", ", ".join(config.formats))
    table.add_row("extras.timestamps", str(config.extras.timestamps))
    table.add_row("extras.speaker_diarization", str(config.extras.speaker_diarization))
    table.add_row("extras.confidence_scores", str(config.extras.confidence_scores))
    table.add_row("api_key", "***" if config.api_key else "[red]NOT SET[/red]")
    console.print(table)


if __name__ == "__main__":
    app()
