# How-to : Compiler EveryCli depuis les sources

Ce guide est destiné aux développeurs qui souhaitent modifier le code d'EveryCli ou générer leurs propres binaires à partir du dépôt Git.

## 1. Préparer l'environnement
Clonez le dépôt et créez un environnement virtuel Python (recommandé : Python 3.11+).

```bash
git clone https://github.com/HE11032006/EveryCli.git
cd EveryCli
python3 -m venv .venv
source .venv/bin/activate
```

## 2. Installer les dépendances
Installez les bibliothèques nécessaires. Notez que nous utilisons une version allégée de PyTorch pour limiter la taille des binaires.

```bash
pip install -r requirements.txt
```

## 3. Tester en mode développement
Avant de compiler, vous pouvez tester le code directement en utilisant Python :

```bash
# Lancer le daemon
python3 -m everycli.everycli daemon --start

# Lancer une recherche
python3 -m everycli.everycli search "git commit"
```

## 4. Compilation avec PyInstaller
EveryCli utilise des fichiers `.spec` pour configurer la compilation. Le binaire principal est le `daemon` car il embarque le modèle d'intelligence artificielle.

### Compiler le Daemon (Full CPU)
Cette commande génère le binaire `everycli-daemon` dans le dossier `dist/`.

```bash
pyinstaller everycli-daemon.spec --clean
```

### Préparer le dossier de distribution
Le script wrapper (`everycli`) se trouve dans le dossier `dist/`. Assurez-vous qu'il est à côté du binaire compilé.

```bash
ls dist/
# Doit contenir : everycli (script) et everycli-daemon (binaire)
```

## 5. Dépannage
- **Taille du binaire** : Si le binaire dépasse 1 Go, vérifiez que vous n'avez pas installé la version GPU de PyTorch par erreur.
- **Modèle manquant** : PyInstaller doit copier le dossier du modèle HuggingFace. Vérifiez le chemin dans `everycli-daemon.spec` (variable `model_path`).
