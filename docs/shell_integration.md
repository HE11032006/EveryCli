# Intégration shell

EveryCli sépare l’interface humaine du protocole destiné aux wrappers. Cette séparation réduit le risque qu’une commande trouvée soit exécutée par surprise.

## Recherche interactive

Le mode interactif affiche plusieurs candidats et laisse l’utilisateur choisir au clavier :

```bash
everycli search "annuler mon dernier commit" --top 3 --interactive
```

`-i` est l’alias court de `--interactive`. La limite `--top` s’applique aussi aux choix interactifs :

```bash
everycli search "requête" --top 3 -i
```

Le mode interactif affiche le namespace, l’identifiant, la commande, l’explication et les avertissements associés au candidat sélectionné.

## Protocole `--shell`

Le mode `-s` ou `--shell` est destiné aux wrappers et aux intégrations shell :

```bash
everycli search "annuler mon dernier commit" --shell
```

Dans ce mode, `stdout` contient uniquement la commande résolue, sans newline final. Les informations de diagnostic sont envoyées sur `stderr`. Cela permet à un wrapper de capturer la commande sans mélanger les explications à sa valeur de retour.

`--shell` ne demande pas de confirmation et n’exécute pas la commande. Le wrapper doit seulement placer la commande dans un buffer éditable ou l’afficher pour copie. Il ne doit pas utiliser `eval` par défaut.

Pour conserver un protocole déterministe, `--shell` ne se combine pas avec `-i`, `--run`, `--copy`, `--error` ou `--top` supérieur à `1`.

## Bash et Zsh

Les wrappers Bash et Zsh du dépôt sont destinés à charger l’intégration dans le shell courant. Ils doivent être inspectés avant d’être ajoutés à un fichier de profil :

```bash
sed -n '1,220p' bin/everycli.bash
sed -n '1,260p' bin/everycli.zsh
```

Le principe recommandé est de demander une commande à EveryCli, puis de la placer dans la ligne éditable lorsque le shell le permet. L’utilisateur peut alors modifier la commande et doit confirmer lui-même son exécution.

Après une installation release, les wrappers doivent appeler le binaire installé dans `~/.local/bin`. En développement, `EVERYCLI_BIN` peut être défini pour sélectionner un binaire précis.

## PowerShell

Le wrapper PowerShell historique se trouve dans [`everycli.ps1`](../everycli.ps1). En développement, charge-le dans le terminal courant :

```powershell
. .\everycli.ps1
evc "annuler mon dernier commit sans perdre mes changements"
```

Pour une installation release, `everycli` doit être disponible sur le PATH. Pour un test ciblé, définis `EVERYCLI_BIN` avant de charger le wrapper :

```powershell
$env:EVERYCLI_BIN = "$env:LOCALAPPDATA\EveryCli\bin\everycli.exe"
. .\everycli.ps1
evc "lister les fichiers"
```

Lorsque PSReadLine est disponible, le wrapper place la commande dans le buffer éditable. Sinon, il l’affiche pour copie manuelle. Il ne l’exécute pas automatiquement.

## Sécurité d’exécution

Une intégration shell ne doit jamais transformer silencieusement une sortie de recherche en exécution. Les règles suivantes s’appliquent :

| Action | Comportement recommandé |
|---|---|
| Recherche normale | Afficher la commande et son explication |
| `--copy` | Copier seulement après l’action explicite de l’utilisateur |
| `--run` | Demander une confirmation avant l’exécution |
| `--shell` | Retourner une valeur brute au wrapper, sans exécuter |
| Wrapper interactif | Placer dans un buffer éditable ou afficher |

Les avertissements du corpus doivent rester visibles dans le rendu humain. Un wrapper ne doit pas supprimer `stderr` sans raison, car il pourrait masquer une alerte ou un diagnostic de daemon.

## Diagnostic

Pour inspecter la valeur brute et les diagnostics séparément :

```bash
command=$(everycli search "lister les fichiers" --shell 2>everycli-shell-diagnostics.txt)
printf 'Commande: %s\n' "$command"
cat everycli-shell-diagnostics.txt >&2
```

Cette commande ne lance pas la valeur capturée. Évite `eval "$command"` sauf si ton intégration possède sa propre politique de confirmation et d’échappement.

Pour diagnostiquer le binaire utilisé :

```bash
command -v everycli
printf 'EVERYCLI_BIN=%s\n' "${EVERYCLI_BIN:-non défini}"
```

## Limites

Le support shell dépend des capacités du terminal et de PSReadLine/ZLE. Le chemin de repli sûr est toujours l’affichage de la commande pour validation humaine. Le daemon reste local et le protocole TCP n’est pas destiné à être exposé sur le réseau.
