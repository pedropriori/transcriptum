from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.text import Text

from src.config import load_config, SUPPORTED_LANGUAGES, SUPPORTED_FORMATS, AppConfig
from src.transcriber import collect_audio_files, transcribe_batch
from src.exporters import get_exporters
from src.models import TranscriptionStatus
from src.exporters.json import result_to_dict

app = typer.Typer(help="Transcriptum — batch WhatsApp audio transcription")
config_app = typer.Typer(help="Config commands")
app.add_typer(config_app, name="config")

console = Console()

_FORMATS_AVAILABLE = sorted(SUPPORTED_FORMATS)


def _show_config_panel(config: AppConfig, n_files: int | None = None) -> None:
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Chave", style="dim")
    table.add_column("Valor", style="bold")

    dir_label = str(config.input_dir)
    if n_files is not None:
        dir_label += f"  [dim]({n_files} arquivos .ogg)[/dim]"
    table.add_row("Pasta de entrada", dir_label)
    table.add_row("Pasta de saída", str(config.output_dir))
    table.add_row("Idioma", f"{config.language}  [dim]({SUPPORTED_LANGUAGES.get(config.language, '')})[/dim]")
    table.add_row("Formatos", ", ".join(config.formats))
    table.add_row("Timestamps", "[green]sim[/green]" if config.extras.timestamps else "[dim]não[/dim]")
    table.add_row("Diarização", "[green]sim[/green]" if config.extras.speaker_diarization else "[dim]não[/dim]")
    table.add_row("Confiança", "[green]sim[/green]" if config.extras.confidence_scores else "[dim]não[/dim]")
    table.add_row("API Key", "[green]●[/green] configurada" if config.api_key else "[red]● NÃO CONFIGURADA[/red]")

    console.print(Panel(table, title="[bold]Configuração[/bold]", border_style="blue"))


def _interactive_overrides(config: AppConfig) -> dict:
    """Ask the user to review and optionally change run settings. Returns overrides dict."""
    overrides: dict = {}

    console.print()
    if not Confirm.ask("[bold]Personalizar configurações?[/bold]", default=False, console=console):
        return overrides

    console.print()

    # Input directory
    new_input = Prompt.ask(
        f"  Pasta de entrada",
        default=str(config.input_dir),
        console=console,
    )
    if new_input != str(config.input_dir):
        overrides["input_dir"] = Path(new_input)

    # Language
    lang_hint = "/".join(SUPPORTED_LANGUAGES.keys())
    new_lang = Prompt.ask(
        f"  Idioma  [dim]({lang_hint})[/dim]",
        default=config.language,
        console=console,
    )
    if new_lang != config.language:
        overrides["language"] = new_lang

    # Formats
    fmt_hint = "  ".join(_FORMATS_AVAILABLE)
    current_formats = ", ".join(config.formats)
    raw_formats = Prompt.ask(
        f"  Formatos  [dim](disponíveis: {fmt_hint})[/dim]",
        default=current_formats,
        console=console,
    )
    new_formats = [f.strip() for f in raw_formats.replace(" ", ",").split(",") if f.strip()]
    if new_formats != config.formats:
        overrides["formats"] = new_formats

    # Extras
    console.print()
    console.print("  [dim]Extras (dados adicionais na transcrição):[/dim]")
    extras: dict = {}

    new_ts = Confirm.ask("    Timestamps por palavra?", default=config.extras.timestamps, console=console)
    if new_ts != config.extras.timestamps:
        extras["timestamps"] = new_ts

    new_spk = Confirm.ask("    Diarização por speaker?", default=config.extras.speaker_diarization, console=console)
    if new_spk != config.extras.speaker_diarization:
        extras["speaker_diarization"] = new_spk

    new_conf = Confirm.ask("    Confiança por palavra?", default=config.extras.confidence_scores, console=console)
    if new_conf != config.extras.confidence_scores:
        extras["confidence_scores"] = new_conf

    if extras:
        overrides["extras"] = extras

    return overrides


