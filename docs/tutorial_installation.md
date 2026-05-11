# Tutorial : Installer et utiliser EveryCli (Release)

Bienvenue dans EveryCli ! Ce guide vous accompagne pour installer l'outil à partir d'une version pré-compilée (Release) et réaliser votre première recherche.

## Prérequis
- **Linux / macOS** : Un terminal et `python3` (généralement pré-installé).
- **Windows** : PowerShell 5.1+ ou Windows Terminal.
- Aucun besoin d'installer de bibliothèques d'IA, tout est inclus dans les binaires !

## 1. Téléchargement et décompression
Téléchargez l'archive correspondant à votre système depuis la page des [Releases](https://github.com/HE11032006/EveryCli/releases).

### Linux / macOS
```bash
tar -xzf everycli-platform.tar.gz
cd everycli-platform
```

### Windows
Décompressez le fichier `.zip` dans un dossier (ex: `C:\Tools\EveryCli`).

## 2. Installation globale

### Linux / macOS
Créez un lien symbolique :
```bash
sudo ln -s $(pwd)/everycli /usr/local/bin/everycli
sudo ln -s $(pwd)/everycli-daemon /usr/local/bin/everycli-daemon
```

### Windows (PowerShell en mode Administrateur)
Ajoutez le dossier EveryCli à votre variable d'environnement `PATH` :
```powershell
[System.Environment]::SetEnvironmentVariable("Path", $env:Path + ";C:\chemin\vers\EveryCli", "User")
```

## 3. Utilisation selon votre système

### Linux / macOS
Utilisez la commande `everycli` directement :
```bash
everycli search "comment commit mes changements"
```

### Windows
Utilisez la commande `everycli.ps1` (ou `everycli` si le dossier est dans le PATH) :
```powershell
everycli search "git commit"
```

## 4. Recherche ciblée (Scoped Search)
La syntaxe est la même partout :
```bash
everycli search "git: commit mes changements"
```

## Et après ?
- Le moteur reste en veille en arrière-plan pour répondre instantanément à vos prochaines recherches.
- Si vous souhaitez arrêter le moteur manuellement : `everycli daemon --stop`.
