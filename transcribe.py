from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import questionary
import typer
from questionary import Style as QStyle
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table

from src.config import SUPPORTED_LANGUAGES, AppConfig, load_config
from src.exporters import get_exporters
from src.exporters.json import result_to_dict
from src.models import TranscriptionStatus
from src.transcriber import collect_audio_files, transcribe_batch

# ── App setup ────────────────────────────────────────────────────────────────

app = typer.Typer(
    help="Transcriptum — batch WhatsApp audio transcription",
    add_completion=False,
)
config_app = typer.Typer(help="Config commands")
app.add_typer(config_app, name="config")

console = Console()

# ── Questionary style ────────────────────────────────────────────────────────

_Q_STYLE = QStyle([
    ("qmark",       "fg:cyan bold"),
    ("question",    "bold"),
    ("answer",      "fg:cyan bold"),
    ("pointer",     "fg:cyan bold"),
    ("highlighted", "fg:cyan bold"),
    ("selected",    "fg:green"),
    ("separator",   "fg:gray"),
    ("instruction", "fg:gray italic"),
    ("text",        ""),
])

# ── Constants ────────────────────────────────────────────────────────────────

_ALL_FORMATS = ["md", "txt", "json", "docx", "pdf"]
_FORMAT_LABELS = {
    "md":   "md   — Markdown",
    "txt":  "txt  — Texto plano",
    "json": "json — JSON estruturado",
    "docx": "docx — Word (.docx)",
    "pdf":  "pdf  — PDF",
}
_EXTRAS = {
    "timestamps":           "Timestamps por palavra",
    "speaker_diarization":  "Diarização por speaker",
    "confidence_scores":    "Confiança por palavra",
}

# ── UI helpers ────────────────────────────────────────────────────────────────

def _clear() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def _config_panel(config: AppConfig, n_files: int | None = None) -> None:
    extras_on = [label for key, label in _EXTRAS.items() if getattr(config.extras, key)]
    extras_str = "[green]" + ", ".join(extras_on) + "[/green]" if extras_on else "[dim]nenhum[/dim]"

    dir_str = str(config.input_dir)
    if n_files is not None:
        dir_str += f"  [dim]({n_files} arquivos .ogg)[/dim]"

    t = Table(show_header=False, box=None, padding=(0, 2))
    t.add_column(style="dim", no_wrap=True)
    t.add_column()
    t.add_row("Pasta",    dir_str)
    t.add_row("Idioma",   f"[bold]{config.language}[/bold]  [dim]— {SUPPORTED_LANGUAGES.get(config.language, '')}[/dim]")
    t.add_row("Formatos", "[bold]" + ", ".join(config.formats) + "[/bold]")
    t.add_row("Extras",   extras_str)
    t.add_row("API Key",  "[green]● configurada[/green]" if config.api_key else "[red]● NÃO CONFIGURADA[/red]")

    console.print(Panel(t, title="[bold cyan]Transcriptum[/bold cyan]", border_style="cyan"))


# ── TUI menu ──────────────────────────────────────────────────────────────────

