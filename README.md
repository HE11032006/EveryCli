# 🚀 EveryCli

**Ne cherchez plus vos commandes, décrivez-les.**

EveryCli est un assistant de ligne de commande intelligent qui utilise l'IA pour trouver instantanément la commande exacte dont vous avez besoin, même si vous ne connaissez pas sa syntaxe.

![License](https://img.shields.io/github/license/HE11032006/EveryCli)
![Build Status](https://img.shields.io/github/actions/workflow/status/HE11032006/EveryCli/build.yml)
![Platform](https://img.shields.io/badge/platform-linux%20%7C%20macos%20%7C%20windows-lightgrey)

## ✨ Caractéristiques

- **Recherche Sémantique** : Comprend l'intention (ex: "annuler commit" → `git reset HEAD~1`).
- **Performance Instantanée** : Architecture Daemon/Client pour des réponses en <50ms.
- **Multi-Plateforme** : Binaires optimisés pour Linux, macOS et Windows.
- **Zéro Dépendance** : Pas besoin d'installer Python ou des modèles IA pour l'utiliser.
- **Extensible** : Ajoutez vos propres commandes via de simples fichiers YAML.

## 🏁 Démarrage Rapide (Release)

1. Téléchargez le binaire pour votre OS sur la page [Releases](https://github.com/HE11032006/EveryCli/releases).
2. Installez le wrapper :
   ```bash
   # Linux / macOS
   sudo ln -s $(pwd)/everycli /usr/local/bin/everycli
   ```
3. Lancez votre première recherche :
   ```bash
   everycli search "comment modifier mon dernier commit"
   ```

## 🛠️ Installation pour Développement

Si vous souhaitez contribuer ou compiler depuis les sources :

```bash
git clone https://github.com/HE11032006/EveryCli.git
cd EveryCli
pip install -r requirements.txt
python3 -m everycli.everycli search "git push"
```

## 🏗️ Architecture

EveryCli utilise une architecture hybride pour concilier l'intelligence des modèles NLP et la réactivité attendue d'un outil CLI.

```mermaid
graph TD
    User([Utilisateur]) --> Wrapper[everycli script/ps1]
    Wrapper --> Client{Daemon vivant ?}
    Client -- Oui --> Socket(TCP Socket)
    Client -- Non --> Binary[everycli-daemon bin]
    Socket --> Daemon[Daemon Engine]
    Daemon --> Matcher[Hybrid Matcher IA + TF-IDF]
    Matcher --> YAML[(YAML Database)]
```

> [!IMPORTANT]
> Le premier lancement après un redémarrage démarre automatiquement le Daemon. Les recherches suivantes seront quasi-instantanées car le modèle IA reste chargé en mémoire.

## ⚙️ Configuration

Vous pouvez personnaliser EveryCli via des variables d'environnement :
- `EVERYCLI_PORT` : Port du daemon (défaut: 51821).
- `EVERYCLI_DEBUG` : Mode verbeux pour le dépannage.

---
*Fait avec ❤️ pour simplifier la vie des développeurs.*
