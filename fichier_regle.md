# EveryCli — Fichier de passation (mis à jour, session longue)

**Ce fichier remplace toute version précédente.** À coller en premier message à un autre assistant IA si la session en cours s'arrête (limite de tokens). Repo maintenant à `H:\Projet\EveryCli` (a été déplacé/recloné plusieurs fois pendant la session — vérifier le chemin réel avec `Filesystem:list_allowed_directories` si un connecteur filesystem est utilisé).

**La vraie source de vérité détaillée reste [`HACKATHON_PLAN.md`](HACKATHON_PLAN.md) — le lire en entier avant de continuer.** Ce fichier-ci est un résumé condensé + les règles de travail + les pièges déjà résolus (pour ne pas les redécouvrir).

---

## 1. Règles de travail (impératif)

- **Commits faits par l'utilisateur**, jamais par l'assistant. L'assistant propose message + commande, l'utilisateur exécute.
- **Commandes à résultat long** (build, test, cargo, pip, git log...) : données à l'utilisateur, jamais exécutées par l'assistant lui-même (l'assistant n'a pas de terminal sur la machine de l'utilisateur — seulement un accès fichiers en lecture/écriture via un connecteur `Filesystem` MCP).
- **Édition de fichiers directe autorisée** via le connecteur `Filesystem` (lecture/écriture/édition) — pas besoin de tout faire coller par l'utilisateur.
- **Ne cocher une case du plan qu'après vérification réelle** (build/test confirmé par l'utilisateur). Ne jamais présenter comme acquis ce qui n'a pas été testé.
- **Toujours vérifier avant de conclure une régression/un problème** — plusieurs fois cette session, une alarme initiale ("ça a régressé", "le travail est perdu") s'est révélée être une fausse piste après vérification (`git log`, mesures objectives). Mesurer avant de diagnostiquer.
- **Repo GitHub** : `https://github.com/HE11032006/EveryCli`, branche `reverie-hacks-2026`. Vérifié synchronisée avec `origin` à plusieurs reprises pendant la session (pas de commits perdus à ce jour).

## 2. Décision architecturale majeure (ne pas remettre en cause sans raison forte)

Le daemon Python (PyInstaller) a été entièrement remplacé par un daemon 100% Rust + ONNX Runtime, suite à un bug de hang au démarrage jamais résolu côté Python/Windows. Le protocole client-serveur (JSON ligne-par-ligne, TCP `127.0.0.1:51821`, actions `search`/`ping`/`reload`) est resté identique — le client `everycli-rs` n'a jamais eu besoin d'être réécrit pour cette migration, seulement étendu ensuite (`add`/`list`/`remove`, UI).

Sentinel (`everycli plan`, planificateur LLM-based) reste un composant **Python séparé**, non concerné par la migration.

## 3. Architecture actuelle des crates Rust (`rust/`)

