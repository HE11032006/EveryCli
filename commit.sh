#!/bin/bash

# Commit 1
git add everycli/infra/hybrid_matcher.py
git commit -m "perf: optimisation des seuils hybrid_matcher"

# Commit 2
git add everycli/infra/semantic_matcher.py
git commit -m "perf: cache des embeddings pour semantic_matcher"

# Commit 3
git add everycli/infra/tfidf_matcher.py
git commit -m "perf: ajustement des seuils tfidf_matcher"

# Commit 4
git add everycli/everycli.py
git commit -m "perf: déplacement du spinner dans everycli.py"

# Commit 5
git add everycli/infra/daemon.py
git commit -m "feat: ajout du serveur daemon TCP"

# Commit 6
git add everycli/infra/daemon_runner.py
git commit -m "feat: ajout du runner pour le daemon"

# Commit 7
git add everycli/infra/daemon_client.py
git commit -m "feat: ajout du client daemon avec fallback"

# Commit 8
git add everycli/everycli.py everycli/core/command_runner.py
git commit -m "feat: intégration des commandes daemon dans le CLI"

# Commit 9
git add everycli/core/search_engine.py everycli/core/interfaces.py
git commit -m "feat: intégration du daemon dans le moteur de recherche"

# Commit 10
git add everycli/core/models.py
git commit -m "feat: ajout des types DaemonResult et DaemonError"

# Commit 11
git add everycli/core/add_engine.py everycli/infra/yaml_writer.py
git commit -m "feat: notification du daemon après ajout de scénario"

# Commit 12
git add everycli/infra/yaml_loader.py
git commit -m "refactor: adaptation du yaml_loader pour le daemon"

# Commit 13
git add everycli/infra/os_resolver.py
git commit -m "refactor: adaptation de l'os_resolver pour le daemon"

# Commit 14
git add everycli/infra/rich_formatter.py everycli/infra/clipboard_copy.py
git commit -m "refactor: adaptation du rich_formatter et clipboard"

# Commit 15
git add everycli/infra/shell_runner.py
git commit -m "refactor: adaptation du shell_runner"

# Commit 16
git add tests/test_search_engine.py tests/test_models_and_interface.py
git commit -m "test: mise à jour des tests du moteur de recherche"

# Commit 17
git add tests/test_clipboard_copy.py tests/test_os_resolver.py tests/test_rich_formatter.py tests/test_shell_runner.py tests/test_tfidf_matcher.py tests/test_yaml_loader.py everycli/infra/test_add_engine.py everycli/infra/test_yaml_writer.py
git commit -m "test: mise à jour des tests d'infrastructure"

# Commit 18
git add everycli/data/commands/bash_command.yaml everycli/data/commands/composer.yaml everycli/data/commands/docker.yaml everycli/data/commands/docker_compose.yaml everycli/data/commands/git.yaml everycli/data/commands/linux.yaml
git commit -m "chore: mise à jour des fichiers YAML de commandes"

# Commit 19
git add everycli/__init__.py everycli/core/__init__.py everycli/data/__init__.py everycli/infra/__init__.py
git commit -m "chore: mise à jour des exports des packages"

# Commit 20
git add pyproject.toml
git commit -m "chore: ajout des dépendances daemon dans pyproject.toml"

echo "✅ 20 commits terminés avec succès"
