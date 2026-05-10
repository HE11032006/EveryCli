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
from everycli.infra.hybrid_matcher import HybridMatcher
from everycli.infra.rich_formatter import RichFormatter
from everycli.infra.shell_runner import ShellRunner
from everycli.infra.clipboard_copy import ClipboardCopy
from everycli.infra import daemon_client
from everycli.infra.daemon_client import DaemonResult, DaemonError

app = typer.Typer(add_completion=False, help="Find the exact CLI command you need.")
console = Console()

DATA_DIR     = Path(__file__).parent / "data" / "commands"
ENVIRONMENTS = ["git", "linux", "docker", "npm", "ssh", "other"]


# ── Fallback local (sans daemon) ──────────────────────────────────────────────

def _search_local(query: str, top_k: int) -> list:
    """Recherche directe sans daemon — lente mais toujours fonctionnelle."""
    matcher = HybridMatcher(semantic_weight=0.6)
    engine = SearchEngine(
        loader=YamlLoader(DATA_DIR),
        matcher=matcher,
        os_resolver=OSResolver(),
    )
    with console.status("[dim]Chargement...[/dim]", spinner="dots"):
        engine.boot()
        return engine.search(query, top_k=top_k)


# ── search ────────────────────────────────────────────────────────────────────

@app.command()
def search(
    query: str = typer.Argument(..., help="Ce que tu veux faire, en langage naturel."),
    top: int = typer.Option(1, "--top", "-t", help="Nombre de résultats."),
    error: str = typer.Option(None, "--error", "-e", help="Message d'erreur à diagnostiquer."),
    env: str = typer.Option(None, "--env", help="Filtrer par environnement."),
    copy: bool = typer.Option(False, "--copy", "-c", help="Copier la commande dans le presse-papier."),
    run: bool = typer.Option(False, "--run", "-r", help="Exécuter la commande directement."),
    no_daemon: bool = typer.Option(False, "--no-daemon", help="Forcer le mode direct (sans daemon)."),
):
    """Trouve la commande CLI dont tu as besoin."""

    # ── Résolution des résultats (daemon ou fallback local) ───────────────────
    results = []
    used_daemon = False

    if not no_daemon:
        daemon_resp = daemon_client.search(query, top_k=top)

        if isinstance(daemon_resp, DaemonResult):
            used_daemon = True
            # Convertir les dicts en objets compatibles RichFormatter
            results = _daemon_results_to_search_results(daemon_resp.results)
        else:
            # DaemonError — warning + fallback silencieux
            console.print(
                f"  [yellow]⚠ Daemon indisponible ({daemon_resp.reason})"
                f" — mode direct activé.[/yellow]"
            )
            results = _search_local(query, top_k=top)
    else:
        results = _search_local(query, top_k=top)

    # ── Filtrage environnement ────────────────────────────────────────────────
    if env:
        results = [r for r in results if env.lower() in r.scenario.tags]

    if not results:
        console.print("\n[yellow]Aucun résultat trouvé.[/yellow] Essaie d'autres mots-clés.")
        raise typer.Exit(1)

    # ── Affichage ─────────────────────────────────────────────────────────────
    formatter = RichFormatter()
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


def _daemon_results_to_search_results(raw: list[dict]) -> list:
    """
    Convertit les dicts JSON du daemon en SearchResult compatibles
    avec RichFormatter — sans recharger le moteur.
    """
    from everycli.core.models import (
        Scenario, Command, SearchResult, OS
    )
    from everycli.infra.os_resolver import OSResolver

    current_os = OSResolver().resolve()
    out = []
    for r in raw:
        cmd = Command(linux=r["command"], windows=r["command"], macos=r["command"])
        scenario = Scenario(
            id=r["id"],
            description=r["description"],
            tags=r.get("tags", []),
            command=cmd,
            explanation=r.get("explanation", ""),
            warning=r.get("warning", ""),
        )
        out.append(SearchResult(
            scenario=scenario,
            resolved_command=r["command"],
            score=r.get("score", 0.0),
        ))
    return out


# ── daemon ────────────────────────────────────────────────────────────────────

@app.command()
def daemon(
    start: bool = typer.Option(False, "--start", help="Démarrer le daemon."),
    stop:  bool = typer.Option(False, "--stop",  help="Arrêter le daemon."),
    status: bool = typer.Option(False, "--status", help="Afficher l'état du daemon."),
    logs:  bool = typer.Option(False, "--logs",  help="Afficher les logs du daemon."),
    debug: bool = typer.Option(False, "--debug", help="Démarrer en mode verbeux."),
):
    """Gérer le daemon EveryCLI (start / stop / status / logs)."""
    from everycli.infra.daemon import (
        start_daemon, stop_daemon, status_daemon, show_logs
    )

    if start:
        console.print("[dim]Démarrage du daemon EveryCLI...[/dim]")
        start_daemon(debug=debug)
    elif stop:
        stop_daemon()
    elif status:
        status_daemon()
    elif logs:
        show_logs()
    else:
        console.print(
            "Usage : everycli daemon [--start | --stop | --status | --logs]\n"
            "Ajoute --debug avec --start pour les logs verbeux."
        )


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

    # Notifie le daemon de recharger la base
    if daemon_client.send_reload():
        console.print("  [dim]→ Daemon notifié (base rechargée)[/dim]")


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
