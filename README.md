# EveryCli

Un outil CLI intelligent pour vous aider à trouver les bonnes commandes selon votre OS.

## Installation
crée un environnement virtuel:

### Sur Windows (PowerShell) :
```powershell
.\.venv\Scripts\activate
pip install -r requirements.txt
```

### Lancer les tests :
Une fois installé, tu peux vérifier que tout fonctionne avec :
```powershell
pytest
```
### Utiliser EveryCLi :

```bash
everycli "modifier mon dernier commit"
```

## Install

```bash
pip install -e .
```

## Usage

```bash
# Trouver une commande
everycli "annuler mon dernier commit sans perdre mes changements"

# Voir les 3 meilleurs résultats
everycli "commit" --top 3

# Diagnostiquer une erreur
everycli "modifier mon commit" --error "nothing to commit"
```

## Stack

- Python 3.11+
- TF-IDF matching (phase 2 : NLP sémantique)
- Rich terminal display
- Base YAML extensible
