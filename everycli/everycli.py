"""
EveryCLI — entry point.
As thin as possible: wire dependencies, boot, run.
"""

from pathlib import Path
import typer

from everycli.core.search_engine import SearchEngine
from everycli.infra.os_resolver import OSResolver
from everycli.infra.yaml_loader import YamlLoader
from everycli.infra.tfidf_matcher import TFIDFMatcher
from everycli.infra.rich_formatter import RichFormatter
from rich.console import Console

app = typer.Typer(add_completion=False)
console = Console()

DATA_DIR = Path(__file__).parent / "data" / "commands"


def _build_engine() -> SearchEngine:
    """Wire all dependencies and return a booted SearchEngine."""
    engine = SearchEngine(
        loader=YamlLoader(DATA_DIR),
        matcher=TFIDFMatcher(),
        os_resolver=OSResolver(),
    )
    engine.boot()
    return engine


@app.command()
def search(
    query: str = typer.Argument(..., help="Ce que tu veux faire, en langage naturel."),
    top: int = typer.Option(1, "--top", "-t", help="Nombre de résultats à afficher."),
    error: str = typer.Option(None, "--error", "-e", help="Message d'erreur à diagnostiquer."),
):
    """
    Trouve la commande CLI dont tu as besoin.

    Exemple : everycli "modifier mon dernier commit"
    """
    engine = _build_engine()
    formatter = RichFormatter()
    results = engine.search(query, top_k=top)

    if not results:
        console.print("\n[yellow]Aucun résultat trouvé.[/yellow] Essaie d'autres mots-clés.")
        raise typer.Exit(1)

    for result in results:
        formatter.format(result)

        if error:
            formatter.format_error_hint(error, result)

    console.print()


def main():
    app()


if __name__ == "__main__":
    main()