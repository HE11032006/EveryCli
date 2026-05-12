# Référence technique

Ce document détaille les paramètres de configuration, la structure des données et le fonctionnement interne d'EveryCli.

## Variables d'environnement
EveryCli peut être configuré via les variables d'environnement suivantes :

| Variable | Description | Valeur par défaut |
| :--- | :--- | :--- |
| `EVERYCLI_PORT` | Port utilisé pour la communication Socket entre le client et le daemon. | `51821` |
| `EVERYCLI_LOG_LEVEL` | Niveau de verbosité des logs (`DEBUG`, `INFO`, `ERROR`). | `INFO` |

## Structure des fichiers de données (YAML)
Les commandes sont stockées dans `everycli/data/commands/*.yaml`. Chaque commande suit ce schéma :

```yaml
- id: identifiant_unique
  description: Ce que fait la commande (utilisé pour la recherche sémantique)
  tags: [liste, de, mots, clés]
  commands:
    linux: "commande bash"
    windows: "commande powershell"
  explanation: Détails supplémentaires sur le fonctionnement.
  warning: (Optionnel) Alertes de sécurité ou risques.
```

## Fonctionnement du Daemon
Le daemon est un serveur TCP minimaliste.
- **Socket** : Il écoute sur `127.0.0.1` (localhost).
- **Protocole** : Échange de messages JSON suivis d'un caractère `\n`.
- **Cycle de vie** :
    - Au démarrage, il charge le modèle Sentence-Transformers en mémoire RAM.
    - Il reste actif jusqu'à ce qu'il reçoive une commande `--stop` ou un signal `SIGTERM`.
    - Le fichier PID est stocké dans `~/.everycli/daemon.pid`.

## Localisation des fichiers (Binaire)
Quand EveryCli est compilé avec PyInstaller :
- **`sys._MEIPASS`** : Répertoire temporaire contenant les ressources embarquées.
- **`models/`** : Contient les poids du modèle sémantique.
- **`everycli/data/commands/`** : Contient les fichiers YAML des commandes.
