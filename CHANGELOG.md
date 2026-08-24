# Changelog

Ce fichier consigne les changements techniques d’EveryCli par domaine. Il ne remplace pas l’historique Git chronologique et ne constitue pas un document de présentation.

## Unreleased — Reverie Hacks 2026

### Architecture et exécution

- Remplacement du daemon Python/PyInstaller du chemin de recherche rapide par un daemon natif Rust.
- Ajout du crate `everycli-inference` pour charger `model.onnx` et exécuter l’encodage sémantique avec ONNX Runtime.
- Ajout du crate `everycli-daemon`, serveur TCP local sur `127.0.0.1:51821`.
- Conservation du protocole JSON ligne par ligne pour les actions `ping`, `search` et `reload`.
- Conservation d’un chemin de repli local lorsque le daemon n’est pas disponible.
- Chargement dynamique du runtime natif : `onnxruntime.dll` sous Windows et `libonnxruntime.so` sous Linux.
- Ajout d’un cache disque des embeddings du corpus, invalidé lorsque le contenu du modèle ou du corpus change.
- Maintien de Sentinel comme composant Python séparé pour la planification de commandes avec un LLM.

### Modèle et recherche

- Publication de l’artefact ONNX de production dans `Michelhe/everycli-minilm-ft-boosted-onnx`.
- Verrouillage dans la CI de la révision Hugging Face et des SHA-256 de `model.onnx` et `tokenizer.json`.
- Mise en place d’un score hybride combinant lexical, sémantique et bonus de namespace.
- Remplacement du filtrage dur par namespace par un bonus additif afin de ne pas exclure des paraphrases ou des commandes personnalisées.
- Ajout de `--debug` pour afficher les composantes du score et le score hybride.
- Ajout d’un seuil minimal de pertinence à `0.50` afin de rejeter les requêtes manifestement hors sujet.
- Ajout et utilisation du benchmark bilingue `eval/confusion_set.yaml` pour mesurer le ranking ; résultat enregistré : 58 requêtes réussies sur 66, soit 87,9 %.
- Ajout de tests de seuil couvrant une requête faussement positive et une requête valide.

### Commandes personnalisées

- Ajout de `everycli add` pour créer une commande personnelle depuis le terminal.
- Ajout de `everycli list` et `everycli remove` pour gérer le corpus personnel.
- Stockage des commandes personnalisées dans `~/.everycli/commands` sous Linux et `%USERPROFILE%\.everycli\commands` sous Windows.
- Fusion des commandes personnelles avec le corpus intégré côté daemon et côté recherche locale.
- Rechargement à chaud du daemon après ajout ou suppression.
- Conservation des commandes et de la configuration personnelles lors d’une désinstallation normale.

### Interface terminal et localisation

- Limitation effective de la sélection interactive par `--top`.
- Ajout du nombre de candidats dans le prompt interactif.
- Affichage du namespace et de l’identifiant pour distinguer des résultats proches.
- Affichage séparé des explications, commandes et avertissements dans le rendu terminal.
- Clarification du résultat ciblé par `--copy` et `--run` lorsqu’il existe plusieurs candidats.
- Remplacement du message générique de reload par une indication de la cause : connexion, envoi, timeout, JSON invalide ou refus du daemon.
- Ajout et validation de la localisation anglaise et française des messages principaux.
- Respect des sorties non interactives et de `NO_COLOR` lorsque la couleur ne convient pas au terminal.

### Parsing du corpus

- Support des scalaires YAML en bloc avec `|` dans le parseur utilisé par le corpus.
- Ajout d’un test couvrant une explication multi-ligne issue du corpus réel.
- Conservation de la résolution de commande par plateforme et du namespace dérivé du nom de fichier.

### Installation et distribution

- Ajout d’un installeur Linux `install.sh` prenant en charge :
  - un bundle extrait à côté du script ;
  - un dossier local avec `--local-source` ;
  - le téléchargement d’une release GitHub avec `--version` ou `latest`.
- Vérification SHA-256 de l’archive téléchargée avant installation Linux.
- Installation Linux dans `~/.local/share/everycli`, liens dans `~/.local/bin` et service `systemd --user`.
- Attente active de la réponse `ping` du daemon Linux, avec délai étendu pour le premier chargement du modèle.
- Ajout d’un désinstalleur Linux qui arrête et retire le service, supprime les liens et conserve `~/.everycli` par défaut.
- Ajout de l’option explicite `--remove-user-commands` pour supprimer les données personnelles Linux.
- Alignement de `install.ps1` sur les bundles Windows complets et sur la vérification SHA-256.
- Correction de la séparation entre le dossier utilisateur et le compte de service Windows avec `EVERYCLI_USER_DATA_DIR`.
- Validation de l’installation Windows depuis un staging complet : client, daemon, modèle, tokenizer, runtime et corpus.
- Validation de l’installation Linux sous WSL : service actif, port local, recherche sémantique, configuration et désinstallation conservant la configuration utilisateur.

### CI/CD et sécurité de la chaîne de build

- Ajout d’un job CI Ubuntu qui télécharge les artefacts ONNX validés depuis Hugging Face.
- Compilation séparée sur `ubuntu-latest`, `windows-latest` et `macos-latest`.
- Téléchargement du runtime natif officiel adapté à chaque job.
- Correction de l’extraction Linux : l’archive ONNX Runtime fournit `libonnxruntime.so` comme lien symbolique ; le packaging copie le fichier réel versionné vers le nom attendu.
- Ajout de `fail-fast: false` dans la matrice afin qu’un échec Ubuntu n’annule pas le diagnostic Windows ou macOS.
- Correction de l’appel `cargo audit`, exécuté depuis `rust/` où se trouve le `Cargo.lock`.
- Production d’archives complètes Linux et Windows avec le modèle, le tokenizer, le runtime, le corpus, les binaires et les scripts.
- Publication de `SHA256SUMS` pour les archives de release à partir d’un tag `v*`.
- Exclusion des fichiers de secrets et des artefacts locaux non destinés au dépôt.

### Validation et mesures

- `cargo test -p everycli-rs` validé avec 26 tests.
- `cargo test -p everycli-core` validé avec 25 tests, dont les tests de résolution du daemon et du parseur YAML.
- `cargo test -p everycli-daemon` validé avec 2 tests de seuil de pertinence.
- Mesure Windows du flux daemon : moyenne observée de 382,8 ms sur cinq essais.
- Mesure Windows du repli local : moyenne observée de 33,2 ms sur cinq essais.
- Les mesures de latence dépendent de la machine et distinguent le flux complet du daemon de la recherche locale.

### Limites connues

- macOS compile et passe les tests CI, mais son installeur, son runtime natif et son archive publique n’ont pas encore été validés de bout en bout.
- Le modèle ONNX est distribué en float32 et pèse environ 470 Mo.
- Les poids du ranking sont calibrés empiriquement sur le benchmark actuel, et non sur une évaluation exhaustive de toutes les intentions.
- Le daemon local est destiné à un usage personnel et n’est pas conçu comme un service multi-utilisateur.
- `cargo fmt --all -- --check` reste bloqué par des différences de formatage préexistantes dans d’autres crates du workspace ; aucune règle de formatage globale n’est présentée comme validée dans ce changelog.
