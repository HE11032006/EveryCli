# Changelog — Reverie Hacks 2026

Toutes les entrées ci-dessous correspondent à un travail réellement effectué et vérifié pendant le hackathon (branche `reverie-hacks-2026`). Regroupées par axe fonctionnel plutôt que par date exacte de commit — voir `git log` sur la branche pour l'historique chronologique précis.

## Architecture — migration du daemon Python vers Rust + ONNX Runtime

Le daemon Python (PyInstaller) souffrait d'un hang non résolu au démarrage sur Windows (15+ minutes, cause jamais isolée avec certitude malgré investigation). Plutôt que corriger ce symptôme, toute la classe de problèmes a été éliminée : plus de Python dans le runtime distribué.

- Export du modèle de similarité sémantique (`paraphrase-multilingual-MiniLM-L12-v2`, fine-tuné sur le corpus EveryCli) au format ONNX.
- Nouveau crate `everycli-inference` : encodeur sémantique 100% Rust via ONNX Runtime.
- Nouveau crate `everycli-daemon` : remplace `daemon_server.py`, même protocole JSON/TCP exact — **le client existant (`everycli-rs`) n'a nécessité aucune modification**.
- Résultat mesuré : chargement du modèle 7.3x plus rapide (1.59s vs 11.65s), latence d'inférence 1.7x plus rapide (12.45ms vs 21.60ms/requête).
- Cache disque des embeddings du corpus (invalidation automatique par hash de contenu) pour un redémarrage quasi instantané une fois le cache chaud.

## Recherche hybride — calibrage et correction d'un bug structurel

- Ajout d'un mode `--debug` exposant les scores lexical/sémantique/hybride séparément.
- Jeu de test `confusion_set.yaml` (66 requêtes bilingues) pour mesurer objectivement la qualité du ranking : **87.9% de succès** (58/66), contre 75.8% avant calibrage.
- Bug structurel trouvé et corrigé : un filtrage dur par namespace excluait des résultats pertinents avant même le scoring sémantique — remplacé par un bonus additif au score plutôt qu'un filtre, ce qui a aussi rendu possible la fonctionnalité `everycli add` (voir plus bas) sans risque de rendre les commandes de l'utilisateur invisibles.

## `everycli add` — commandes personnalisées

- Nouvelle commande interactive pour ajouter des commandes personnelles au corpus.
- Stockées dans un dossier séparé (`~/.everycli/commands`), jamais écrasé par une mise à jour du corpus intégré.
- Fusionnées avec le corpus intégré à la recherche, aussi bien côté daemon que côté repli local.
- Rechargement à chaud du daemon après ajout (pas besoin de redémarrer).

## Distribution — installeurs

- `install.ps1` (Windows) : installation en une commande, ajout au PATH, daemon démarré automatiquement à l'ouverture de session (dossier Démarrage), vérifié de bout en bout depuis un état système propre.
- `install.sh` (Linux) écrit sur le même modèle (service `systemd --user`), en cours de vérification sous WSL.
- macOS : non commencé, prévu après validation Linux.

## Interface / expérience utilisateur

- Correction d'un bug où répondre à une désambiguïsation continuait d'afficher plusieurs résultats au lieu d'une réponse nette.
- Suppression du blocage par question forcée lors d'une désambiguïsation automatique — remplacé par un affichage informatif, l'utilisateur choisit en lisant plutôt que l'outil ne décide à sa place.
- Sortie colorée (désactivée automatiquement si non-terminal ou `NO_COLOR` défini), deux formats distincts selon qu'il y a un ou plusieurs résultats.

## Connu, non résolu

- Un modèle fine-tuné expérimental (entraîné sur des paires de données boostées) a été testé et s'est révélé moins performant que le modèle de base sur `confusion_set.yaml` — abandonné, le modèle de base reste en production.
- Poids du score hybride (lexical/sémantique/bonus namespace) fixés empiriquement, pas calibrés finement.
- Serveur daemon mono-thread (une connexion à la fois) — suffisant pour un usage personnel, pas conçu pour de la concurrence.
