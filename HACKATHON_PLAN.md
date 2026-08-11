# EveryCli — Plan Reverie Hacks 2026

Ce fichier liste tout ce qu'on prévoit de faire pendant le hackathon, dans l'ordre de priorité. Une case n'est cochée que quand c'est réellement fait et vérifié (compilé/testé chez toi) — pas avant.

Branche de travail : `reverie-hacks-2026`
Tag de départ : `v1.1.1` (état avant hackathon)
Tag d'arrivée visé : `v1.2.0`

---

## Axe 1 — Architecture du daemon : sortir de PyInstaller, passer en Rust + ONNX

**Pourquoi** : le binaire Full gelé (PyInstaller) hang au chargement du modèle sur Windows, cause non isolée avec certitude. Plutôt que de continuer à corriger des symptômes un par un, on élimine la cause racine : plus de Python du tout dans le runtime distribué.

- [x] Exporter le modèle `Michelhe/everycli-minilm-ft-boosted` en ONNX (`optimum-cli export onnx --library-name transformers`)
  - Piège rencontré : `tokenizer_class: "TokenizersBackend"` (abstraction transformers v5) dans le tokenizer_config.json en cache — patché localement en `XLMRobertaTokenizerFast` (le vrai nom de classe, confirmé par les tokens spéciaux `<s>/</s>/<mask>` typiques de XLM-RoBERTa/SentencePiece)
- [x] Test de vélocité isolé (`rust/onnx-bench/`) : crate Rust avec `ort` 2.0.0-rc.13 (feature `load-dynamic`), charge le modèle ONNX, fait une inférence, compare au Python
  - **Résultat : chargement 7.3x plus rapide (1.59s vs 11.65s), latence par requête 1.7x plus rapide (12.45ms vs 21.60ms), même en single-thread**
  - Sanity check cosinus cohérent (paires même-domaine nettement plus proches que cross-domaine) — pooling manuel validé qualitativement
  - Pièges de compilation résolus : API `ort` 2.0-rc (pas d'`Environment` séparé, `try_extract_array` pas `try_extract_tensor`, `ort::Error<R>` pas Send+Sync → `map_err` explicite), conflit de liaison MSVC statique/dynamique résolu via feature `load-dynamic` (charge `onnxruntime.dll` au runtime plutôt qu'à la compilation)
- [x] Porter la logique d'inférence (tokenization + forward pass + mean pooling déjà validés dans onnx-bench) dans le vrai daemon (`rust/everycli-daemon`, nouveau crate)
- [x] Le daemon devient un seul binaire Rust natif (`everycli-daemon`) — **confirmé end-to-end** : le vrai client `everycli-rs` (aucune modification) parle au nouveau daemon Rust via le protocole JSON existant, log de connexion vérifié (ping + search reçus), résultats hybrides lexical+sémantique cohérents sur une vraie requête ("annuler mon dernier commit" → 3 candidats git pertinents, scores 0.72/0.69/0.65, désambiguïsation client déclenchée correctement entre deux commandes proches)
- [ ] Coût de démarrage à froid : calcul des embeddings du corpus (453 scénarios) prend ~4-6.5s à chaque lancement du daemon — candidat pour un cache disque (embeddings + hash du modèle) pour rendre les redémarrages quasi instantanés
- [ ] Valider la parité de similarité avec le corpus de test réel (pas juste 5 requêtes de sanity check) — comparer scores hybrides Rust vs résultats attendus / ancien comportement Python sur un jeu de requêtes de référence
- [ ] Calibrer les poids lexical/sémantique (actuellement 0.35/0.65, arbitraires) contre ce jeu de référence
- [ ] Décider : garder le modèle en float32 (470MB, simple) ou quantifier en int8 pour réduire la taille de distribution (optimisation, pas bloquant)
- [ ] Le serveur TCP est actuellement mono-thread (une connexion à la fois) — suffisant pour un usage personnel local, à revoir si besoin de concurrence

## Axe 1bis — Calibrage et fine-tuning (fait avec DeepSeek, à intégrer au suivi)

- [x] Mode `--debug` sur le daemon/client pour voir les scores séparés (lexical, sémantique, hybride)
- [x] Jeu de test `confusion_set.yaml` (66 requêtes) pour mesurer objectivement la qualité du ranking
- [x] Itérations de calibrage : alias supplémentaires dans `explicit_namespace()`, poids hybrides ajustés (0.35/0.65 → 0.40/0.60 → 0.45/0.55), ordre des alias, fallback par tags
- [x] Résultat : 58/66 (87.9%) sur confusion_set, contre 50/66 (75.8%) initial
- [x] Fine-tuning supplémentaire : 1880 paires d'entraînement générées depuis le corpus (tags boostés), entraîné sur Colab → nouveau modèle HuggingFace (repo à confirmer : `Michelhe/everycli-minilm-ft-boosted`)
- [ ] Export ONNX du nouveau modèle boosté (en cours)
- [ ] Rebrancher le daemon sur le nouveau modèle et relancer confusion_set.yaml pour mesurer l'amélioration réelle

