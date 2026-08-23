# Tutoriel : installer et utiliser EveryCli

EveryCli distribue des archives Linux et Windows précompilées contenant les binaires Rust, le modèle ONNX, le tokenizer, le runtime ONNX Runtime CPU natif et le corpus intégré. **L’utilisateur final n’a pas besoin d’installer Rust, Cargo ou Python.** Les releases sont publiées sur le dépôt [GitHub EveryCli](https://github.com/HE11032006/EveryCli).

## 1. Installer une release sans Rust

Choisir un tag publié, par exemple `v0.1.0`. Le script d’installation doit être téléchargé comme un fichier local, puis relu si nécessaire ; il ne faut pas exécuter directement un script récupéré par un pipe shell.

### Linux x86_64

```bash
VERSION=v0.1.0
curl --fail --location --proto '=https' --tlsv1.2 \
  -o install.sh \
  "https://raw.githubusercontent.com/HE11032006/EveryCli/${VERSION}/install.sh"
chmod +x install.sh
./install.sh --version "$VERSION" --language fr
```

L’installeur télécharge `everycli-linux-x86_64.tar.gz` et `SHA256SUMS` depuis la release correspondante, vérifie l’empreinte SHA-256, puis installe EveryCli dans `~/.local/share/everycli`. Il crée les liens dans `~/.local/bin`, configure et démarre le service `systemd --user` et conserve les commandes personnelles dans `~/.everycli/commands`.

### Windows x86_64

Dans PowerShell :

```powershell
$Version = "v0.1.0"
Invoke-WebRequest `
  -Uri "https://raw.githubusercontent.com/HE11032006/EveryCli/$Version/install.ps1" `
  -OutFile .\install.ps1
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\install.ps1 -Version $Version -Language fr
```

L’installeur télécharge `everycli-windows-x86_64.zip`, vérifie son SHA-256 avec `SHA256SUMS`, puis installe les binaires et le runtime. Par défaut, il tente d’utiliser le service Windows natif ; l’option `-NoService` permet d’utiliser le dossier Démarrage sans élévation administrateur.

### Vérifier manuellement une archive Linux

Pour inspecter l’archive avant installation, télécharger l’archive et son manifeste depuis la page [Releases](https://github.com/HE11032006/EveryCli/releases), puis exécuter :

```bash
VERSION=v0.1.0
mkdir -p "$HOME/Downloads/everycli-$VERSION"
cd "$HOME/Downloads/everycli-$VERSION"
curl --fail --location -O "https://github.com/HE11032006/EveryCli/releases/download/${VERSION}/everycli-linux-x86_64.tar.gz"
curl --fail --location -O "https://github.com/HE11032006/EveryCli/releases/download/${VERSION}/SHA256SUMS"
grep 'everycli-linux-x86_64.tar.gz$' SHA256SUMS | sha256sum -c -
tar -xzf everycli-linux-x86_64.tar.gz
./install.sh --local-source "$PWD" --language fr
```

Cette méthode n’effectue aucune compilation. `--local-source` signifie uniquement que l’archive déjà téléchargée est utilisée comme source locale.

## 2. Utiliser EveryCli

Ouvrir un nouveau terminal, ou recharger le profil après l’installation :

```bash
source ~/.profile
everycli search "comment annuler mon dernier commit"
```

Le daemon fonctionne en arrière-plan. Lors de son premier démarrage, il peut calculer le cache d’embeddings du corpus ; le client retombe automatiquement sur la recherche locale si le daemon n’est pas encore prêt.

Les options principales sont les suivantes :

```bash
everycli search "requête" --top 3         # afficher plusieurs résultats
everycli search "requête" --interactive   # choisir au clavier
everycli search "requête" --copy          # copier la commande
everycli search "requête" --run           # exécuter après confirmation
everycli search "requête" --json          # sortie machine-readable
everycli search "requête" --no-daemon      # forcer la recherche locale
```

Pour gérer son corpus personnel :

```bash
everycli add
everycli list
everycli remove
```

Les commandes personnelles sont stockées dans `~/.everycli/commands` sous Linux et `%USERPROFILE%\.everycli\commands` sous Windows. Elles ne sont pas écrasées par une mise à jour du corpus intégré.

## 3. Désinstaller

### Linux

```bash
./uninstall.sh
```

Le script arrête et retire le service `systemd --user`, supprime les liens et le dossier d’installation, mais **conserve par défaut** les commandes et la configuration de `~/.everycli`. Pour supprimer explicitement ces données personnelles :

```bash
./uninstall.sh --remove-user-commands
```

### Windows

```powershell
.\uninstall.ps1
```

L’installeur retire le service ou le lanceur, le dossier d’installation et les variables gérées. Les commandes personnelles sont conservées par défaut ; utiliser l’option destructive documentée par le script uniquement après confirmation.

## 4. Compiler depuis les sources — développeurs uniquement

La compilation est nécessaire uniquement pour modifier EveryCli ou produire un staging local avant publication. Elle n’est pas une étape du parcours utilisateur final.

```bash
git clone https://github.com/HE11032006/EveryCli.git
cd EveryCli
git switch reverie-hacks-2026
cd rust
cargo build --release -p everycli-rs -p everycli-daemon
cd ..
./scripts/linux/stage-release.sh
./install.sh --local-source "$PWD/dist/linux"
```

Le staging développeur exige que le modèle ONNX, le tokenizer et le runtime natif aient déjà été produits ou téléchargés. Le workflow GitHub Actions les prépare automatiquement pour les archives de release ; ils ne sont volontairement pas versionnés dans le dépôt Git en raison de leur taille.

## 5. Dépannage

Consulter le statut et les logs du daemon sous Linux :

```bash
systemctl --user status everycli-daemon.service --no-pager
journalctl --user -u everycli-daemon.service -n 100 --no-pager
cat "$HOME/.local/share/everycli/logs/daemon.log"
```

Sous Windows, consulter le journal d’installation dans `%LOCALAPPDATA%\EveryCli\logs\install-service.log` et vérifier le service avec `sc.exe query EveryCliDaemon`.

macOS n’est pas encore proposé comme archive installable : le workflow peut compiler et tester la cible, mais aucune release macOS n’est publiée tant que le runtime natif et l’installeur n’ont pas été validés de bout en bout.