@app.command()
def run(
    input: Optional[str] = typer.Option(None, "--input", "-i", help="Pasta de entrada (sobrescreve config.yaml)"),
    formats: Optional[str] = typer.Option(None, "--formats", "-f", help="Formatos separados por vírgula: md,txt,json,docx,pdf"),
    timestamps: bool = typer.Option(False, "--timestamps", help="Incluir timestamps por palavra"),
    speakers: bool = typer.Option(False, "--speakers", help="Habilitar diarização por speaker"),
    confidence: bool = typer.Option(False, "--confidence", help="Incluir confiança por palavra"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Pular seleção interativa, usar config.yaml direto"),
) -> None:
    """Transcreve todos os .ogg da pasta de entrada."""

    # Build CLI overrides from flags
    flag_overrides: dict = {}
    if input:
        flag_overrides["input_dir"] = Path(input)
    if formats:
        flag_overrides["formats"] = [f.strip() for f in formats.split(",")]
    extras: dict = {}
    if timestamps:
        extras["timestamps"] = True
    if speakers:
        extras["speaker_diarization"] = True
    if confidence:
        extras["confidence_scores"] = True
    if extras:
        flag_overrides["extras"] = extras

    # Load config with flag overrides first
    try:
        config = load_config(overrides=flag_overrides if flag_overrides else None)
    except FileNotFoundError as e:
        console.print(f"[red]Erro:[/red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Erro de configuração:[/red] {e}")
        raise typer.Exit(1)

    # Resolve file count early for the panel
    try:
        audio_files = collect_audio_files(config.input_dir)
    except (FileNotFoundError, ValueError) as e:
        audio_files = None
        audio_error = str(e)
    else:
        audio_error = None

    console.rule("[bold]Transcriptum[/bold]")
    _show_config_panel(config, n_files=len(audio_files) if audio_files else None)

    # Interactive mode: only when no flags were passed and not --yes
    if not flag_overrides and not yes:
        interactive_overrides = _interactive_overrides(config)
        if interactive_overrides:
            try:
                config = load_config(overrides=interactive_overrides)
            except Exception as e:
                console.print(f"[red]Erro de configuração:[/red] {e}")
                raise typer.Exit(1)
            # Re-resolve files if input_dir changed
            if "input_dir" in interactive_overrides:
                try:
                    audio_files = collect_audio_files(config.input_dir)
                    audio_error = None
                except (FileNotFoundError, ValueError) as e:
                    audio_files = None
                    audio_error = str(e)
            console.print()
            console.rule("[bold]Configuração final[/bold]")
            _show_config_panel(config, n_files=len(audio_files) if audio_files else None)

    if not config.api_key:
        console.print("[red]Erro:[/red] ASSEMBLYAI_API_KEY não configurada. Adicione ao arquivo .env.")
        raise typer.Exit(1)

    if audio_files is None:
        console.print(f"[red]Erro:[/red] {audio_error}")
        raise typer.Exit(1)

    console.print()
    if not Confirm.ask(f"[bold]Iniciar transcrição de {len(audio_files)} arquivo(s)?[/bold]", default=True, console=console):
        console.print("[yellow]Cancelado.[/yellow]")
        raise typer.Exit(0)

    console.print()
    console.print("Transcrevendo via AssemblyAI...")

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

    all_results = transcribe_batch(audio_files, config, on_result=on_result)

    run_id = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    output_dir = config.output_dir / config.input_dir.name / run_id
    output_dir.mkdir(parents=True, exist_ok=True)

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
    """Lista todos os idiomas suportados pelo AssemblyAI."""
    table = Table(title="Idiomas suportados")
    table.add_column("Código", style="cyan", width=8)
    table.add_column("Idioma")
    for code, name in SUPPORTED_LANGUAGES.items():
        table.add_row(code, name)
    console.print(table)


@config_app.command("show")
def config_show() -> None:
    """Exibe a configuração atual resolvida."""
    try:
        config = load_config()
    except Exception as e:
        console.print(f"[red]Erro:[/red] {e}")
        raise typer.Exit(1)
    _show_config_panel(config)


if __name__ == "__main__":
    app()
