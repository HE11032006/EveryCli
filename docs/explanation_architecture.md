# Architecture d’EveryCli

Ce document décrit les composants permanents du projet et leurs frontières. Il explique pourquoi EveryCli utilise un daemon local, comment le ranking combine plusieurs signaux et où se trouvent les données distribuées.

## Vue d’ensemble

EveryCli sépare l’interface CLI du calcul sémantique coûteux :

```text
Utilisateur
    │
    ▼
everycli-rs  ── JSON/TCP localhost ──>  everycli-daemon
    │                                      │
    │                                      ├── corpus YAML
    │                                      ├── model.onnx
    │                                      ├── tokenizer.json
    │                                      └── ONNX Runtime natif
    │
    └── repli local si le daemon est indisponible
```

| Composant | Responsabilité | Technologie |
|---|---|---|
| `everycli-rs` | Parsing des options, affichage, actions utilisateur et repli local | Rust |
| `everycli-core` | Corpus, parsing YAML, recherche lexicale et résolution de daemon | Rust |
| `everycli-inference` | Tokenisation, chargement ONNX et embeddings | Rust + ONNX Runtime |
| `everycli-daemon` | Serveur local, cache et recherche hybride | Rust, TCP localhost |
| Sentinel | Planification et revue de commandes avec un LLM | Python |
| Corpus intégré | Scénarios de commandes par domaine | YAML |

## Pourquoi un daemon local ?

Le modèle sémantique doit être chargé et initialisé avant de produire des embeddings. Refaire cette opération pour chaque commande rendrait l’outil interactif inutilisable. Le daemon garde donc le modèle et le cache en mémoire, puis répond aux recherches du client.

Le daemon écoute uniquement sur `127.0.0.1:51821`. Il n’est pas conçu comme une API réseau publique ou un service multi-utilisateur. Sous Linux, son cycle de vie est géré par `systemd --user`. Sous Windows, l’installeur peut configurer le service Windows ou le dossier de démarrage selon les permissions et l’option choisie.

Le premier chargement peut être long, en particulier sur une machine modeste ou sous WSL. Une fois le corpus encodé, un cache disque est utilisé lorsque le modèle et les données correspondent.

## Protocole client-daemon

Le protocole est une ligne JSON par requête et par réponse. Les actions principales sont :

| Action | Objet |
|---|---|
| `ping` | Vérifier que le daemon répond |
| `search` | Rechercher des commandes et renvoyer les scores et métadonnées |
| `reload` | Recharger le corpus et recalculer les embeddings nécessaires |

Le client tente de joindre le daemon. Si celui-ci n’est pas disponible, le client peut rechercher localement avec le matcher lexical et peut tenter de relancer le daemon selon le contexte. Les erreurs de reload indiquent désormais la cause connue plutôt qu’un simple message générique.

## Recherche hybride

EveryCli calcule plusieurs signaux :

1. Le score lexical mesure les recouvrements entre la requête, la description, les tags et les métadonnées du scénario.
2. Le score sémantique compare l’embedding de la requête avec les embeddings des scénarios grâce à `model.onnx`.
3. Le bonus de namespace favorise un domaine explicite comme Git ou Docker, sans exclure les autres namespaces.

Le score hybride actuellement utilisé est calibré empiriquement : score lexical `0.45`, score sémantique `0.55`, bonus de namespace `+0.2` lorsque la route du domaine s’applique. Un seuil minimal de pertinence de `0.50` permet de rejeter les requêtes manifestement hors sujet.

Le benchmark `eval/confusion_set.yaml` sert à comparer les évolutions. Le résultat enregistré pendant le travail de release est de 58 requêtes réussies sur 66, soit 87,9 %. Cette mesure ne constitue pas une garantie pour toutes les requêtes possibles.

## Modèle et runtime

`model.onnx` contient le graphe et les poids du modèle exporté. Il n’est pas compilé en Rust. Rust fournit le code qui charge le graphe et appelle ONNX Runtime.

Le dépôt de distribution du modèle est [`Michelhe/everycli-minilm-ft-boosted-onnx`](https://huggingface.co/Michelhe/everycli-minilm-ft-boosted-onnx). Le workflow CI verrouille une révision et vérifie les SHA-256 de `model.onnx` et `tokenizer.json`.

Le runtime est natif et dépend de la plateforme :

```text
Windows : onnxruntime.dll
Linux   : libonnxruntime.so
```

Ces bibliothèques sont placées à côté des binaires dans l’archive release. Elles ne doivent pas être mélangées entre plateformes.

## Corpus et commandes personnelles

Le corpus intégré se trouve dans `everycli/data/commands/`. Le nom du fichier YAML détermine le namespace. Les entrées fournissent notamment une description, des tags, une commande par plateforme, une explication et éventuellement un avertissement.

Les commandes créées avec `everycli add` sont stockées dans `~/.everycli/commands` sous Linux et `%USERPROFILE%\.everycli\commands` sous Windows. Elles sont chargées en plus du corpus intégré et ne sont pas écrasées par une mise à jour.

L’action `reload` permet au daemon de prendre en compte ces changements sans redémarrage complet.

## Sentinel

Sentinel, accessible dans le flux Python du projet, est séparé du chemin de recherche Rust. Il peut utiliser un LLM pour formuler une revue de commande, mais il ne remplace pas le corpus local et n’exécute pas la commande à la place de l’utilisateur.

## Distribution

Une archive complète contient les éléments suivants :

```text
bin/       client et daemon compilés pour la plateforme
model/     model.onnx et tokenizer.json
runtime/   bibliothèque ONNX Runtime native
data/     corpus intégré
scripts    installateur et désinstalleur de la plateforme
```

L’utilisateur final reçoit des binaires déjà compilés. Rust et Python sont nécessaires pour le développement ou la CI, pas pour installer une release.
