"""
EveryCLI — entry point.
As thin as possible: wire dependencies, boot, run.
"""

from pathlib import Path
import typer
from rich.console import Console
from rich.prompt import Confirm, Prompt

# On garde uniquement les imports légers pour le mode client
from everycli.infra import daemon_client
from everycli.infra.daemon_client import DaemonResult, DaemonError

import sys
import os
import os

app = typer.Typer(add_completion=False, help="Find the exact CLI command you need.")
console = Console()

# Support PyInstaller (chemins gelés)
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    DATA_DIR = Path(sys._MEIPASS) / "everycli" / "data" / "commands"
else:
    DATA_DIR = Path(__file__).parent / "data" / "commands"


def available_environments(data_dir: Path = DATA_DIR) -> list[str]:
    """Return the corpus namespaces accepted by the interactive add flow.

    The choices follow the YAML files, so adding a new ecosystem cannot leave
    the CLI menu stale (as happened with composer and docker_compose).
    """
    namespaces = sorted(path.stem for path in data_dir.glob("*.yaml"))
    return [*namespaces, "other"]

def _get_history():
    from everycli.core.history import History
    return History()

# history_manager sera chargé à la demande
_history_manager = None

def _get_history_manager():
    global _history_manager
    if _history_manager is None:
        from everycli.core.history import History
        _history_manager = History()
    return _history_manager


# La logique de recherche (local/daemon) a été déplacée dans core.coordinator.SearchCoordinator


# ── search ────────────────────────────────────────────────────────────────────