**Leçon à retenir** : tout nouveau checkpoint fine-tuné/poussé sur HuggingFace doit repasser par l'export ONNX (safetensors → .onnx) avant d'être utilisable par le daemon Rust — ce n'est pas automatique, c'est une étape manuelle à refaire à chaque nouveau modèle. Si le modèle est déjà téléchargé en local (`snapshot_download`), pointer `optimum-cli export onnx --model <dossier local>` directement dessus plutôt que de re-télécharger depuis le hub.

**Décision** : le modèle fine-tuné "boosté" (`Michelhe/everycli-minilm-ft-boosted`, 1880 paires) **régresse** par rapport au modèle de base sur `confusion_set.yaml` (en dessous de 87.9%) — confirmé à la fois sur un exemple isolé (similarité cosinus brute) et sur le score global via le daemon. **On garde le modèle de base (`Karmelkke/everycli-minilm-ft`) en production.** Le repo `Michelhe/everycli-minilm-ft-boosted` est repoussé avec les poids du modèle de base (historique git préservé, le fine-tuning boosté reste récupérable dans les commits antérieurs si on veut le retravailler plus tard). Le daemon local pointe sur `onnx-bench/models/everycli-minilm-ft` (le tout premier export, déjà testé et fonctionnel).

**Bug structurel trouvé et corrigé** : le fallback `detect_namespace_by_tags()` ajouté pendant le calibrage cassait la recherche en excluant des scénarios pertinents AVANT le scoring hybride (namespace `bash_command`, très générique, gagnait par volume de correspondances de tags faibles plutôt que par pertinence réelle) — chute à 77.3%. Root cause plus profonde : **tout filtrage dur par namespace avant le scoring casse le principe même de la recherche sémantique**, et aurait aussi cassé la découvrabilité des commandes ajoutées via `everycli add` (namespace générique type `custom_commands`, exclu dès qu'une requête contient un mot-clé d'un autre écosystème déjà dans `ALIASES`). **Fix** : `filter_candidates` (filtre dur) reste utilisé uniquement par `search()` (fallback lexical pur, sans signal sémantique pour rattraper une exclusion à tort) ; le daemon utilise maintenant `candidates_for_platform()` (aucune exclusion par namespace) + `explicit_namespace()` comme **bonus additif** au score hybride (+0.2, arbitraire) plutôt que comme filtre. Résultat : retour à 87.9% (58/66) **et** le problème `everycli add` est résolu structurellement, pas contourné.

**Poids hybrides actuels** : lexical 0.45 / sémantique 0.55 / bonus namespace +0.2 (tous arbitraires, point de départ raisonnable, pas calibrés finement). Les 8 échecs restants sur `confusion_set.yaml` sont des confusions fines entre commandes très proches (ex: `docker compose down` vs `stop`, `exec` vs `run`) — du vrai calibrage, plus des bugs de filtrage.

## Axe 2 — Distribution : `install.sh` / `install.ps1`

### Windows — fait et vérifié end-to-end

- [x] `scripts\windows\stage-release.ps1` : assemble un dossier `dist\windows` (binaires release + modèle ONNX + runtime + corpus) — sert de base au futur packaging CI
- [x] `install.ps1` : copie dans `%LOCALAPPDATA%\EveryCli`, ajoute au PATH utilisateur (idempotent), démarre le daemon immédiatement
- [x] Persistance au démarrage de session : **dossier Démarrage de Windows** (`shell:startup`) avec un lanceur VBScript invisible (pas de fenêtre console), PAS le Planificateur de tâches — `schtasks /create` a échoué avec "Accès refusé" sur la machine de test (restriction locale/de groupe), le dossier Démarrage ne demande aucune permission spéciale et est fonctionnellement équivalent pour ce besoin
- [x] **Vérifié end-to-end depuis un état propre** : nouveau terminal, dossier hors du repo (`C:\Users\EULOGE`), `everycli search "..."` fonctionne — PATH + découverte automatique du daemon sibling + daemon déjà actif en arrière-plan depuis l'installation, résultats cohérents (scores 0.59/0.59/0.53 sur une vraie requête de désambiguïsation git)
- [ ] Désinstallation propre (script ou commande dédiée) — pas encore fait
- [ ] Vrai mode téléchargement depuis une release GitHub (actuellement seul `-LocalSource` fonctionne — mode téléchargement écrit comme point d'extension mais pas implémenté, nécessite une vraie release publiée d'abord)
- [ ] Taille de l'installation à vérifier (modèle float32 470MB + runtime ONNX + binaires) — lié à la décision de quantification de l'Axe 1

