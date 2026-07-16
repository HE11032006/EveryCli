"""
validate_corpus.py — validateur strict, indépendant du loader applicatif.

Le loader (`everycli/infra/yaml_loader.py`) est volontairement TOLÉRANT : une
entrée cassée est logguée et ignorée, pour que l'app ne plante jamais chez un
utilisateur. Ce validateur, lui, fait l'inverse : il rapporte TOUTES les
erreurs du corpus d'un coup, pour être utilisé :
  - en local avant de merger un lot généré (par toi ou par Codex),
  - en CI, pour empêcher un corpus cassé d'être mergé,
  - comme `test_schema_validation.py` (O6 du cahier des charges).

Usage :
    python3 tools/validate_corpus.py [chemin_du_dossier]
    (par défaut : everycli/data/commands)

Exit code 0 si tout est valide, 1 sinon (utilisable en CI / pre-commit).
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml


class ValidationError(Exception):
    """Levée si on veut faire échouer un pipeline sur un corpus invalide."""


# Champs obligatoires par type d'entrée. `command` est un cas spécial :
# il faut "command" OU "commands", géré séparément ci-dessous.
_REQUIRED_FIELDS = {
    "command": ["id", "description", "tags", "explanation"],
    "tip": ["id", "description", "tags", "content"],
    "troubleshooting": ["id", "description", "tags", "causes", "solutions"],
    "reference": ["id", "description", "tags", "content"],
}
_KNOWN_KINDS = set(_REQUIRED_FIELDS)


def _extract_entries(data):
    """Même logique récursive que YamlLoader — supporte listes plates et
    catégories imbriquées (bash_command.yaml, linux.yaml, docker_compose.yaml)."""
    if isinstance(data, list):
        for item in data:
            yield from _extract_entries(item)
    elif isinstance(data, dict):
        if "id" in data and "description" in data:
            yield data
        else:
            for value in data.values():
                yield from _extract_entries(value)


def _validate_entry(entry: dict, source_file: str) -> list[str]:
    errors = []
    entry_id = entry.get("id", "<sans id>")
    kind = entry.get("kind", "command")

    if kind not in _KNOWN_KINDS:
        errors.append(
            f"{source_file} :: {entry_id} : kind={kind!r} inconnu "
            f"(attendu: {sorted(_KNOWN_KINDS)})"
        )
        return errors  # pas la peine d'aller plus loin, on ne sait pas quoi valider

    for field in _REQUIRED_FIELDS[kind]:
        if field not in entry or entry[field] in (None, "", []):
            errors.append(
                f"{source_file} :: {entry_id} (kind={kind}) : champ obligatoire "
                f"manquant ou vide : {field!r}"
            )

    if kind == "command" and "command" not in entry and "commands" not in entry:
        errors.append(
            f"{source_file} :: {entry_id} (kind=command) : ni 'command' ni "
            f"'commands' présent — aucune commande à exécuter"
        )

    return errors


def validate_corpus(data_dir: Path) -> list[str]:
    """Valide tous les fichiers *.yaml d'un dossier. Retourne la liste de
    TOUTES les erreurs trouvées (liste vide = corpus valide)."""
    data_dir = Path(data_dir)
    errors: list[str] = []
    seen_ids: dict[str, str] = {}  # id -> premier fichier où on l'a vu

    for yaml_file in sorted(data_dir.glob("*.yaml")):
        raw = yaml_file.read_text(encoding="utf-8")
        try:
            data = yaml.safe_load(raw)
        except yaml.YAMLError as e:
            errors.append(f"{yaml_file.name} : YAML invalide — {e}")
            continue

        for entry in _extract_entries(data):
            errors.extend(_validate_entry(entry, yaml_file.name))

            entry_id = entry.get("id")
            if entry_id:
                if entry_id in seen_ids and seen_ids[entry_id] != yaml_file.name:
                    errors.append(
                        f"{yaml_file.name} :: id {entry_id!r} dupliqué "
                        f"(déjà présent dans {seen_ids[entry_id]})"
                    )
                else:
                    seen_ids[entry_id] = yaml_file.name

    return errors


def main() -> int:
    data_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("everycli/data/commands")
    errors = validate_corpus(data_dir)

    if not errors:
        # ASCII output keeps the command usable in legacy Windows consoles
        # configured with cp1252 as well as UTF-8 terminals and CI logs.
        print(f"OK: Corpus valide ({data_dir})")
        return 0

    print(f"ERROR: {len(errors)} erreur(s) trouvée(s) dans {data_dir} :\n")
    for e in errors:
        print(" -", e)
    return 1


if __name__ == "__main__":
    sys.exit(main())