@app.command()
def search(
    query: str = typer.Argument(None, help="Ce que tu veux faire, en langage naturel."),
    top: int = typer.Option(1, "--top", "-t", help="Nombre de résultats."),
    error: str = typer.Option(None, "--error", "-e", help="Message d'erreur à diagnostiquer."),
    env: str = typer.Option(None, "--env", help="Filtrer par environnement."),
    copy: bool = typer.Option(False, "--copy", "-c", help="Copier la commande dans le presse-papier."),
    run: bool = typer.Option(False, "--run", "-r", help="Exécuter la commande directement."),
    interactive: bool = typer.Option(False, "--interactive", "-i", help="Mode interactif avec sélection."),
    shell: bool = typer.Option(
        False,
        "--shell",
        "-s",
        help="Demande confirmation puis imprime la commande retenue sur stdout.",
    ),
    no_daemon: bool = typer.Option(False, "--no-daemon", help="Forcer le mode direct (sans daemon)."),
):
    """Trouve la commande CLI dont tu as besoin."""
    global console
    # In shell mode, stdout is a tiny protocol: the confirmed command only.
    # Rich output and prompts stay visible on stderr for the human user.
    if shell:
        console = Console(stderr=True)
        if interactive:
            console.print("[yellow]-s ne se combine pas avec -i.[/yellow]")
            raise typer.Exit(2)
        if run or copy:
            console.print("[yellow]-s ne se combine pas avec --run ou --copy.[/yellow]")
            raise typer.Exit(2)
        if error:
            console.print("[yellow]-s ne se combine pas avec --error.[/yellow]")
            raise typer.Exit(2)
        if top != 1:
            console.print("[yellow]-s retourne une seule commande ; utilise --top 1.[/yellow]")
            raise typer.Exit(2)
        if not query:
            console.print("[yellow]Le mode -s necessite une requete explicite.[/yellow]")
            raise typer.Exit(2)


    # ── Gestion de l'historique si pas de query ───────────────────────────────
    if not query:
        history_manager = _get_history_manager()
        recent = history_manager.load()
        if not recent:
            console.print("\n[yellow]Aucun historique.[/yellow] Tape une recherche pour commencer !")
            raise typer.Exit(0)
        
        from pick import pick
        # On prépare les labels pour pick : "Ma recherche -> Description de la commande"
        options = []
        for e in recent:
            label = e["query"]
            if e["description"]:
                label += f" [dim]({e['description']})[/dim]"
            options.append(label)

        title = "✦ Recherches récentes (Espace pour choisir, Esc pour quitter) :"
        _, index = pick(options, title, indicator="→")
        if index is None: raise typer.Exit(0)
        query = recent[index]["query"]
        console.print(f"\n[bold cyan]✦ Recherche :[/bold cyan] {query}")

    # ── Résolution des résultats (via le Coordinateur) ────────────────────────
    from everycli.core.coordinator import SearchCoordinator
    coordinator = SearchCoordinator(console, str(DATA_DIR))
    
    # En mode interactif, ou pour la désambiguïsation (O4), on demande plus de résultats
    search_top = 10 if interactive else max(top, 3)
    results = coordinator.execute_search(query, top_k=search_top, no_daemon=no_daemon)

    # ── Filtrage environnement ────────────────────────────────────────────────
    if env:
        results = [r for r in results if env.lower() in r.scenario.tags]

    if not results:
        console.print("\n[yellow]Aucun résultat trouvé.[/yellow] Essaie d'autres mots-clés.")
        raise typer.Exit(1)

    # ── Mode Interactif & O4 ──────────────────────────────────────────────────
    final_results = results
    if interactive and len(results) > 1:
        from pick import pick
        options = [f"{r.scenario.description} [dim]({r.resolved_command})[/dim]" for r in results]
        title = f"✦ Résultats pour '{query}' (Espace pour choisir) :"
        _, index = pick(options, title, indicator="→")
        final_results = [results[index]]
    elif not interactive and len(results) > 1:
        # Désambiguïsation automatique (O4)
        score_diff = results[0].score - results[1].score
        # Si le modèle hésite vraiment (écart < 0.05 ou 5%)
        if score_diff < 0.05 and results[0].score > 0:
            console.print(f"\n[bold yellow]🤔 J'hésite entre deux commandes très proches.[/bold yellow]")
            console.print("Quelle est ton intention ?\n")
            
            console.print(f"  [bold cyan]1.[/bold cyan] {results[0].scenario.description} [dim]({results[0].scenario.namespace or 'general'})[/dim]")
            console.print(f"  [dim]> {results[0].resolved_command}[/dim]\n")
            
            console.print(f"  [bold cyan]2.[/bold cyan] {results[1].scenario.description} [dim]({results[1].scenario.namespace or 'general'})[/dim]")
            console.print(f"  [dim]> {results[1].resolved_command}[/dim]\n")
            
            choice = Prompt.ask("Choix", choices=["1", "2"], default="1", console=console)
            if choice == "2":
                final_results = [results[1]] + [results[0]] + results[2:]

    # ── Affichage & Actions ───────────────────────────────────────────────────
    from everycli.infra.rich_formatter import RichFormatter
    formatter = RichFormatter(console)
    
    # On sauvegarde le premier résultat dans l'historique pour la prochaine fois
    if final_results:
        best = final_results[0]
        _get_history_manager().save(query, description=best.scenario.description, command=best.resolved_command)

    for result in final_results[:top]:
        formatter.format(result)

        if error:
            formatter.format_error_hint(error, result)

        if result.scenario.kind == "command":
            if copy:
                _copy_to_clipboard(result.resolved_command)

            if run:
                _run_command(result.resolved_command, result, formatter)

    if shell and final_results and final_results[0].scenario.kind == "command":
        selected = final_results[0]
        # Dans un pipe, on écrit juste la commande sur stdout
        sys.stdout.write(selected.resolved_command)
        sys.stdout.flush()
        return

    console.print()


