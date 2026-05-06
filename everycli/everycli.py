"""
EveryCLI — entry point.
As thin as possible: wire dependencies, boot, run.
"""

from pathlib import Path
import typer
from rich.console import Console
from rich.prompt import Prompt, Confirm
import yaml

from everycli.core.search_engine import SearchEngine
from everycli.core.add_engine import AddEngine
from everycli.infra.os_resolver import OSResolver
from everycli.infra.yaml_loader import YamlLoader
from everycli.infra.yaml_writer import YamlWriter
from everycli.infra.tfidf_matcher import TFIDFMatcher
from everycli.infra.rich_formatter import RichFormatter
from everycli.infra.shell_runner import ShellRunner
from everycli.infra.clipboard_copy import ClipboardCopy

app = typer.Typer(add_completion=False, help="Find the exact CLI command you need.")
console = Console()

DATA_DIR = Path(__file__).parent / "data" / "commands"
ENVIRONMENTS = ["git", "linux", "docker", "npm", "ssh", "other"]


def _build_search_engine() -> SearchEngine:
    engine = SearchEngine(
        loader=YamlLoader(DATA_DIR),
        matcher=TFIDFMatcher(),
        os_resolver=OSResolver(),
    )
    engine.boot()
    return engine


# ── search ────────────────────────────────────────────────────────────────────

@app.command()
def search(
    query: str = typer.Argument(..., help="Ce que tu veux faire, en langage naturel."),
    top: int = typer.Option(1, "--top", "-t", help="Nombre de résultats."),
    error: str = typer.Option(None, "--error", "-e", help="Message d'erreur à diagnostiquer."),
    env: str = typer.Option(None, "--env", help="Filtrer par environnement."),
    copy: bool = typer.Option(False, "--copy", "-c", help="Copier la commande dans le presse-papier."),
    run: bool = typer.Option(False, "--run", "-r", help="Exécuter la commande directement."),
):
    """Trouve la commande CLI dont tu as besoin."""
    engine = _build_search_engine()
    formatter = RichFormatter()
    results = engine.search(query, top_k=top)

    if env:
        results = [r for r in results if env.lower() in r.scenario.tags]

    if not results:
        console.print("\n[yellow]Aucun résultat trouvé.[/yellow] Essaie d'autres mots-clés.")
        raise typer.Exit(1)

    for result in results:
        formatter.format(result)

        if error:
            formatter.format_error_hint(error, result)

        if copy:
            clipboard = ClipboardCopy()
            success = clipboard.copy(result.resolved_command)
            if success:
                console.print("  [bold green]✔ Copié dans le presse-papier[/bold green]")
            else:
                console.print(
                    "  [yellow]⚠ Impossible de copier.[/yellow] "
                    "Installe xclip (Linux) : sudo apt install xclip"
                )

        if run:
            console.print(f"\n  [dim]Exécution de :[/dim] [cyan]{result.resolved_command}[/cyan]\n")
            confirmed = Confirm.ask("  Confirmes-tu l'exécution ?")
            if confirmed:
                runner = ShellRunner()
                code, output = runner.run(result.resolved_command)
                if output:
                    console.print(f"\n[dim]{output}[/dim]")
                if code == 0:
                    console.print("\n  [bold green]✔ Commande exécutée avec succès[/bold green]")
                else:
                    console.print(f"\n  [bold red]✖ Erreur (code {code})[/bold red]")
                    formatter.format_error_hint(output, result)

    console.print()


# ── add ───────────────────────────────────────────────────────────────────────

@app.command()
def add():
    """Ajouter un nouveau scénario à la base de données."""
    console.print("\n[bold cyan]✦ Ajouter un scénario[/bold cyan]\n")

    env = Prompt.ask("  Environnement", choices=ENVIRONMENTS, default="git")
    description = Prompt.ask("  Ce que ça fait (en français naturel)")
    tags_raw = Prompt.ask("  Tags (séparés par des virgules)")
    tags = [t.strip() for t in tags_raw.split(",")]
    linux_cmd = Prompt.ask("  Commande Linux/macOS")
    windows_cmd = Prompt.ask("  Commande Windows", default=linux_cmd)
    explanation = Prompt.ask("  Explication courte")
    warning = Prompt.ask("  Warning (optionnel, Entrée pour ignorer)", default="")

    console.print()
    if not Confirm.ask("  Tout semble bon, on enregistre ?"):
        console.print("[yellow]Annulé.[/yellow]")
        raise typer.Exit(0)

    engine = AddEngine(writer=YamlWriter(DATA_DIR))
    scenario = engine.add(
        environment=env,
        description=description,
        tags=tags,
        linux_command=linux_cmd,
        windows_command=windows_cmd,
        explanation=explanation,
        warning=warning,
    )

    console.print(
        f"\n[bold green]✔ Scénario ajouté[/bold green] → [cyan]{scenario.id}[/cyan]\n"
    )


# ── list ──────────────────────────────────────────────────────────────────────

@app.command(name="list")
def list_scenarios(
    env: str = typer.Option(None, "--env", help="Filtrer par environnement."),
):
    """Lister tous les scénarios disponibles."""
    loader = YamlLoader(DATA_DIR)
    scenarios = loader.load_all()

    if env:
        scenarios = [s for s in scenarios if env.lower() in s.tags]

    if not scenarios:
        console.print("[yellow]Aucun scénario trouvé.[/yellow]")
        raise typer.Exit(0)

    console.print(f"\n[bold cyan]✦ {len(scenarios)} scénarios disponibles[/bold cyan]\n")

    current_env = None
    for scenario in scenarios:
        env_tag = scenario.tags[0] if scenario.tags else "other"
        if env_tag != current_env:
            current_env = env_tag
            console.print(f"  [bold white]{current_env.upper()}[/bold white]")
        console.print(f"    [dim]•[/dim] {scenario.description}")

    console.print()


# ── export ────────────────────────────────────────────────────────────────────

@app.command()
def export(
    output: Path = typer.Option(
        Path("everycli_export.yaml"),
        "--output", "-o",
        help="Fichier de destination.",
    ),
    env: str = typer.Option(None, "--env", help="Exporter uniquement un environnement."),
):
    """Exporter la base de scénarios pour la partager."""
    loader = YamlLoader(DATA_DIR)
    scenarios = loader.load_all()

    if env:
        scenarios = [s for s in scenarios if env.lower() in s.tags]

    if not scenarios:
        console.print("[yellow]Aucun scénario à exporter.[/yellow]")
        raise typer.Exit(0)

    entries = []
    for s in scenarios:
        entry: dict = {
            "id": s.id,
            "description": s.description,
            "tags": s.tags,
            "commands": {
                "linux": s.command.linux,
                "windows": s.command.windows,
            },
            "explanation": s.explanation,
        }
        if s.warning:
            entry["warning"] = s.warning
        if s.error_hints:
            entry["errors"] = [
                {"trigger": h.trigger, "cause": h.cause, "fix": h.fix}
                for h in s.error_hints
            ]
        entries.append(entry)

    output.write_text(
        yaml.dump(entries, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

    console.print(
        f"\n[bold green]✔ Export terminé[/bold green] → "
        f"[cyan]{output}[/cyan] "
        f"([white]{len(entries)} scénarios[/white])\n"
    )


def main():
    app()


if __name__ == "__main__":
    main()