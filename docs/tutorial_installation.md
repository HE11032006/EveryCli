# Tutoriel : installer et utiliser EveryCli

Ce tutoriel s’adresse aux utilisateurs et aux testeurs de release. Une release précompilée contient déjà le client Rust, le daemon, `model.onnx`, `tokenizer.json`, le runtime ONNX Runtime propre à la plateforme et le corpus intégré. **Rust, Cargo et Python ne sont pas nécessaires sur la machine de l’utilisateur.**

## Choisir une source

Il existe deux parcours utilisateur :

| Source | Quand l’utiliser | Téléchargement supplémentaire |
|---|---|---:|
| Archive extraite | Tu as déjà téléchargé un bundle complet | Non |
| Script seul | Tu veux laisser l’installeur télécharger une release GitHub | Oui, depuis GitHub Releases |
| `--local-source` | Test développeur d’un staging local | Non |

Un bundle extrait doit contenir `bin/`, `model/`, `runtime/`, `data/` et l’installeur correspondant. L’installeur détecte ce bundle à côté de lui et l’utilise directement.

## Installer sous Linux x86_64

### Depuis une archive de release

Depuis la page [GitHub Releases](https://github.com/HE11032006/EveryCli/releases), télécharge `everycli-linux-x86_64.tar.gz`, puis exécute :

```bash
tar -xzf everycli-linux-x86_64.tar.gz
cd everycli-linux-x86_64
./install.sh --language fr
```

L’installeur installe EveryCli dans `~/.local/share/everycli`, crée les liens `~/.local/bin/everycli` et `~/.local/bin/everycli-daemon`, puis active `everycli-daemon.service` avec `systemd --user`.

### Depuis le script seul

Pour télécharger explicitement une version précise, récupère le script correspondant au même tag que la release :

```bash
VERSION=v1.2.0
curl --fail --location --proto '=https' --tlsv1.2 \
  -o install.sh \
  "https://raw.githubusercontent.com/HE11032006/EveryCli/${VERSION}/install.sh"
chmod +x install.sh
./install.sh --version "$VERSION" --language fr
```

Sans `--version`, l’installeur utilise la release GitHub marquée `Latest` :

```bash
./install.sh --language fr
```

Le téléchargement de l’archive et de `SHA256SUMS` se fait en HTTPS. L’installeur vérifie le hash avant d’extraire et refuse un bundle incomplet.

Après l’installation, ouvre un nouveau terminal ou recharge le profil :

```bash
source ~/.profile
hash -r
everycli search "comment annuler mon dernier commit"
```

Le premier démarrage peut prendre plus de temps : le daemon charge le modèle et calcule le cache des embeddings du corpus. Sous une machine lente ou WSL, cette phase peut durer plusieurs minutes.

## Installer sous Windows x86_64

### Depuis une archive extraite

Télécharge `everycli-windows-x86_64.zip`, extrais-le, ouvre PowerShell dans le dossier extrait et lance :

```powershell
.\install.ps1 -Language fr
```

`install.ps1` détecte le bundle voisin et n’effectue pas de téléchargement redondant.

### Depuis le script seul

```powershell
$Version = "v1.2.0"
Invoke-WebRequest `
  -Uri "https://raw.githubusercontent.com/HE11032006/EveryCli/$Version/install.ps1" `
  -OutFile .\install.ps1
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\install.ps1 -Version $Version -Language fr
```

L’installeur place EveryCli dans `%LOCALAPPDATA%\EveryCli`, ajoute son dossier `bin` au PATH utilisateur, vérifie `SHA256SUMS` et installe le daemon. Utilise `-NoService` pour éviter l’élévation et utiliser le dossier de démarrage Windows :

```powershell
.\install.ps1 -NoService -Language fr
```

Le mode service Windows peut demander une élévation. L’installeur arrête une ancienne instance avant de changer de mode afin d’éviter deux daemons qui se disputeraient le port `51821`.

## Utiliser EveryCli

```bash
everycli search "décris ton intention"
everycli search "requête" --top 3
everycli search "requête" --interactive
everycli search "requête" --copy
everycli search "requête" --run
everycli search "requête" --json
everycli search "requête" --no-daemon
```

Le mode interactif accepte `-i` ou `--interactive`. Les options doivent être séparées :

```bash
everycli search "requête" --top 3 -i
```

`--copy` copie la commande sélectionnée, tandis que `--run` demande une confirmation avant d’exécuter quoi que ce soit. Les commandes personnelles sont gérées avec :

```bash
everycli add
everycli list
everycli remove
```

Elles sont stockées séparément du corpus intégré : `~/.everycli/commands` sous Linux et `%USERPROFILE%\.everycli\commands` sous Windows.

## Utiliser `everycli ask`

`everycli ask` est distinct de `everycli search`. `search` retrouve une commande dans le corpus local sans clé API. `ask` appelle une API compatible OpenAI pour proposer une commande, une explication, un avertissement et des tags. Il propose ensuite d’enregistrer la suggestion dans le corpus personnel ; l’utilisateur doit toujours relire la commande avant de l’exécuter.

Configure la clé API avec la configuration locale :

```bash
everycli config set api_key "ta-cle-api"
everycli config show
everycli ask "compresser le dossier courant"
```

La clé peut aussi être fournie par `EVERYCLI_API_KEY`. Pour utiliser un fournisseur compatible OpenAI, configure éventuellement :

```bash
everycli config set provider openai
everycli config set api_url "https://api.openai.com/v1"
everycli config set api_model "gpt-4o-mini"
```

`everycli config show` n’affiche jamais la valeur complète de la clé. Sous Unix, le fichier de configuration est créé avec des permissions privées. Sans clé, `ask` affiche une erreur de configuration ; cela ne bloque pas `search`.

`everycli plan` correspond à Sentinel, le planificateur Python séparé. Il effectue une revue de sécurité d’une commande issue du corpus et ne lance pas la commande automatiquement.

## Désinstaller

Sous Linux, depuis le dépôt ou depuis un dossier qui contient `uninstall.sh` :

```bash
./uninstall.sh
```

Cette commande arrête et supprime le service, les liens, l’installation et les blocs EveryCli du profil. Elle conserve par défaut `~/.everycli`, notamment la configuration et les commandes personnelles. Pour supprimer explicitement ces données :

```bash
./uninstall.sh --remove-user-commands
```

Sous Windows :

```powershell
.\uninstall.ps1
```

Les données personnelles sont conservées par défaut. Vérifie l’option destructive documentée par la version de `uninstall.ps1` uniquement lorsque cette suppression est voulue.

## Dépannage

Sous Linux, vérifie le service et le port :

```bash
systemctl --user status everycli-daemon.service --no-pager -l
journalctl --user -u everycli-daemon.service -n 100 --no-pager
ss -ltn | grep 51821
cat "$HOME/.local/share/everycli/logs/daemon.log"
```

Si `everycli: command not found` apparaît juste après l’installation, le shell courant n’a pas encore rechargé le profil :

```bash
source ~/.profile
hash -r
command -v everycli
```

Si le service est actif mais que le port ne répond pas immédiatement, attends la fin du premier chargement du modèle avant de conclure à un échec.

Sous Windows, vérifie le service avec :

```powershell
sc.exe query EveryCliDaemon
Get-Process everycli-daemon -ErrorAction SilentlyContinue
```

Consulte aussi `%LOCALAPPDATA%\EveryCli\logs\install-service.log` lorsque le mode service a été utilisé.

## macOS

Le code macOS est compilé et testé dans la CI, mais aucune archive macOS installable n’est publiée pour le moment. L’installeur et le runtime natif macOS doivent encore être validés de bout en bout.