@app.command()
def plan(
    query: str = typer.Argument(..., help="Objectif décrit en langage naturel."),
    top: int = typer.Option(5, "--top", "-t", min=1, max=10, help="Nombre de candidats examinés."),
    local: bool = typer.Option(False, "--local", help="Ne pas utiliser GPT-5.6, même si une clé est configurée."),
):
    """Préparer une commande vérifiable avant de la copier ou de l'exécuter.

    Cette commande ne lance jamais de shell. GPT-5.6, lorsqu'il est configuré,
    explique et départage les candidats issus du corpus; la commande finale et
    son niveau de risque restent ancrés dans le corpus local.
    """
    from everycli.core.coordinator import SearchCoordinator
    from everycli.core.command_plan import LocalCommandPlanner
    from everycli.infra.openai_command_planner import OpenAICommandPlanner
    from rich.panel import Panel

    coordinator = SearchCoordinator(console, str(DATA_DIR))
    results = coordinator.execute_search(query, top_k=top)
    if not results:
        console.print("[yellow]Aucune commande candidate trouvée.[/yellow]")
        raise typer.Exit(1)

    planner_name = "local"
    if not local and OpenAICommandPlanner.available():
        try:
            command_plan = OpenAICommandPlanner().plan(query, results)
            planner_name = command_plan.planner
        except Exception as error:
            console.print(f"[yellow]Planificateur IA indisponible : {error}. Basculement local.[/yellow]")
            command_plan = LocalCommandPlanner().plan(results[0])
    else:
        command_plan = LocalCommandPlanner().plan(results[0])

    checks = "\n".join(f"  • {check}" for check in command_plan.preflight_checks)
    confirmation = "Oui — relis et confirme avant exécution." if command_plan.confirmation_required else "Non, mais relis la commande."
    content = (
        f"[bold]{command_plan.title}[/bold]\n\n"
        f"[cyan]{command_plan.command}[/cyan]\n\n"
        f"{command_plan.explanation}\n\n"
        f"[bold]Risque :[/bold] {command_plan.risk.value.upper()} — {command_plan.risk_reason}\n"
        f"[bold]Confirmation requise :[/bold] {confirmation}\n\n"
        f"[bold]À vérifier avant de continuer :[/bold]\n{checks}\n\n"
        f"[dim]Source : {command_plan.source_id} · Planificateur : {planner_name} · Aucune commande n'a été exécutée.[/dim]"
    )
    console.print(Panel(content, title="EveryCli Sentinel", border_style="cyan"))


def _copy_to_clipboard(command: str):
    from everycli.infra.clipboard_copy import ClipboardCopy
    clipboard = ClipboardCopy()
    success = clipboard.copy(command)
    if success:
        console.print("  [bold green]✔ Copié dans le presse-papier[/bold green]")
    else:
        console.print("  [yellow]⚠ Impossible de copier.[/yellow] Installe xclip.")

def _run_command(command: str, result, formatter):
    from rich.prompt import Confirm
    console.print(f"\n  [dim]Exécution de :[/dim] [cyan]{command}[/cyan]\n")
    if Confirm.ask("  Confirmes-tu l'exécution ?"):
        from everycli.infra.shell_runner import ShellRunner
        runner = ShellRunner()
        code, output = runner.run(command)
        if output:
            console.print(f"\n[dim]{output}[/dim]")
        if code == 0:
            console.print("\n  [bold green]✔ Commande exécutée avec succès[/bold green]")
        else:
            console.print(f"\n  [bold red]✖ Erreur (code {code})[/bold red]")
            formatter.format_error_hint(output, result)


# Les fonctions de mapping daemon -> results ont été déplacées dans le Coordinateur


# ── daemon ────────────────────────────────────────────────────────────────────