- **`everycli-core`** : parsing du corpus YAML (parseur maison, PAS un vrai parseur YAML générique — indentation stricte, voir §6), recherche lexicale, `load_corpus_merged()` (fusionne corpus intégré + utilisateur), `filter_candidates()` (filtre dur, utilisé seulement par `search()` lexical pur), `candidates_for_platform()` (pas de filtre namespace, utilisé par le daemon), `explicit_namespace()` (public, détection de mot-clé d'écosystème).
- **`everycli-inference`** : `SemanticEncoder` (ONNX Runtime via crate `ort` 2.0.0-rc.13, feature `load-dynamic`), `init_runtime()`, `cosine_similarity()`.
- **`everycli-daemon`** : le serveur TCP. Double mode console/service Windows (`--service`, crate `windows-service`). Thread par connexion (`Arc<Mutex<DaemonState>>`). Score hybride = lexical (poids 0.45) + sémantique (poids 0.55) + bonus namespace (+0.2, additif, PAS un filtre). Cache disque des embeddings du corpus, clé = hash du texte réellement embeddé (description+tags×3+explication+commande×3) + hash de contenu échantillonné du fichier modèle (PAS sa date de modification — une simple copie de fichier change la date mais pas le contenu).
- **`everycli-rs`** : le client CLI. Sous-commandes `search`, `add`, `list`, `remove`. Couleurs via `owo-colors` (désactivées auto si non-terminal/`NO_COLOR`). Sélection interactive via `inquire` (flèches, pas de saisie de chiffre). Chargement du corpus local **paresseux** (seulement si repli nécessaire ou `--error`) — optimisation de latence importante, voir §5.
- **`rust/onnx-bench`** : crate de benchmark/export, pas du code de production.

## 4. Pièges déjà rencontrés et résolus (NE PAS redécouvrir)

1. `optimum` récent a scindé l'export ONNX dans `optimum-onnx` (package séparé).
2. Repo HF du modèle a `tokenizer_class: "TokenizersBackend"` (bug transformers v5) → patcher en `XLMRobertaTokenizerFast` (modèle = BERT multilingue + tokenizer SentencePiece XLM-R).
3. `optimum-cli export onnx` doit avoir `--library-name transformers` explicite (le défaut `sentence_transformers` plante).
4. `ort` n'a pas de version "stable" — `2.0.0-rc.13`+ est la version recommandée en prod malgré le suffixe `-rc`.
5. API `ort` 2.0-rc : pas d'`Environment` séparé, `try_extract_array` (pas `try_extract_tensor`), `session.run()` prend `&mut self`, `ort::inputs!` ne retourne pas un `Result`, `ort::Error<R>` pas toujours `Send`/`Sync` → `.map_err(|e| anyhow::anyhow!("{e}"))` explicite partout.
6. Conflit de liaison MSVC statique/dynamique en liant `ort` statiquement sous Windows → fix : feature `load-dynamic` (charge `onnxruntime.dll` au runtime, pas à la compilation). Télécharger le zip officiel `onnxruntime-win-x64-*` depuis les releases GitHub de `microsoft/onnxruntime`.
7. Version d'`ndarray` doit matcher celle qu'`ort` utilise en interne (`^0.17` pour `ort` 2.0.0-rc.13).
8. `Tensor::from_array()` prend possession de l'array — cloner avant si réutilisé après (ex: `attention_mask` pour le mean pooling).
9. **Filtrage dur par namespace AVANT le scoring hybride casse le principe même de la recherche sémantique** (et aurait cassé la découvrabilité des commandes `everycli add`). Un fallback par tags ajouté pendant le calibrage (`detect_namespace_by_tags`) causait une régression (77.3% au lieu de 87.9%) en excluant des scénarios pertinents par volume de correspondances faibles. **Fix** : namespace = bonus additif au score, jamais un filtre, sauf dans `search()` (repli lexical pur sans signal sémantique pour rattraper une exclusion à tort).
10. **`schtasks /create` peut échouer avec "Accès refusé"** sur certaines machines (restriction locale/de groupe) même sans lien avec les droits admin classiques — d'où l'usage du dossier Démarrage de Windows (aucune permission) comme alternative, puis du vrai service Windows (`sc.exe create`, nécessite lui de vraies droits admin, géré par auto-élévation UAC).
11. **`-Verb RunAs` (élévation UAC) ne démarre PAS forcément dans le même dossier de travail** que le script appelant — toujours résoudre les chemins en absolu (`Resolve-Path`) avant élévation, et/ou passer `-WorkingDirectory` explicitement.
12. **Capturer la sortie d'un processus élevé est piégeux** — la redirection externe (`*>> fichier` via `-Command`) a échoué silencieusement deux fois. Fix fiable : `Start-Transcript`/`Stop-Transcript` (mécanisme PowerShell natif) appelé **depuis l'intérieur** du script qui tourne élevé.
13. **Un venv Python déplacé sur Windows casse les lanceurs `.exe`** générés par pip (chemin absolu figé dedans) même si `python.exe` lui-même fonctionne — recréer le venv plutôt que de rafistoler.
14. **`requirements.txt` ne doit jamais contenir de flags pip** (`--break-system-packages` va sur la ligne de commande, jamais dans le fichier) — erreur trouvée et corrigée une fois, a failli être réintroduite après un reclone (fix jamais commité initialement).
15. **Chaque nouveau checkpoint fine-tuné doit repasser par l'export ONNX** (safetensors → .onnx), ce n'est pas automatique.
16. **Deux mécanismes de démarrage auto (service + dossier Démarrage) actifs en même temps = conflit de port** (`os error 10048`) — `install.ps1` nettoie maintenant systématiquement l'autre mécanisme à chaque install, et arrête toute instance active avant de démarrer la nouvelle.
17. **Chargement paresseux du corpus côté client** : `everycli-rs` parsait tout le corpus YAML local à CHAQUE recherche, même quand le daemon répondait avec succès (où ce parsing ne sert à rien) — coûtait ~0.4s. Rendu paresseux (macro `ensure_corpus!()`), gain mesuré : ~0.5-0.6s → ~0.13-0.21s.

## 5. État vérifié à ce jour (Windows uniquement — Linux/macOS jamais testés, voir §7)

- Daemon Rust fonctionnel end-to-end, hybride lexical+sémantique, 87.9% sur `eval/confusion_set.yaml`.
- `everycli add`/`list`/`remove` vérifiés fonctionnels (commande perso trouvée au coude-à-coude avec le corpus intégré, suppression avec confirmation).
- `install.ps1` : service Windows **par défaut** (auto-élévation UAC, repli sur dossier Démarrage si refusé/`-NoService`), `uninstall.ps1` symétrique. Nettoyage mutuel des deux mécanismes. Détection de daemon déjà actif (message clair, plus d'erreur brute).
- Daemon multi-thread (thread par connexion, `Arc<Mutex<DaemonState>>>`) — plus mono-thread.
- Latence recherche client : ~0.13-0.21s (mesuré, après fix du chargement paresseux).
- Couleurs + `--interactive` (via `inquire`) vérifiés fonctionnels sur PowerShell, `cmd.exe`, Git Bash.
- Mode téléchargement GitHub release : **codé mais jamais testé** (aucune release publique n'existe — décision explicite de tester au moment de la vraie soumission).

## 6. Format YAML du corpus (parseur maison, pas un vrai parseur YAML)

```yaml
- id: identifiant_unique
  description: "texte"
  tags: ["tag1", "tag2"]
  commands:
    linux: "commande"
    windows: "commande"
    macos: "commande"   # optionnel
  explanation: "texte"
  warning: "texte"       # optionnel
```

Indentation stricte : `- id:` à 0, champs à 2 espaces, sous-champs de `commands:` à 4 espaces. Le **nom du fichier = le namespace** de tous les scénarios qu'il contient. `everycli add` écrit dans `~/.everycli/commands/<namespace>.yaml` (jamais dans le corpus intégré `everycli/data/commands/`).

## 7. Ce qui reste à faire

- **Linux (WSL) et macOS** — jamais testés, remis "à la fin" plusieurs fois dans la session. `install.sh`/`scripts/linux/stage-release.sh` écrits mais non vérifiés.
- Taille du modèle (470MB float32) — quantification int8 envisagée, pas faite.
- Tags git (`v1.1.1`, `v1.2.0-dev`) — à vérifier si posés.
- Captures d'écran avant/après pour le jury — pas faites.
- `docs/BUILD_WEEK.md` — pas encore vérifié/mis à jour (les autres fichiers de `docs/` l'ont été : `tutorial_installation.md`, `explanation_architecture.md`, `how_to_build.md`, `reference_config.md`, `shell_integration.md`).
- Site frontend (`frontend/`) — géré en parallèle par l'utilisateur lui-même, pas par l'assistant.
- Idée en discussion, pas commencée : intégrer optionnellement l'API d'un modèle tiers (fourni par un partenaire du hackathon Indaba X), avec clé API configurable par l'utilisateur — à cadrer avant de coder.

## 8. Contexte externe

L'utilisateur participe aussi à **Indaba X** (soumission séparée, ~200 mots, catégorie NLP/IA) — une description a été rédigée et affinée dans la conversation, à ne pas perdre si quelqu'un demande à la retrouver (accent mis sur : recherche hybride lexicale+sémantique calibrée à 87.9%, 100% local/hors-ligne, daemon Rust+ONNX, `everycli add` pour la personnalisation).
