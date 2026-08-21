# Tutoriel : Installer et utiliser EveryCli

> **Architecture actuelle (branche `reverie-hacks-2026`)** : EveryCli est passé d'un daemon Python (PyInstaller) à un daemon 100% Rust + ONNX Runtime — voir [CHANGELOG.md](../CHANGELOG.md). Ce tutoriel décrit le nouveau flux. Aucune release GitHub publique ne distribue encore ces binaires ; en attendant, installe depuis les sources (ci-dessous).

## 1. Compiler depuis les sources

```bash
git clone https://github.com/HE11032006/EveryCli.git
cd EveryCli/rust
cargo build --release -p everycli-rs -p everycli-daemon
```

Il te faut aussi le modèle ONNX et le runtime ONNX Runtime — voir [`rust/onnx-bench/README`](../rust/onnx-bench) (ou le [CONTRIBUTING.md](../CONTRIBUTING.md), section "Working on the ONNX export tooling") pour les exporter/télécharger.

## 2. Installer

### 🪟 Windows

```powershell
cd EveryCli
.\scripts\windows\stage-release.ps1
.\install.ps1 -LocalSource "dist\windows"
```

Par défaut, ça installe EveryCli comme un vrai **service Windows** (redémarre automatiquement en cas de crash, démarre même avant connexion) — une invite d'élévation (UAC) apparaît une fois, à accepter. Si tu préfères éviter toute invite admin, ajoute `-NoService` : EveryCli démarre alors via le dossier Démarrage de Windows à la place (aucune permission spéciale, mais pas de redémarrage automatique).

```powershell
.\install.ps1 -LocalSource "dist\windows" -NoService
```

### 🐧 Linux

```bash
cd EveryCli
./scripts/linux/stage-release.sh
./install.sh --local-source dist/linux
```

La persistance est gérée par un service `systemd --user`, installé et activé automatiquement.

### 🍎 macOS

Pas encore disponible.

## 3. Utiliser

Ouvre un **nouveau** terminal (le PATH mis à jour ne s'applique qu'aux nouvelles fenêtres) :

```bash
everycli search "comment annuler mon dernier commit"
```

Le daemon tourne déjà en arrière-plan depuis l'installation — pas besoin de le démarrer manuellement. S'il n'est pas encore prêt (premier démarrage, calcul des embeddings du corpus), `everycli` retombe automatiquement sur une recherche locale le temps qu'il finisse de charger.

### Options utiles

```bash
everycli search "requête" --top 3        # plusieurs résultats
everycli search "requête" --interactive  # sélection au clavier
everycli search "requête" --copy         # copie la commande dans le presse-papier
everycli search "requête" --run          # exécute après confirmation
everycli search "requête" --json         # sortie machine-readable
everycli search "requête" --no-daemon    # force la recherche locale (sans le daemon)
```

### Ajouter tes propres commandes

```bash
everycli add       # ajoute une commande via une série de prompts
everycli list       # liste tes commandes personnalisées
everycli remove     # en supprime une (sélection au clavier)
```

Stockées dans `~/.everycli/commands` (`%USERPROFILE%\.everycli\commands` sous Windows) — jamais écrasées par une mise à jour du corpus intégré.

## 4. Désinstaller

### Windows

```powershell
.\uninstall.ps1
```

Arrête et retire le service (ou le processus), nettoie le PATH, supprime le dossier d'installation. Tes commandes personnalisées (`~/.everycli`) sont conservées par défaut — ajoute `-RemoveUserCommands` pour tout supprimer.

### Linux

Pas encore de script dédié — voir [CHANGELOG.md](../CHANGELOG.md) pour le statut.

## 5. Ancienne version (Python, v1.1.1 et antérieures)

Si tu utilises encore une ancienne release (Full/Lite basée sur PyInstaller), voir l'historique du dépôt pour la version précédente de ce tutoriel — cette architecture est en cours de remplacement (voir [CHANGELOG.md](../CHANGELOG.md)).