@app.command()
def daemon(
    start: bool = typer.Option(False, "--start", help="Démarrer le daemon."),
    stop:  bool = typer.Option(False, "--stop",  help="Arrêter le daemon."),
    status: bool = typer.Option(False, "--status", help="Afficher l'état du daemon."),
    logs:  bool = typer.Option(False, "--logs",  help="Afficher les logs du daemon."),
    install: bool = typer.Option(False, "--install", help="Installer en tant que service systemd (Linux)."),
    debug: bool = typer.Option(False, "--debug", help="Démarrer en mode verbeux."),
):
    """Gérer le daemon EveryCLI (start / stop / status / logs / install)."""
    from everycli.infra.daemon import (
        start_daemon, stop_daemon, status_daemon, show_logs, install_systemd_service
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
    elif install:
        install_systemd_service()
    else:
        console.print(
            "Usage : everycli daemon [--start | --stop | --status | --logs | --install]\n"
            "Ajoute --debug avec --start pour les logs verbeux."
        )


# ── add ───────────────────────────────────────────────────────────────────────

@app.command()
def add():
    """Ajouter un nouveau scénario à la base de données."""
    from rich.prompt import Prompt, Confirm
    console.print("\n[bold cyan]✦ Ajouter un scénario[/bold cyan]\n")

    env = Prompt.ask("  Environnement", choices=available_environments(), default="git")
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

    from everycli.core.add_engine import AddEngine
    from everycli.infra.yaml_writer import YamlWriter
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

    console.print(f"\n[bold green]✔ Scénario ajouté[/bold green] → [cyan]{scenario.id}[/cyan]\n")
    if daemon_client.send_reload():
        console.print("  [dim]→ Daemon notifié (base rechargée)[/dim]")


# ── list ──────────────────────────────────────────────────────────────────────

@app.command(name="list")
def list_scenarios(
    env: str = typer.Option(None, "--env", help="Filtrer par environnement."),
):
    """Lister tous les scénarios disponibles."""
    from everycli.infra.yaml_loader import YamlLoader
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
    output: Path = typer.Option(Path("everycli_export.yaml"), "--output", "-o", help="Destination."),
    env: str = typer.Option(None, "--env", help="Filtrer par environnement."),
):
    """Exporter la base de scénarios."""
    from everycli.infra.yaml_loader import YamlLoader
    loader = YamlLoader(DATA_DIR)
    scenarios = loader.load_all()

    if env:
        scenarios = [s for s in scenarios if env.lower() in s.tags]

    if not scenarios:
        console.print("[yellow]Aucun scénario à exporter.[/yellow]")
        raise typer.Exit(0)

    entries = []
    for s in scenarios:
        entry = {
            "id": s.id, "description": s.description, "tags": s.tags,
            "commands": {"linux": s.command.linux, "windows": s.command.windows},
            "explanation": s.explanation,
        }
        if s.warning: entry["warning"] = s.warning
        if s.error_hints:
            entry["errors"] = [{"trigger": h.trigger, "cause": h.cause, "fix": h.fix} for h in s.error_hints]
        entries.append(entry)

    import yaml
    output.write_text(yaml.dump(entries, allow_unicode=True, sort_keys=False), encoding="utf-8")
    console.print(f"\n[bold green]✔ Export terminé[/bold green] → [cyan]{output}[/cyan] ([white]{len(entries)} scénarios[/white])\n")


# ── import ────────────────────────────────────────────────────────────────────

@app.command(name="import")
def import_yaml(
    path: Path = typer.Argument(..., help="Fichier YAML à importer."),
):
    """Importer un fichier YAML externe."""
    if not path.exists():
        console.print(f"[bold red]✖ Erreur :[/bold red] Le fichier {path} n'existe pas.")
        raise typer.Exit(1)
    
    try:
        import yaml
        content = yaml.safe_load(path.read_text())
        if not isinstance(content, list): raise ValueError("Format liste attendu.")
    except Exception as e:
        console.print(f"[bold red]✖ Erreur :[/bold red] {e}")
        raise typer.Exit(1)

    dest = DATA_DIR / path.name
    import shutil
    shutil.copy(path, dest)
    console.print(f"\n[bold green]✔ Importation réussie[/bold green] → [cyan]{dest.name}[/cyan]\n")
    if daemon_client.send_reload():
        console.print("  [dim]→ Daemon notifié (base rechargée)[/dim]")


# ── update ────────────────────────────────────────────────────────────────────

