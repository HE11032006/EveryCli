# Référence technique

Ce document détaille les paramètres de configuration, la structure des données et le fonctionnement interne d'EveryCli.

> Architecture actuelle (branche `reverie-hacks-2026`) : daemon et client 100% Rust + ONNX Runtime. Voir [CHANGELOG.md](../CHANGELOG.md).

## Variables d'environnement

Utilisées par le client (`everycli-rs`) ET le daemon (`everycli-daemon`) — les deux doivent voir les mêmes valeurs pour fonctionner ensemble correctement.

| Variable | Description | Valeur par défaut |
| :--- | :--- | :--- |
| `EVERYCLI_PORT` | Port TCP de communication client/daemon. | `51821` |
| `EVERYCLI_DATA_DIR` | Dossier du corpus intégré (YAML). | `../everycli/data/commands` (relatif au dossier de lancement du daemon) |
| `EVERYCLI_USER_DATA_DIR` | Dossier des commandes personnalisées (`everycli add`). | `~/.everycli/commands` (`%USERPROFILE%\.everycli\commands` sous Windows) |
| `EVERYCLI_MODEL_DIR` | Dossier contenant `model.onnx` + `tokenizer.json`. | `onnx-bench/models/everycli-minilm-ft` |
| `EVERYCLI_ONNXRUNTIME_DYLIB` | Chemin vers `onnxruntime.dll`/`.so`. | `onnx-bench/runtime/onnxruntime.dll` (ou `.so` selon l'OS) |

Ces valeurs par défaut sont pensées pour un lancement en développement depuis `rust/`. Une installation via `install.ps1`/`install.sh` les définit explicitement (variables d'environnement persistantes côté client, `Environment=` dans l'unit systemd ou clé de Registre côté service Windows).

## Structure des fichiers de données (YAML)

Les commandes sont stockées dans `everycli/data/commands/*.yaml` (corpus intégré) ou `~/.everycli/commands/*.yaml` (commandes personnalisées, écrites par `everycli add`). Le **nom du fichier détermine le namespace** de chaque scénario qu'il contient. Chaque commande suit ce schéma :

```yaml
- id: identifiant_unique
  description: Ce que fait la commande (utilisé pour la recherche lexicale + sémantique)
  tags: [liste, de, mots, cles]
  commands:
    linux: "commande bash"
    windows: "commande powershell"
    macos: "commande zsh" # optionnel
  explanation: Détails supplémentaires sur le fonctionnement.
  warning: (Optionnel) Alertes de sécurité ou risques.
```

## Fonctionnement du daemon

Le daemon (`everycli-daemon`) est un serveur TCP.
- **Socket** : écoute sur `127.0.0.1` (localhost), thread par connexion.
- **Protocole** : une ligne de JSON par requête/réponse (`\n`-terminated). Actions supportées : `search`, `ping`, `reload`.
- **Cycle de vie** :
  - Au démarrage : charge le runtime ONNX, le modèle sémantique, puis le corpus (avec cache disque des embeddings, invalidé par hash de contenu du modèle + du corpus, pas par date de fichier).
  - Reste actif jusqu'à un arrêt explicite — pas de fichier PID : sur Windows, géré via le Service Control Manager (`sc.exe query/stop`) ou en tuant le processus (`Get-Process everycli-daemon`) ; sur Linux, via `systemctl --user stop everycli-daemon`.
  - `reload` recalcule le corpus + les embeddings à chaud, sans redémarrer le process (utilisé par `everycli add`/`remove`).

## Localisation des fichiers (binaires Rust)

Le daemon et le client sont des exécutables natifs — pas de répertoire temporaire d'extraction (contrairement à l'ancien flux PyInstaller). Les chemins du modèle/runtime/corpus sont résolus via les variables d'environnement ci-dessus, généralement pointées vers le dossier d'installation (`%LOCALAPPDATA%\EveryCli` sous Windows, `~/.local/share/everycli` sous Linux).

Le client cherche aussi le daemon **à côté de son propre exécutable** (même dossier `bin/`) pour l'auto-découverte/auto-lancement — voir `rust/everycli-core/src/daemon.rs`, `SIBLING_DAEMON_NAMES`.
