[🇬🇧 English](README.md) | 🇫🇷 Français

# 🚀 EveryCli

**Ne cherche plus tes commandes, décris-les.**

EveryCli est un assistant en ligne de commande intelligent qui utilise l'IA pour trouver instantanément la commande exacte dont tu as besoin, même si tu n'en connais pas la syntaxe.

EveryCli inclut désormais **Sentinel** : un planificateur de commandes en mode "revue avant exécution". Il transforme une intention en une commande ancrée dans le corpus, un niveau de risque, et des vérifications à faire avant d'exécuter quoi que ce soit. Il n'exécute jamais une commande à ta place.

![License](https://img.shields.io/github/license/HE11032006/EveryCli)
![Build Status](https://img.shields.io/github/actions/workflow/status/HE11032006/EveryCli/build.yml)

## 🚀 Avant / Après : Reverie Hacks 2026

> Voir [CHANGELOG.md](CHANGELOG.md) pour le détail complet. Statuts marqués "en cours" vérifiés partiellement seulement.

| Aspect | Avant (v1.1.1) | Après (branche `reverie-hacks-2026`) |
|---|---|---|
| Architecture du daemon | Python + PyInstaller, hang non résolu au démarrage sur Windows | 100% Rust + ONNX Runtime, aucun hang observé, démarrage ~1.6s |
| Vitesse d'inférence | ~21.6ms/requête | ~12.5ms/requête (mesuré, single-thread) |
| Installation Windows | Téléchargement manuel, renommage d'exe, config PATH manuelle | `install.ps1` en une commande, vérifié de bout en bout |
| Installation Linux | Manuelle | `install.sh` écrit, vérification en cours (WSL) |
| Installation macOS | Manuelle | Pas encore commencé |
| Persistance du daemon | Lancement manuel, bloque le terminal, ne survit pas à un reboot | Démarre automatiquement à l'ouverture de session, détaché |
| Commandes personnalisées | Aucune | `everycli add`, jamais écrasées par une mise à jour |
| Désambiguïsation | Question bloquante forcée | Affichage informatif, l'utilisateur choisit en lisant |
| Qualité du ranking | Non mesurée objectivement | 87.9% sur `confusion_set.yaml` (66 requêtes), reproductible |

---

## Sommaire

- [Démarrage](#️-démarrage)
- [Vue d'ensemble](#-vue-densemble)
- [Structure du dépôt](#structure-du-dépôt)
- [Statut & feuille de route](#️-statut--feuille-de-route)
- [Contribuer](#-contribuer)
- [Licence](#-licence)

---

## ✈️ Démarrage

> **Note (branche `reverie-hacks-2026`)** : le daemon d'EveryCli est passé d'une architecture Python/PyInstaller à une architecture native Rust + ONNX Runtime — voir [CHANGELOG.md](CHANGELOG.md) pour le pourquoi et le détail. Aucune release GitHub publique ne distribue encore ces nouveaux binaires, donc pour l'instant les scripts d'installation fonctionnent depuis un build local. Le flux de téléchargement Full/Lite/Rust plus bas décrit encore la release précédente (`v1.1.1`).

### 🪟 Installation (Windows) — vérifiée de bout en bout

```powershell
cd rust
cargo build --release -p everycli-rs -p everycli-daemon
cd ..
.\scripts\windows\stage-release.ps1
.\install.ps1 -LocalSource "dist\windows"
```

Ça installe EveryCli dans `%LOCALAPPDATA%\EveryCli`, l'ajoute à ton PATH utilisateur, et démarre le daemon automatiquement à chaque ouverture de session (via le dossier Démarrage de Windows — aucun droit admin nécessaire). Ouvre un **nouveau** terminal et lance :

```powershell
everycli search "comment annuler mon dernier commit"
```

### 🐧 Installation (Linux) — écrite, vérification en cours (WSL)

```bash
cd rust
cargo build --release -p everycli-rs -p everycli-daemon
cd ..
./scripts/linux/stage-release.sh
./install.sh --local-source dist/linux
```

La persistance est gérée par un service `systemd --user`, installé et activé automatiquement.

### 🍎 macOS

Pas encore commencé.

### Ajouter tes propres commandes

```bash
everycli add
```

Te guide à travers quelques prompts (catégorie, description, commande, explication, tags/avertissement optionnels) et écrit le résultat dans `~/.everycli/commands` (`%USERPROFILE%\.everycli\commands` sous Windows) — un dossier séparé du corpus intégré, donc tes commandes perso ne sont jamais écrasées par une mise à jour.

### 📦 Ancienne release Python (v1.1.1 et antérieures)

Trois versions étaient disponibles pour chaque système d'exploitation sur la page [Releases](https://github.com/HE11032006/EveryCli/releases) :

- **Version Full** (~300Mo) : **prête à l'emploi.** Inclut le modèle IA. Parfaite pour un usage hors-ligne ou un premier lancement rapide.
- **Version Lite** (~50Mo) : **légère.** Télécharge automatiquement le modèle IA (~400Mo) à la première recherche. Recommandée avec une bonne connexion internet.
- **Version Rust** (`everycli-rs-*` + `everycli-data.zip`, quelques Mo au total) : **démarrage le plus rapide, pas de Python.** Binaire natif, sans dépendance, recherche lexicale instantanée. Passe automatiquement en recherche sémantique complète si un daemon Full/Lite tourne en local. Voir [`rust/README.md`](rust/README.md) pour l'usage.

1. Télécharge la version qui correspond à ton besoin.
2. (Optionnel) Configuration pour un accès facile :

   #### 🐧 Linux / 🍎 macOS
   1. Télécharge `everycli-linux-full` (le daemon).
   2. Place le wrapper `bin/everycli` dans ton PATH.
   ```bash
   chmod +x everycli-linux-full bin/everycli
   sudo ln -s $(pwd)/everycli-linux-full /usr/local/bin/everycli-daemon
   sudo ln -s $(pwd)/bin/everycli /usr/local/bin/everycli

   # Démarre le daemon une fois
   everycli-daemon --start

   # Cherche instantanément !
   everycli "git commit"
   ```

   #### 🪟 Windows
   - Place `everycli-windows-full.exe` et `everycli.ps1` dans un dossier.
   - Renomme l'exe en `everycli-daemon.exe`.
   - Ajoute le dossier à ton **PATH**.
   - Lance : `everycli search "git commit"`

3. Consulte notre [Guide d'installation détaillé](docs/tutorial_installation.md) pour plus d'infos (décrit le flux Python de la v1.1.1).

### 🛠️ Installation (Source, Python — Sentinel uniquement)

Sentinel (le planificateur de sécurité basé sur un LLM, voir plus bas) reste basé sur Python, séparé du chemin de recherche rapide en Rust. Si tu veux le construire/y contribuer :

1. Clone le dépôt : `git clone https://github.com/HE11032006/EveryCli.git`.
2. Va à la racine : `cd EveryCli`.
3. Installe les dépendances : `pip install -r requirements.txt`.

### Utilisation en local

Recherche rapide (Rust, recommandé — voir les sections d'installation ci-dessus) :
```bash
everycli search "comment annuler mon dernier commit"
```

Sentinel, le planificateur de sécurité basé sur un LLM, reste basé sur Python, séparé du chemin de recherche rapide en Rust — planifie une commande en sécurité avant de la coller dans un terminal :
```bash
python -m everycli.everycli plan "supprimer les images Docker inutilisées en sécurité"
```

Avec `OPENAI_API_KEY` configuré, Sentinel utilise GPT-5.6 pour sélectionner et
expliquer une des commandes déjà récupérées depuis le corpus local. Utilise
`--local` pour forcer le planificateur de sécurité entièrement hors-ligne.

### Mesurer la qualité de la recherche

`eval/confusion_set.yaml` est un ensemble bilingue de requêtes en langage
naturel pour Git, Docker, Compose, npm, Composer, SSH, Python et Linux. Il ne
stocke volontairement aucun score fictif : mesure le corpus actuel avant une
démo ou une release.

```bash
python tools/evaluate_confusion.py
```

Utilise `--fail-under 80` seulement après avoir convenu d'une base de
référence pour l'environnement cible. `--matcher lexical` est disponible pour
diagnostiquer la base BM25 seule ; le défaut est le même matcher hybride
qu'utilise EveryCli. L'évaluateur n'exécute jamais une commande retournée.

Pour une démo portable sans réseau, définis `EVERYCLI_OFFLINE=1` ; EveryCli
utilise un modèle sémantique en cache quand disponible, et retombe sinon sur
des signaux lexicaux locaux plutôt que d'attendre des tentatives de
téléchargement.

> [!TIP]
> Pour profiter de temps de réponse sous 50ms, EveryCli utilise un Daemon en arrière-plan. La première recherche le démarre automatiquement.

---

## 📖 Vue d'ensemble

EveryCli est construit pour la vitesse et l'intelligence. Presque tout notre contenu est généré depuis des fichiers YAML que tu trouveras dans le dossier `everycli/data/commands/`.

Si tu veux contribuer une modification ou un ajout à la doc, lis notre [Guide de contribution](CONTRIBUTING.md).

### Sources de documentation

Pour approfondir, consulte nos fichiers de documentation dédiés :
- 📖 [Tutoriel : Installation](docs/tutorial_installation.md)
- 🛠️ [Comment construire & tester](docs/how_to_build.md)
- 🏗️ [Explication de l'architecture](docs/explanation_architecture.md)
- ⚙️ [Référence de configuration](docs/reference_config.md)
- 🛡️ [Build Week / Sentinel](docs/BUILD_WEEK.md)

### Structure du dépôt

Voici un aperçu haut niveau des fichiers et dossiers pertinents.

```text
EveryCli/
├── .github/             # Workflows CI/CD (build automatique des binaires)
├── bin/                 # Wrappers shell rapides (Linux/macOS)
├── docs/                # Documentation détaillée façon Diátaxis
├── everycli/
│   ├── core/            # Logique métier (Modèles, moteur de recherche, coordinateur)
│   ├── data/
│   │   └── commands/    # Base de scénarios YAML (corpus intégré)
│   └── infra/           # Infra du planificateur Sentinel (basé LLM, Python)
├── rust/
│   ├── everycli-core/   # Chargement du corpus + recherche lexicale (Rust, lib partagée)
│   ├── everycli-inference/ # Encodeur sémantique (ONNX Runtime)
│   ├── everycli-daemon/ # Daemon TCP (remplace daemon_server.py)
│   └── everycli-rs/     # Client CLI (search, add)
├── scripts/
│   ├── windows/         # stage-release.ps1 (packaging pour install.ps1)
│   └── linux/           # stage-release.sh (packaging pour install.sh)
├── install.ps1          # Installeur Windows
├── install.sh           # Installeur Linux
├── everycli.ps1         # Wrapper PowerShell Windows (ancien flux Python)
├── requirements.txt     # Dépendances Python (planificateur Sentinel)
└── README.md            # Tu es ici
```

---

## 🗺️ Statut & feuille de route

### ✅ Fonctionnalités terminées
*   **Daemon natif Rust + ONNX** : remplace le daemon Python/PyInstaller, plus de blocage au démarrage, inférence ~1.7x plus rapide (voir [CHANGELOG.md](CHANGELOG.md)).
*   **`everycli add`** : ajoute tes propres commandes, stockées séparément du corpus intégré, jamais écrasées par une mise à jour.
*   **Calibrage de la précision sémantique** : scoring hybride lexical + sémantique (modèle ONNX local, fine-tuné sur le corpus EveryCli), 87.9% sur le benchmark `confusion_set.yaml`.
*   **Désambiguïsation interactive (O4)** : quand l'écart sémantique entre les meilleurs résultats est trop faible, EveryCli montre les candidats proches au lieu de deviner à ta place.
*   **Intégration astuces & dépannage** : l'interface de recherche affiche distinctement des astuces contextuelles (💡) et des conseils de dépannage (🔧), pour prévenir les erreurs avant qu'elles n'arrivent.
*   **Intégration shell fluide** : support de Bash (`everycli.bash`), Zsh (`everycli.zsh` avec widget ZLE), et PowerShell (`everycli.ps1`) pour un flux de travail sans friction.
*   **Installeurs en une commande** : `install.ps1` (Windows, vérifié de bout en bout) et `install.sh` (Linux, en cours) configurent le PATH et un daemon en arrière-plan automatiquement.
*   **Planificateur Sentinel** : planification et vérification sécurisées propulsées par des LLM pour des actions complexes multi-étapes (Python, séparé du chemin de recherche rapide en Rust).

### 🚧 Prévu / améliorations futures
*   **Installeur macOS** : pas encore commencé.
*   **Boost par historique** : remonter les commandes selon l'historique d'exécution de l'utilisateur pour s'adapter aux habitudes individuelles.
*   **Index ANN (Approximate Nearest Neighbors)** : migrer de la recherche par similarité exhaustive vers un index ANN (ex : FAISS) pour maintenir des latences sous 10ms même avec un corpus de 10 000+ commandes.
*   **Quantification du modèle** : le modèle ONNX est actuellement distribué en float32 (~470Mo) — une quantification int8 réduirait la taille d'installation.
*   **Service Windows natif** : actuellement le daemon démarre via le dossier Démarrage de Windows (fonctionne, aucune permission nécessaire) ; un vrai service Windows (conforme SCM, via le crate `windows-service`) serait plus robuste pour un redémarrage automatique en cas de crash.

---

## 👏 Contribuer

Toutes les contributions sont bienvenues ! Que ce soit pour ajouter une nouvelle commande ou améliorer le matcher IA.
Consulte notre [Guide de contribution](CONTRIBUTING.md) pour plus de détails.

---

## 📄 Licence

EveryCli est sous licence **MIT**.
La documentation est sous licence Creative Commons.

---
*Fait avec ❤️ pour les développeurs qui détestent mémoriser des flags.*
