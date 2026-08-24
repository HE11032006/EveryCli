# Référence de configuration

Cette page décrit les variables d’environnement, les chemins de données, le schéma du corpus et le protocole du daemon. Elle s’adresse aux développeurs et intégrateurs ; le parcours d’installation utilisateur est décrit dans [`tutorial_installation.md`](tutorial_installation.md).

## Variables d’environnement

Les variables doivent être cohérentes entre le client et le daemon lorsque les deux processus doivent utiliser les mêmes fichiers.

| Variable | Rôle | Défaut de développement |
|---|---|---|
| `EVERYCLI_PORT` | Port TCP local du daemon | `51821` |
| `EVERYCLI_TIMEOUT` | Timeout réseau du client, en secondes | `1` |
| `EVERYCLI_DATA_DIR` | Corpus YAML intégré | `../everycli/data/commands` selon le dossier de lancement |
| `EVERYCLI_USER_DATA_DIR` | Corpus YAML personnel | `~/.everycli/commands` |
| `EVERYCLI_MODEL_DIR` | Dossier de `model.onnx` et `tokenizer.json` | `onnx-bench/models/everycli-minilm-ft` |
| `EVERYCLI_ONNXRUNTIME_DYLIB` | Bibliothèque ONNX Runtime dynamique | `onnx-bench/runtime/onnxruntime.dll` ou `.so` selon l’OS |
| `EVERYCLI_LANG` | Langue d’affichage lorsqu’elle est définie | Détection ou français selon le client |
| `EVERYCLI_OFFLINE` | Favorise le fonctionnement sans téléchargement réseau | Non défini |
| `EVERYCLI_API_KEY` | Clé API de `everycli ask` lorsqu’elle n’est pas enregistrée dans la configuration | Non défini |

`everycli ask` utilise aussi les valeurs `api_key`, `api_url`, `api_model` et `provider` du fichier `~/.everycli/config.toml`. Les clés connues peuvent être auto-détectées par leur préfixe ; un fournisseur compatible OpenAI peut être configuré explicitement. Cette configuration concerne le client Rust et ne modifie pas le chemin local de `search`.

Les installeurs remplacent les défauts de développement par des chemins absolus. Sous Linux, les données de l’application se trouvent normalement dans `~/.local/share/everycli`. Sous Windows, elles se trouvent normalement dans `%LOCALAPPDATA%\EveryCli`.

## Fichiers de données

Le corpus intégré est organisé ainsi :

```text
everycli/data/commands/*.yaml
```

Les commandes personnelles sont stockées séparément :

```text
Linux   : ~/.everycli/commands/*.yaml
Windows : %USERPROFILE%\.everycli\commands\*.yaml
```

Le nom du fichier YAML fournit le namespace. Une entrée suit cette forme générale :

```yaml
- id: identifiant_unique
  description: Intention décrite en langage naturel
  tags: [mot-cle, autre-mot]
  commands:
    linux: "commande bash"
    windows: "commande PowerShell"
    macos: "commande shell"
  explanation: Explication affichée avec le résultat
  warning: Avertissement optionnel
```

Le champ `commands` peut contenir une commande spécifique à chaque système. Les explications multi-lignes peuvent utiliser un bloc YAML `|`. Le parseur valide les champs nécessaires et la résolution choisit la commande correspondant à la plateforme courante.

## `everycli ask` et Sentinel

`everycli search` effectue une recherche locale dans le corpus et le daemon Rust ; il ne nécessite aucune clé API. `everycli ask` appelle une API compatible OpenAI avec une requête structurée, puis affiche une commande, une explication, un avertissement éventuel et des tags. Il demande ensuite à l’utilisateur s’il veut enregistrer la proposition dans son corpus personnel.

La clé peut être stockée dans `~/.everycli/config.toml` avec :

```bash
everycli config set api_key "ta-cle-api"
everycli config set provider openai
everycli config set api_url "https://api.openai.com/v1"
everycli config set api_model "gpt-4o-mini"
```

Elle peut aussi être fournie ponctuellement par `EVERYCLI_API_KEY`. Le fichier de configuration est écrit avec des permissions `0600` sous Unix. Ne publie jamais sa valeur dans une issue, un log ou un commit.

Sentinel (`everycli plan`) est un composant Python séparé. Selon son chemin d’exécution, il utilise `OPENAI_API_KEY` et produit une revue de sécurité d’une commande déjà récupérée ; il ne doit pas être confondu avec `everycli ask`.

## Modèle et cache

`EVERYCLI_MODEL_DIR` doit contenir au minimum :

```text
model.onnx
tokenizer.json
```

Le daemon peut générer un cache d’embeddings du corpus dans ce dossier. Ce cache est un artefact local et ne constitue pas une dépendance distribuée obligatoire. Il est invalidé lorsque le contenu pertinent du modèle ou du corpus change.

L’artefact ONNX de production est versionné dans [`Michelhe/everycli-minilm-ft-boosted-onnx`](https://huggingface.co/Michelhe/everycli-minilm-ft-boosted-onnx). La CI fige une révision et vérifie les hashes avant l’assemblage des releases.

## Runtime ONNX

Le nom du runtime dépend du système :

```text
Windows : onnxruntime.dll
Linux   : libonnxruntime.so
```

`EVERYCLI_ONNXRUNTIME_DYLIB` doit pointer vers le fichier réellement présent sur la machine. Le runtime Windows ne peut pas être utilisé par un binaire Linux, et inversement.

## Protocole daemon

Le daemon écoute localement sur `127.0.0.1:${EVERYCLI_PORT}`. Chaque requête et chaque réponse est une ligne JSON terminée par `\n`.

Exemples de requêtes :

```json
{"action":"ping"}
{"action":"search","query":"comment annuler mon dernier commit","top_k":3,"context":null}
{"action":"reload"}
```

Les actions principales sont `ping`, `search` et `reload`. Le client ne doit pas exposer le port sur une interface réseau publique.

## Cycle de vie

Le daemon charge le runtime, le modèle, le tokenizer et le corpus, puis reste en écoute. Le premier chargement peut être long. Sous Linux, `systemd --user` démarre le service à l’ouverture de session. Sous Windows, `install.ps1` configure le service ou le dossier de démarrage selon l’option choisie.

`reload` permet de relire le corpus personnel après `everycli add` ou `everycli remove` sans redémarrer le processus. Le client retombe sur la recherche locale lorsque le daemon est indisponible.

## Résolution du daemon par le client

Le client cherche d’abord le daemon configuré explicitement, puis les noms conventionnels à côté de son propre exécutable. Les binaires installés dans un bundle doivent rester dans le même dossier `bin/` afin de permettre l’auto-détection.

Cette résolution ne remplace pas la configuration du modèle : le daemon doit toujours recevoir les bons chemins `EVERYCLI_MODEL_DIR`, `EVERYCLI_ONNXRUNTIME_DYLIB` et `EVERYCLI_DATA_DIR`.
