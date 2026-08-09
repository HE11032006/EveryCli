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
*(inchangé, voir version précédente du plan)*

## Axe 3 — Service en arrière-plan (fiable, persistant au reboot)
*(inchangé)*

## Axe 4 — Bugs déjà identifiés
- [x] Mismatch de noms de binaires sibling — corrigé dans `daemon.rs`
- [ ] Gestion PID peu fiable sur Windows — obsolète une fois l'Axe 1/3 faits
- [ ] Ambiguïté d'extraction `everycli-data.zip` — obsolète une fois l'Axe 1 fait

## Axe 5 — Commande `everycli add`
*(inchangé)*

## Axe 6 — Design / UI
*(inchangé)*

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
