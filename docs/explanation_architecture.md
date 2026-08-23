# Architecture : pourquoi un daemon et un moteur hybride ?

> Ce document décrit l'architecture actuelle (branche `reverie-hacks-2026`, 100% Rust + ONNX Runtime). Voir [CHANGELOG.md](../CHANGELOG.md) pour le détail de la migration depuis l'ancienne architecture Python/PyInstaller.

EveryCli n'est pas un simple moteur de recherche de texte. Ce document explique les choix architecturaux qui permettent d'allier intelligence sémantique et performance instantanée.

## 1. Le défi de l'IA sur un outil CLI

Un modèle d'embeddings sémantiques a un coût au démarrage : charger le modèle et initialiser le runtime d'inférence prend un temps non négligeable — mesuré à ~1.6s pour le chargement du modèle ONNX sur cette machine. Le refaire à chaque recherche serait inacceptable pour un outil censé répondre instantanément.

## 2. La solution : un daemon en arrière-plan

EveryCli utilise une architecture **client/serveur locale** :
- **Le daemon** (`everycli-daemon`, Rust) tourne en arrière-plan (service Windows natif ou `systemd --user` sur Linux), garde le modèle chargé en mémoire, et répond aux requêtes via un protocole JSON simple sur TCP (`127.0.0.1:51821`).
- **Le client** (`everycli-rs`, Rust) envoie la requête au daemon et affiche le résultat. S'il ne peut pas joindre le daemon, il retombe automatiquement sur une recherche lexicale locale — pas d'échec sec.
- **Résultat mesuré** : une fois le daemon prêt, latence d'inférence sémantique ~12ms, temps de réponse client complet ~130-210ms.

## 3. Le moteur hybride (lexical + sémantique)

EveryCli combine deux signaux pour classer les résultats :

### Score lexical
Correspondance de mots-clés entre la requête et la description/les tags d'un scénario — rapide, précis quand l'utilisateur utilise le vocabulaire exact (ex : "git").

### Score sémantique
Similarité cosinus entre l'embedding de la requête et celui de chaque scénario, via un modèle de similarité de phrases (`paraphrase-multilingual-MiniLM-L12-v2`, fine-tuné sur le corpus EveryCli), exécuté localement via ONNX Runtime. Il comprend l'intention derrière les mots — "annuler mon dernier commit" retrouve `git reset --soft HEAD~1` même sans le mot "git".

### Bonus de namespace (pas un filtre)
Un mot-clé explicite d'écosystème dans la requête (ex : "docker") donne un bonus au score des scénarios de ce namespace — mais ne **filtre** jamais les autres. C'est une décision délibérée : un filtrage dur exclurait à tort des paraphrases sans mot-clé, ou des commandes personnalisées ajoutées via `everycli add` dans un namespace différent. Voir [CHANGELOG.md](../CHANGELOG.md) pour le bug concret que cette décision a corrigé.

Les poids actuels (lexical 0.45 / sémantique 0.55 / bonus namespace +0.2) sont calibrés empiriquement contre `eval/confusion_set.yaml` (87.9% de précision sur 66 requêtes bilingues), pas figés définitivement.

## 4. Distribution sans dépendance

Le daemon et le client sont des binaires Rust natifs — aucune dépendance à un interpréteur Python ou à une bibliothèque externe au runtime. Le modèle (`model.onnx`) et le runtime d'inférence (`onnxruntime.dll`/`.so`) sont distribués à côté des binaires, chargés dynamiquement au démarrage. Voir `install.ps1`/`install.sh` pour le flux d'installation complet.

## 5. Commandes personnalisées

`everycli add` écrit dans un dossier séparé du corpus intégré (`~/.everycli/commands`), fusionné à la recherche côté client ET daemon — jamais écrasé par une mise à jour de l'application.

## Composant Python restant : Sentinel

Le planificateur Sentinel (`everycli plan`, LLM-based, voir `everycli/infra/`) reste un composant Python séparé — il n'a pas été concerné par cette migration, et continue de fonctionner indépendamment du chemin de recherche rapide en Rust.