@app.command()
def update():
    """Mettre à jour la base via Git."""
    console.print("\n[bold cyan]✦ Mise à jour des scénarios[/bold cyan]\n")
    import subprocess
    try:
        result = subprocess.run(["git", "pull"], cwd=str(DATA_DIR.parent.parent), capture_output=True, text=True)
        if result.returncode == 0:
            if "Already up to date" in result.stdout:
                console.print("  [green]Base déjà à jour.[/green]")
            else:
                console.print("  [bold green]✔ Mise à jour effectuée.[/bold green]")
                if daemon_client.send_reload(): console.print("  [dim]→ Daemon notifié[/dim]")
        else:
            console.print(f"  [yellow]⚠ Échec :[/yellow] {result.stderr}")
    except Exception as e:
        console.print(f"  [bold red]✖ Erreur :[/bold red] {e}")
    console.print()


# ── completion ────────────────────────────────────────────────────────────────

@app.command()
def install():
    """Installer l'auto-complétion."""
    console.print("\n[bold cyan]✦ Installation de l'auto-complétion[/bold cyan]\n")
    console.print("Exécute :\n")
    console.print("[bold white]ZSH :[/bold white]  everycli --install-completion zsh")
    console.print("[bold white]BASH :[/bold white] everycli --install-completion bash")
    console.print("\nEnsuite : [cyan]source ~/.zshrc[/cyan] (ou ~/.bashrc)\n")


# ── history ───────────────────────────────────────────────────────────────────

@app.command()
def history(
    clear: bool = typer.Option(False, "--clear", help="Vider l'historique.")
):
    """Gérer l'historique des recherches."""
    history_manager = _get_history_manager()
    if clear:
        history_manager.clear()
        console.print("[bold green]✔ Historique vidé.[/bold green]")
    else:
        recent = history_manager.load()
        if not recent:
            console.print("[yellow]L'historique est vide.[/yellow]")
        else:
            from rich.table import Table
            from rich.box import ROUNDED

            table = Table(title="\n✦ Historique des recherches", box=ROUNDED, header_style="bold magenta")
            table.add_column("Recherche", style="cyan", no_wrap=True)
            table.add_column("Description de la commande", style="white")
            table.add_column("Commande associée", style="bold green")

            for e in recent[:15]: # On affiche les 15 derniers
                table.add_row(
                    e["query"], 
                    e["description"] or "[dim]N/A[/dim]", 
                    e["command"] or "[dim]N/A[/dim]"
                )
            
            console.print(table)
            console.print("\n[dim]Conseil : Tape 'everycli search' sans argument pour naviguer dans l'historique.[/dim]\n")


def main():
    # Intercepted before Typer/Click ever sees argv: this is how the daemon
    # respawns itself (see `daemon_client._respawn_command`). It must not
    # touch Rich (`console`/`app`) at all — a fully detached respawned
    # process (no console, stdio redirected to NUL) crashes the moment Rich
    # tries to probe terminal capabilities, whereas `start_daemon()`'s plain
    # `print()` calls are safe.
    from everycli.infra.daemon_client import DAEMON_RUNNER_ARG
    if len(sys.argv) > 1 and sys.argv[1] == DAEMON_RUNNER_ARG:
        from everycli.infra.daemon import start_daemon
        start_daemon()
        return

    from everycli.core.exceptions import EveryCliError
    try:
        app()
    except EveryCliError as e:
        console.print(f"\n[bold red]✖ Erreur EveryCli :[/bold red] {e}")
        sys.exit(1)
    except Exception as e:
        if os.environ.get("EVERYCLI_DEBUG"):
            raise e
        console.print(f"\n[bold red]✖ Une erreur inattendue est survenue :[/bold red] {e}")
        console.print("[dim]Utilise EVERYCLI_DEBUG=1 pour voir les détails.[/dim]")
        sys.exit(1)


if __name__ == "__main__":
    main()
