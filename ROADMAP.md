# Bilan et Feuille de Route (Roadmap) - EveryCli V1

Ce document trace l'état actuel du projet à l'issue de notre dernière session, incluant les fonctionnalités réalisées et celles qui ont été identifiées (notamment lors des conversations avec Claude) pour être développées plus tard.

---

## ✅ Ce qui a été accompli (Bilan)

Ces éléments sont maintenant terminés, testés (182/182 tests) et fonctionnels :

### 1. Précision du Moteur de Recherche (Sémantique)
*   **Ajustement des Poids** : La pondération (`semantic_weight`) a été passée à `0.85` pour s'assurer que le moteur d'Intelligence Artificielle local (via `paraphrase-multilingual-MiniLM-L12-v2`) prime sur les simples correspondances de mots-clés.
*   **Corpus Enrichi** : Les commandes problématiques comme `docker_compose_up` et `git_undo_last_commit_discard_changes` ont été complétées pour répondre parfaitement aux intentions naturelles complexes (ex: "lance tous les containers en arriere plan").
*   **Maintien du Fast-Path** : La recherche purement lexicale est toujours utilisée, mais uniquement quand il y a une certitude absolue, préservant ainsi les performances sans sacrifier la pertinence.

### 2. Désambiguïsation Interactive (O4)
*   **Confirmation Utilisateur** : Lorsque le moteur sémantique trouve deux commandes avec des scores très proches (écart < 5%), EveryCli ne prend plus le risque d'exécuter la mauvaise commande. Il s'arrête et demande : *"🤔 J'hésite entre deux commandes très proches. Quelle est ton intention ?"*.

### 3. Exploitation Réelle des Tips et Troubleshooting (UI)
*   *Auparavant, ces informations étaient validées dans le YAML mais invisibles pour l'utilisateur.*
*   **Extraction** : Le `yaml_loader` parse désormais intégralement les types `tip` et `troubleshooting` avec leurs champs `causes` et `solutions`.
*   **Affichage Riche (Rich)** : 
    *   Les **Tips (💡)** s'affichent avec une esthétique ambrée claire.
    *   Les **Dépannages (🔧)** s'affichent en rouge, listant de manière proactive les causes probables et les solutions.
*   **Sécurité** : Il est impossible de "copier" ou "d'exécuter" un tip par erreur (contrairement à une commande standard).

### 4. Intégration Shell Complète
*   **Scripts Natifs** : Création de `everycli.bash` et `everycli.zsh` (en plus du `everycli.ps1` existant) pour une intégration native.
*   **Expérience Transparente** : La commande `evc "mon intention"` insère directement le résultat dans le prompt du terminal, prêt à être édité ou validé par l'utilisateur (zéro exécution aveugle).

### 5. Performances et Benchmarking
*   **Vitesse** : Création du script `tools/benchmark_speed.py`.
*   **Résultats** : Toutes les requêtes testées tournent sous les 100ms. La moyenne (warm-path) est de **4.2ms**. Le daemon Python garde le modèle en mémoire de façon fiable.

---

## 🚧 Ce qui reste à faire (Feuille de Route)

Ces éléments ont été discutés avec Claude et actés comme les "prochaines étapes" (Features futures / Optimisations avancées) :

### 1. Client Natif en Rust (`everycli-rs`)
*   **Objectif** : Remplacer le démarrage du CLI par un binaire ultra-rapide et sans dépendance Python pour l'utilisateur final. 
*   **Statut** : Le code existe dans `rust/`, mais nécessite un environnement avec Rust installé (`rustup`) pour être compilé, testé et lié au daemon Python en arrière-plan.

### 2. Boost par Historique (History Boosting)
*   **Objectif** : Rendre l'outil contextuel à chaque utilisateur. Si un développeur choisit systématiquement une variante précise d'une commande Docker, EveryCli doit le mémoriser et propulser cette commande en top 1 la fois suivante.
*   **Statut** : En attente. Le concept d'enregistrement existe (history manager), mais le boost dynamique au moment de la recherche (`HybridMatcher`) reste à implémenter.

### 3. Indexation ANN (Approximate Nearest Neighbors)
*   **Objectif** : Maintenir des temps de réponse sous les 10ms même si le corpus passe de 1 000 à plus de 10 000 commandes.
*   **Solution** : Migrer de la comparaison de similarité cosinus linéaire actuelle (dans un tableau Numpy) vers une bibliothèque dédiée comme **FAISS**.
*   **Statut** : En attente. Actuellement, la recherche est suffisamment rapide car le corpus est encore modeste.

### 4. Fine-Tuning du Modèle Sémantique
*   **Objectif** : Améliorer drastiquement la compréhension du jargon très spécifique (noms de flags obscurs, abréviations propres au CLI).
*   **Solution** : Prendre notre base de données YAML (qui est déjà bilingue FR/EN avec des exemples de haute qualité) et entraîner/fine-tuner notre modèle `paraphrase-multilingual-MiniLM` dessus.
*   **Statut** : En attente d'un script d'entraînement (`training/`).

### 5. Génération et validation de Dataset
*   **Objectif** : Agrandir le corpus avec des scripts automatisés, extraire du contexte avec `architect_insight` depuis du code Dart/Python pour contextualiser les requêtes.
*   **Statut** : Outils présents dans `dataset_generation/` (to_review.jsonl, generate_dataset.py) à nettoyer et intégrer dans le pipeline régulier.