def _tui_menu(initial_config: AppConfig, initial_n_files: int | None) -> AppConfig | None:
    """
    Arrow-key menu loop. Returns the final AppConfig when user picks 'Iniciar',
    or None when user picks 'Sair'.
    """
    cur_input    = str(initial_config.input_dir)
    cur_language = initial_config.language
    cur_formats  = list(initial_config.formats)
    cur_extras   = {k: getattr(initial_config.extras, k) for k in _EXTRAS}
    cur_n_files  = initial_n_files

    def _rebuild() -> AppConfig:
        return load_config(overrides={
            "input_dir": Path(cur_input),
            "language":  cur_language,
            "formats":   cur_formats,
            "extras":    dict(cur_extras),
        })

    while True:
        _clear()
        try:
            cfg = _rebuild()
        except Exception as e:
            console.print(f"[red]Configuração inválida:[/red] {e}\n")
            cfg = initial_config

        _config_panel(cfg, cur_n_files)
        console.print()

        extras_on   = [v for k, v in _EXTRAS.items() if cur_extras[k]]
        extras_label = ", ".join(extras_on) if extras_on else "nenhum"
        fmt_label   = ", ".join(cur_formats) if cur_formats else "(nenhum)"
        n_label     = f"  ({cur_n_files} arquivos)" if cur_n_files else ""

        choices = [
            questionary.Separator("─── Configurações ───────────────────────────────"),
            questionary.Choice(f"  📁  Pasta de entrada    {cur_input}",                            value="input"),
            questionary.Choice(f"  🌍  Idioma              {cur_language} — {SUPPORTED_LANGUAGES.get(cur_language, '')}",  value="language"),
            questionary.Choice(f"  📄  Formatos            {fmt_label}",                            value="formats"),
            questionary.Choice(f"  ⚙   Extras              {extras_label}",                        value="extras"),
            questionary.Separator("─────────────────────────────────────────────────"),
            questionary.Choice(f"  ▶   Iniciar transcrição{n_label}",                              value="start"),
            questionary.Choice("  ✕   Sair",                                                        value="exit"),
        ]

        action = questionary.select(
            "Selecione uma opção  [↑↓ para navegar · Enter para selecionar]",
            choices=choices,
            style=_Q_STYLE,
            use_shortcuts=False,
        ).ask()

        if action is None or action == "exit":
            return None

        # ── Iniciar ──────────────────────────────────────────────────────────
        if action == "start":
            if not cur_formats:
                console.print("\n[red]Selecione ao menos um formato antes de iniciar.[/red]")
                questionary.press_any_key_to_continue("\n  Pressione qualquer tecla...").ask()
                continue
            return _rebuild()

        # ── Pasta de entrada ─────────────────────────────────────────────────
        if action == "input":
            val = questionary.text(
                "Pasta de entrada:",
                default=cur_input,
                style=_Q_STYLE,
            ).ask()
            if val is not None:
                cur_input = val.strip()
                try:
                    cur_n_files = len(collect_audio_files(Path(cur_input)))
                except Exception:
                    cur_n_files = None

        # ── Idioma ────────────────────────────────────────────────────────────
        elif action == "language":
            lang_choices = [
                questionary.Choice(f"{name}  ({code})", value=code)
                for code, name in SUPPORTED_LANGUAGES.items()
            ]
            val = questionary.select(
                "Idioma:",
                choices=lang_choices,
                default=cur_language,
                style=_Q_STYLE,
            ).ask()
            if val is not None:
                cur_language = val

        # ── Formatos ──────────────────────────────────────────────────────────
        elif action == "formats":
            fmt_choices = [
                questionary.Choice(_FORMAT_LABELS.get(f, f), value=f, checked=(f in cur_formats))
                for f in _ALL_FORMATS
            ]
            val = questionary.checkbox(
                "Formatos de saída  [Espaço para marcar · Enter para confirmar]:",
                choices=fmt_choices,
                style=_Q_STYLE,
            ).ask()
            if val is not None:
                cur_formats = val

        # ── Extras ────────────────────────────────────────────────────────────
        elif action == "extras":
            ext_choices = [
                questionary.Choice(label, value=key, checked=cur_extras[key])
                for key, label in _EXTRAS.items()
            ]
            val = questionary.checkbox(
                "Extras  [Espaço para marcar · Enter para confirmar]:",
                choices=ext_choices,
                style=_Q_STYLE,
            ).ask()
            if val is not None:
                cur_extras = {k: (k in val) for k in _EXTRAS}


# ── Progress-aware transcription ──────────────────────────────────────────────

def _transcribe_with_progress(audio_files, config) -> list:
    all_results = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]{task.description}"),
        BarColumn(bar_width=45),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        console=console,
        transient=False,
    ) as progress:
        task_id = progress.add_task("Transcrevendo", total=len(audio_files))

        def on_result(result):
            all_results.append(result)
            if result.status == TranscriptionStatus.COMPLETED:
                progress.console.print(
                    f"  [green]✓[/green] [dim]{result.id}[/dim] {result.audio_file.path.name}"
                    f"  [dim]{result.duration_str} · {result.confidence_pct}[/dim]"
                )
            else:
                progress.console.print(
                    f"  [red]✗[/red] [dim]{result.id}[/dim] {result.audio_file.path.name}"
                    f"  [red]{result.error}[/red]"
                )
            progress.advance(task_id)

        transcribe_batch(audio_files, config, on_result=on_result)

    return all_results


# ── Commands ──────────────────────────────────────────────────────────────────

