# EveryCli — Fichier de passation (pour poursuivre avec un autre assistant IA)

Ce fichier résume tout le contexte nécessaire pour continuer le travail sans avoir à tout redécouvrir. À coller en premier message à DeepSeek (ou tout autre assistant) avant de continuer.

---

## 1. Contexte du projet

EveryCli : outil CLI de recherche de commandes (git, docker, linux...) par langage naturel, en français/anglais, avec recherche lexicale + sémantique. Participation au hackathon **Reverie Hacks 2026**.

Repo local : `C:\EveryCli`. Branche de travail : `reverie-hacks-2026`.

**Le vrai plan détaillé et à jour est dans `C:\EveryCli\HACKATHON_PLAN.md` — le lire en premier, c'est la source de vérité sur l'avancement.**

## 2. Règles de travail à respecter absolument

- **Les commits, c'est l'utilisateur qui les fait.** L'assistant propose le message de commit, ne lance jamais `git commit` lui-même.
- **Les commandes à résultat long** (build, test, cargo, pip...) : l'assistant les donne à lancer, l'utilisateur les exécute et colle le résultat. L'assistant ne doit pas prétendre avoir exécuté quelque chose qu'il n'a pas pu exécuter.
- **Édition de fichiers** : si l'assistant a un accès filesystem direct au dossier (comme via un connecteur MCP), il peut éditer les fichiers directement — pas besoin de tout faire coller par l'utilisateur.
- **Ne pas cocher une case du plan tant qu'elle n'est pas réellement vérifiée** (compilée/testée par l'utilisateur, résultat confirmé). Ne jamais présenter comme acquis quelque chose qui n'a pas été testé.
- **L'utilisateur a du temps disponible** — préférer la vraie solution architecturale à la rustine rapide quand un choix se présente, mais rester pragmatique sous deadline si un sujet devient un puits de temps sans garantie de résolution (ex: un bug de linking natif profond) — proposer alors un pivot ou une solution de contournement documentée plutôt que de s'acharner indéfiniment.

## 3. Décision architecturale majeure (déjà prise, ne pas la remettre en cause sans raison forte)

**Le daemon Python (PyInstaller) est abandonné au profit d'un daemon 100% Rust + ONNX Runtime.**

Pourquoi : le binaire Windows "Full" (PyInstaller) avait un bug de hang non résolu de 15+ minutes au chargement du modèle IA, cause jamais isolée avec certitude malgré investigation (PID, TCP, Defender tous éliminés). Plutôt que corriger ce symptôme, on a éliminé toute la classe de problèmes (PyInstaller + Windows + ML est une combinaison structurellement fragile) en repartant sur une inférence 100% native.

**Le protocole client-serveur n'a PAS changé** : JSON ligne-par-ligne sur TCP `127.0.0.1:51821`, actions `search`/`ping`/`reload`, même schéma exact que l'ancien `daemon_server.py` Python. Le client Rust existant (`everycli-rs`, crate `everycli-core::daemon`) n'a nécessité **aucune modification** — c'est la clé qui a rendu cette migration faisable sans tout casser.

## 4. État actuel exact (vérifié, testé, fonctionnel)

### Ce qui compile et tourne (confirmé par l'utilisateur, pas supposé)

- **`rust/onnx-bench`** : crate de benchmark isolé. A validé l'hypothèse : chargement modèle 7.3x plus rapide (1.59s vs 11.65s Python), inférence 1.7x plus rapide (12.45ms vs 21.60ms/requête) que `sentence-transformers`.
- **`rust/everycli-inference`** : librairie Rust réutilisable (`SemanticEncoder`, `init_runtime`, `cosine_similarity`). Compile, 3 tests unitaires + 1 doctest passent.
- **`rust/everycli-core`** : existait déjà avant le hackathon (parsing YAML du corpus + recherche lexicale, 100% Rust, déjà testé contre le vrai corpus `everycli/data/commands`, 453 scénarios). Modifié pour exposer `filter_candidates()` et `score()` en public, nécessaires pour que le daemon puisse scorer sémantiquement des scénarios à score lexical nul (paraphrases).
- **`rust/everycli-daemon`** : **le nouveau serveur TCP Rust natif**, remplace `daemon_server.py`. Combine score lexical (`everycli-core`) + score sémantique (`everycli-inference`) en un score hybride (poids actuels 0.35 lexical / 0.65 sémantique — **arbitraires, pas calibrés**). Cache disque des embeddings du corpus (clé = hash contenu corpus + métadonnées fichier modèle, invalidation automatique).

**Confirmé end-to-end** : le vrai client `everycli-rs` (binaire inchangé) parle avec succès à `everycli-daemon`, log de connexion vérifié (ping + search reçus), résultats hybrides cohérents sur une vraie requête ("annuler mon dernier commit" → 3 commandes git pertinentes, scores 0.72/0.69/0.65, désambiguïsation client déclenchée correctement).

**Cache d'embeddings vérifié fonctionnel** : 1er démarrage calcule (~4-6.5s pour 453 scénarios), 2e démarrage charge depuis le cache disque et saute le calcul.

### Fichiers/dossiers clés créés pendant le hackathon

```
rust/onnx-bench/                          # benchmark, crate jetable
rust/onnx-bench/models/everycli-minilm-ft/  # model.onnx + tokenizer.json exportés
rust/onnx-bench/runtime/onnxruntime.dll   # runtime ONNX (chargement dynamique)
rust/onnx-bench/fetch_tokenizer.py
rust/onnx-bench/python_baseline/bench.py
rust/everycli-inference/                  # lib Rust : encodeur sémantique ONNX
rust/everycli-daemon/                     # LE NOUVEAU DAEMON — serveur TCP Rust
training/requirements-onnx-export.txt     # deps pour l'export ONNX (pas le runtime app)
HACKATHON_PLAN.md                         # plan détaillé, à jour, source de vérité
```

## 5. Pièges déjà rencontrés et résolus (NE PAS les redécouvrir)

1. **`optimum` récent a scindé l'export ONNX dans un package séparé** : il faut `pip install "optimum-onnx[onnxruntime]"`, pas juste `optimum`.
2. **Le repo HuggingFace du modèle a `tokenizer_class: "TokenizersBackend"`** dans son `tokenizer_config.json` (abstraction transformers v5, pas encore reconnue par les versions stables). Fix appliqué : patcher ce champ localement en `"XLMRobertaTokenizerFast"` (le vrai nom de classe — le modèle sous-jacent est un BERT multilingue avec tokenizer SentencePiece de XLM-RoBERTa, confirmé par les tokens spéciaux `<s>/</s>/<mask>/<pad>/<unk>`).
3. **`optimum-cli export onnx` doit être appelé avec `--library-name transformers`** (pas la valeur par défaut `sentence_transformers`, dont le chargement plante à cause du bug #2 ci-dessus).
4. **`ort` (crate Rust) n'a pas de version "stable"** — `2.0.0-rc.13` (ou plus récent) est la version recommandée en production malgré le suffixe `-rc`, ne pas chercher une "vraie" version stable ailleurs.
5. **API `ort` 2.0-rc, pièges de compilation rencontrés** :
   - Pas de type `Environment` séparé (contrairement à l'ancienne API v1.x) — `Session::builder()` directement.
   - Extraction de sortie : `try_extract_array::<f32>()`, **pas** `try_extract_tensor`.
   - `session.run()` prend `&mut self`.
   - `ort::inputs! { ... }` retourne directement la valeur (pas un `Result`) — le `?` va sur `.run(...)`, pas sur la macro.
   - **`ort::Error<R>` n'est pas toujours `Send`/`Sync`** (embarque parfois la ressource `R`, ex. `SessionBuilder`, avec des pointeurs bruts). `anyhow` refuse la conversion automatique via `?` dans ce cas → il faut `.map_err(|e| anyhow::anyhow!("{e}"))` explicitement partout où on touche l'API `ort`.
6. **Conflit de liaison MSVC (`LNK2005`/`LNK1120`) entre runtime C++ statique et dynamique** en liant `ort` statiquement sous Windows. **Fix : feature `load-dynamic` de `ort`**, qui charge `onnxruntime.dll` au runtime (`ort::init_from(path)?.commit()`) au lieu de lier statiquement à la compilation. Nécessite de télécharger le zip officiel `onnxruntime-win-x64-*.zip` depuis les releases GitHub de `microsoft/onnxruntime` et de placer `onnxruntime.dll` dans un dossier `runtime/`.
7. **Version d'`ndarray` doit matcher celle qu'`ort` utilise en interne** (`^0.17` pour `ort` 2.0.0-rc.13) — sinon erreurs de type confuses entre deux versions majeures incompatibles d'`ndarray`.
8. **`Tensor::from_array()` prend possession de l'array** — cloner `attention_mask` avant de le passer si on en a encore besoin après (pour le mean pooling).

## 6. Ce qui reste à faire (voir HACKATHON_PLAN.md pour la liste complète et les autres axes)

### Axe 1 (architecture daemon) — presque fini, reste :
- [ ] Valider la parité de similarité sur un vrai jeu de requêtes de référence (pas juste 5 requêtes de sanity check) — comparer aux résultats attendus.
- [ ] Calibrer les poids lexical/sémantique (actuellement 0.35/0.65, arbitraires).
- [ ] Décider : garder le modèle en float32 (470MB) ou quantifier en int8 pour réduire la taille de distribution.
- [ ] Le serveur TCP est actuellement **mono-thread** (une connexion à la fois) — suffisant pour un usage personnel local, à revoir si besoin de concurrence.
- [ ] Nommer/packager le binaire `everycli-daemon` selon la convention `everycli-{os}-full`/`-lite` pour que le mécanisme d'auto-respawn existant du client le trouve automatiquement dans une vraie release (voir `SIBLING_DAEMON_NAMES` dans `rust/everycli-core/src/daemon.rs`).

### Axes suivants (pas commencés) :
- **Axe 2** : `install.sh`/`install.ps1` — installation en une commande, sans dépendance Python/Rust côté utilisateur final.
- **Axe 3** : service en arrière-plan persistant (`systemd --user` sur Linux, service Windows natif via crate `windows-service` — **pas** `sc.exe` direct sur un exe qui ne répond pas au protocole SCM, piège déjà identifié).
- **Axe 5** : commande `everycli add` (commandes personnalisées).
- **Axe 6** : refonte design/UI (mentionné comme non prioritaire par l'utilisateur pour l'instant).
- **Axe 7** : site web de présentation du projet.
- **Axe 8** : preuves pour le hackathon (CHANGELOG.md, tags v1.1.1/v1.2.0, captures avant/après) — à remplir **au fur et à mesure de ce qui est réellement fait**, jamais à l'avance.

## 7. Prochaine étape suggérée

Deux options raisonnables pour continuer :
1. **Finir de nettoyer l'Axe 1** (parité + calibrage des poids) avant de passer à autre chose — plus rigoureux.
2. **Passer à l'Axe 2/3** (install + service) maintenant que le daemon fonctionne, et revenir calibrer plus tard — avance plus vite sur la distribution, qui est l'objectif final du hackathon.

Demander à l'utilisateur laquelle il préfère avant de choisir à sa place.