### Linux - pas commencé

- [ ] `install.sh` équivalent (même structure : bin/model/runtime/data dans `~/.local/share/everycli`, PATH via `~/.local/bin` ou modification de `.profile`)
- [ ] Persistance : `systemd --user` (pas d'équivalent "dossier Démarrage" universel sur Linux, mais `systemd --user` ne devrait pas avoir le même problème de permissions que Task Scheduler — à confirmer)

### macOS — pas commencé, remis à plus tard (décision explicite de l'utilisateur)

## Axe 3 — Service en arrière-plan (fiable, persistant au reboot)
*(inchangé)*

## Axe 4 — Bugs déjà identifiés
- [x] Mismatch de noms de binaires sibling — corrigé dans `daemon.rs`
- [ ] Gestion PID peu fiable sur Windows — obsolète une fois l'Axe 1/3 faits
- [ ] Ambiguïté d'extraction `everycli-data.zip` — obsolète une fois l'Axe 1 fait

## Axe 5 — Commande `everycli add`

- [x] Dossier utilisateur séparé du corpus intégré (`~/.everycli/commands` / `%USERPROFILE%\.everycli\commands`) — jamais écrasé par une mise à jour, même résolution de chemin côté client ET daemon (`EVERYCLI_USER_DATA_DIR` overridable)
- [x] `everycli-core::load_corpus_merged()` — fusionne corpus intégré + utilisateur, dossier utilisateur optionnel (pas d'erreur si absent/vide)
- [x] `everycli add` (everycli-rs) : prompts interactifs (catégorie/namespace, description, commande, explication, tags, avertissement optionnel), génération d'id unique (slug namespace+description, suffixe numérique si collision contre corpus intégré+utilisateur), écriture YAML au format exact attendu par le parseur maison
- [x] Reload best-effort du daemon après ajout (action `reload` déjà implémentée à l'Axe 1, enfin utilisée) — pas bloquant si daemon injoignable
- [x] **Vérifié end-to-end** : commande ajoutée (`mes_scripts_pour_usage_personnel`) retrouvée en recherche via le daemon, au coude à coude avec des commandes du corpus intégré (scores 0.50-0.53), désambiguïsation déclenchée normalement — confirme que le bug de filtrage par namespace corrigé plus tôt (Axe 1) ne bloque pas les commandes utilisateur
- [ ] Peaufinage à prévoir plus tard (Axe 8/finition) : validation des entrées plus stricte, commande par plateforme en option avancée, `everycli list`/`everycli remove` pour gérer les commandes ajoutées

## Axe 6 — Design / UI

- [x] Bug corrigé : après désambiguïsation, l'app affichait toujours 2-3 résultats au lieu d'une réponse nette
- [x] Suppression du blocage par question forcée (1 ou 2 ?) quand les scores sont proches — remplacé par un affichage informatif (même format que `--top N`), l'utilisateur choisit en lisant plutôt que l'outil ne décide à sa place (exception : mode `--shell`, qui garde une sortie déterministe unique pour rester utilisable en script)
- [x] Ajout de `owo-colors` (feature `supports-colors`) : désactivation automatique si sortie non-terminal ou `NO_COLOR` défini (recommandation clig.dev)
- [x] Deux formats distincts : réponse unique (✓ vert + commande cyan/gras) vs liste de plusieurs résultats (numérotée, commandes cyan/gras)
- [x] Score caché par défaut, visible seulement avec `--debug` (nouveau flag) ou `--json`
- [x] **Vérifié** end-to-end : cas "1 résultat" (docker) et cas "plusieurs résultats proches" (git) confirmés fonctionnels par l'utilisateur
- [ ] Mode `--interactive` : upgrade vers une vraie sélection au clavier (`inquire` ou `dialoguer`) au lieu de taper un numéro + Entrée — pas fait ce soir, identifié comme prochaine amélioration
- [ ] Décision explicite : PAS de TUI plein écran (`ratatui`) pour le mode par défaut — casserait le scripting/pipe (`--json`, `--shell`) et l'usage "tape, obtiens, repars". Resterait une option pour un futur mode séparé (`everycli explore` ?), pas une priorité

## Axe 7 — Site web de présentation
*(inchangé)*

## Axe 8 — Preuves pour le hackathon
*(inchangé — rappel : ne cocher qu'après vérification réelle)*

---

## Ordre de travail recommandé (mis à jour)

1. ~~Axe 1, test de vélocité~~ ✅ fait et concluant
2. **Maintenant : porter l'inférence validée dans le vrai daemon Rust** (structure du crate, intégration avec le corpus/hybrid_matcher existant)
3. Axe 3 en parallèle une fois le daemon Rust fonctionnel
4. Axe 2 (install scripts)
5. Axe 5, 6, 7 en parallèle, pas bloquants
6. Axe 8 en continu