@app.command()
def run(
    input:      Optional[str] = typer.Option(None,  "--input",  "-i", help="Pasta de entrada"),
    formats:    Optional[str] = typer.Option(None,  "--formats","-f", help="Formatos: md,txt,json,docx,pdf"),
    timestamps: bool          = typer.Option(False, "--timestamps",   help="Timestamps por palavra"),
    speakers:   bool          = typer.Option(False, "--speakers",     help="Diarização por speaker"),
    confidence: bool          = typer.Option(False, "--confidence",   help="Confiança por palavra"),
    yes:        bool          = typer.Option(False, "--yes", "-y",    help="Pular menu interativo"),
) -> None:
    """Transcreve todos os .ogg da pasta de entrada."""

    # CLI flag overrides
    flag_overrides: dict = {}
    if input:
        flag_overrides["input_dir"] = Path(input)
    if formats:
        flag_overrides["formats"] = [f.strip() for f in formats.split(",")]
    extras_flags: dict = {}
    if timestamps:
        extras_flags["timestamps"] = True
    if speakers:
        extras_flags["speaker_diarization"] = True
    if confidence:
        extras_flags["confidence_scores"] = True
    if extras_flags:
        flag_overrides["extras"] = extras_flags

    try:
        config = load_config(overrides=flag_overrides or None)
    except FileNotFoundError as e:
        console.print(f"[red]Erro:[/red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Erro de configuração:[/red] {e}")
        raise typer.Exit(1)

    if not config.api_key:
        console.print("[red]Erro:[/red] ASSEMBLYAI_API_KEY não configurada. Adicione ao arquivo .env.")
        raise typer.Exit(1)

    # ── Interactive TUI (default when no flags) ───────────────────────────────
    if not flag_overrides and not yes:
        try:
            n_files = len(collect_audio_files(config.input_dir))
        except Exception:
            n_files = None

        config = _tui_menu(config, n_files)
        if config is None:
            console.print("[dim]Saindo.[/dim]")
            raise typer.Exit(0)

    # ── Resolve audio files ───────────────────────────────────────────────────
    try:
        audio_files = collect_audio_files(config.input_dir)
    except (FileNotFoundError, ValueError) as e:
        console.print(f"[red]Erro:[/red] {e}")
        raise typer.Exit(1)

    # ── Run header ────────────────────────────────────────────────────────────
    _clear()
    console.rule("[bold cyan]Transcriptum[/bold cyan]")
    console.print(f"  Pasta:    {config.input_dir}  ({len(audio_files)} arquivos .ogg)")
    console.print(f"  Idioma:   {config.language}  — {SUPPORTED_LANGUAGES.get(config.language, '')}")
    console.print(f"  Formatos: {', '.join(config.formats)}")
    console.rule()
    console.print()

    # ── Transcription with live progress ─────────────────────────────────────
    all_results = _transcribe_with_progress(audio_files, config)

    # ── Persist outputs ───────────────────────────────────────────────────────
    run_id     = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    output_dir = config.output_dir / config.input_dir.name / run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    (output_dir / "transcriptions.json").write_text(
        json.dumps([result_to_dict(r) for r in all_results], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    console.print()
    console.rule()
    console.print("  Exportando outputs...")
    for exporter in get_exporters(config.formats):
        written = exporter.export(all_results, output_dir)
        ind  = sum(1 for p in written if p.parent.name == "individual")
        full = next(p for p in written if "FULL" in p.name)
        console.print(f"  [green]✓[/green] {ind} individuais + {full.name}")

    completed = sum(1 for r in all_results if r.status == TranscriptionStatus.COMPLETED)
    failed    = len(all_results) - completed

    console.rule()
    console.print(
        f"[bold green]Concluído[/bold green]"
        f"  •  {completed}/{len(all_results)} ok"
        f"  •  {output_dir}"
    )
    if failed:
        console.print(f"[yellow]Atenção:[/yellow] {failed} arquivo(s) falharam — verifique transcriptions.json")


@app.command()
def languages() -> None:
    """Lista todos os idiomas suportados."""
    t = Table(title="Idiomas suportados pelo AssemblyAI")
    t.add_column("Código", style="cyan", width=8)
    t.add_column("Idioma")
    for code, name in SUPPORTED_LANGUAGES.items():
        t.add_row(code, name)
    console.print(t)


@config_app.command("show")
def config_show() -> None:
    """Exibe a configuração atual resolvida."""
    try:
        config = load_config()
        try:
            n_files = len(collect_audio_files(config.input_dir))
        except Exception:
            n_files = None
        _config_panel(config, n_files)
    except Exception as e:
        console.print(f"[red]Erro:[/red] {e}")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
