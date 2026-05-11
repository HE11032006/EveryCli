# Architecture : Pourquoi un Daemon et un Moteur Hybride ?

EveryCli n'est pas un simple moteur de recherche de texte. Ce document explique les choix architecturaux qui permettent d'allier intelligence IA et performance instantanée.

## 1. Le défi de l'IA sur un CLI
L'utilisation de modèles de Deep Learning (comme Sentence-Transformers) pose deux problèmes majeurs pour un outil en ligne de commande :
1.  **Temps de chargement** : Charger un modèle de 300 Mo et initialiser PyTorch prend entre 1 et 3 secondes.
2.  **Ressources** : Charger le modèle à chaque commande est inefficace pour la batterie et le CPU.

## 2. La solution : Le Daemon
Pour résoudre ce problème, EveryCli utilise une architecture **Client/Serveur locale** :
- **Le Daemon** : Il tourne en arrière-plan et garde le modèle chargé en RAM. Il attend les requêtes sur un socket local.
- **Le Wrapper (Client)** : Un script Shell ultra-léger qui envoie la requête au daemon et affiche le résultat.
- **Résultat** : Une fois le daemon lancé, chaque recherche prend moins de **0.05s**.

## 3. Le Moteur Hybride (TF-IDF + Sémantique)
EveryCli combine deux approches pour garantir les meilleurs résultats :

### TF-IDF (Recherche par mots-clés)
Très rapide et précis quand l'utilisateur tape le mot exact (ex: "git"). Il est utilisé comme premier filtre.

### Sémantique (NLP / IA)
Utilise le modèle `paraphrase-multilingual-MiniLM-L12-v2`. Il comprend l'intention derrière les mots. 
- *Exemple* : Si vous cherchez "comment enregistrer", il comprend que c'est proche de "commit" même si le mot n'apparaît pas.

## 4. Portabilité via PyInstaller
En "gelant" (freezing) l'application avec PyInstaller, nous permettons à EveryCli de fonctionner sur n'importe quelle machine sans installation complexe de Python. Le binaire embarque son propre interpréteur et ses bibliothèques, garantissant une expérience "zéro dépendance" pour l'utilisateur final.
