# Tutorial : Installer et utiliser EveryCli

Bienvenue dans EveryCli ! Ce guide vous accompagne pour installer l'outil à partir d'une version pré-compilée (Release) pour Linux, macOS ou Windows. Pour l'instant, il y a seulement les commandes git, docker, powershell, bash, composer, docker compose qui sont dans les binaires.

## 1. Téléchargement

Rendez-vous sur la page des [Releases](https://github.com/HE11032006/EveryCli/releases) et téléchargez le fichier correspondant à votre système :

- **Linux** : `everycli-linux-full` (recommandé: ~600 mo) ou `everycli-linux-lite` (le modèle complet se télécharge quand vous lancer la commande pour la première fois).
- **macOS** : `everycli-macos-full` (recommandé ~600 mo) ou `everycli-macos-lite` (le modèle complet se télécharge quand vous lancer la commande pour la première fois).
- **Windows** : `everycli-windows-full.exe` (ou version lite) ET le fichier `everycli.ps1`.

## 2. Installation et Configuration

### 🐧 Linux / 🍎 macOS

1. Donnez les droits d'exécution au fichier téléchargé :

   ```bash
   chmod +x everycli-linux-full  # Remplacez par le nom du fichier téléchargé
   ```
2. Créez un lien symbolique pour pouvoir l'utiliser partout :

   ```bash
   sudo ln -s $(pwd)/everycli-linux-full /usr/local/bin/everycli
   ```
3. Testez l'installation :

   ```bash
   everycli search "comment faire un commit"
   ```

### 🪟 Windows

1. Placez le fichier `.exe` et le fichier `everycli.ps1` dans un dossier stable (ex: `C:\Tools\EveryCli`).
2. Renommez le fichier `.exe` en `everycli-daemon.exe` (pour que le script PowerShell le trouve).
3. Ajoutez le dossier EveryCli à votre variable d'environnement `PATH`.
4. Dans un terminal PowerShell, lancez :
   ```powershell
   everycli search "git commit"
   ```

## 3. Utilisation Avancée

### Recherche ciblée (Scoped Search)

Pour limiter la recherche à un outil spécifique (ex: git), utilisez le préfixe suivi de `:` :

```bash
everycli search "git: annuler le dernier commit"
```

### Gestion du Daemon

EveryCli utilise un daemon en arrière-plan pour des réponses instantanées (<50ms).

- **Arrêter le daemon** : `everycli daemon --stop`
- **Voir l'état** : `everycli daemon --status`

---

*Note : La version **Lite** téléchargera automatiquement le modèle IA (~400Mo) lors de la première recherche. La version **Full** contient déjà tout.*
