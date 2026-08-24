#!/usr/bin/env bash
# EveryCli - installeur Linux.
#
# Installation depuis une archive extraite (aucun compilateur Rust requis) :
#   tar -xzf everycli-linux-x86_64.tar.gz
#   cd everycli-linux-x86_64
#   ./install.sh
#
# L’installeur détecte automatiquement le bundle placé à côté de lui.
# Si aucun bundle local n’est présent, il télécharge la release GitHub.
# Test explicite d'un bundle local préparé ailleurs :
#   ./install.sh --local-source "dist/linux"

set -euo pipefail

REPOSITORY="HE11032006/EveryCli"
VERSION="latest"
LOCAL_SOURCE=""
INSTALL_DIR="$HOME/.local/share/everycli"
LANGUAGE=""
TEMP_DIR=""

usage() {
    cat <<'EOF'
Usage : ./install.sh [options]

Sans --local-source, télécharge l'archive Linux x86_64 de la release GitHub,
puis vérifie son SHA-256 avant extraction. Rust n'est pas requis.

Options :
  --version VERSION       Release à installer (latest ou vX.Y.Z)
  --local-source DIR      Utiliser un bundle local déjà assemblé
  --install-dir DIR       Dossier d'installation (défaut : ~/.local/share/everycli)
  --language en|fr        Langue sans question interactive
  --help                  Afficher cette aide
EOF
}

cleanup() {
    if [[ -n "$TEMP_DIR" && -d "$TEMP_DIR" ]]; then
        rm -rf "$TEMP_DIR"
    fi
}
trap cleanup EXIT

while [[ $# -gt 0 ]]; do
    case "$1" in
        --version)
            [[ $# -ge 2 ]] || { echo "--version nécessite une valeur." >&2; exit 1; }
            VERSION="$2"
            shift 2
            ;;
        --local-source)
            [[ $# -ge 2 ]] || { echo "--local-source nécessite un dossier." >&2; exit 1; }
            LOCAL_SOURCE="$2"
            shift 2
            ;;
        --install-dir)
            [[ $# -ge 2 ]] || { echo "--install-dir nécessite un chemin." >&2; exit 1; }
            INSTALL_DIR="$2"
            shift 2
            ;;
        --language|--lang)
            [[ $# -ge 2 ]] || { echo "--language nécessite en ou fr." >&2; exit 1; }
            LANGUAGE="$2"
            shift 2
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        *)
            echo "Option inconnue : $1" >&2
            usage >&2
            exit 1
            ;;
    esac
done

if [[ -z "$LANGUAGE" ]]; then
    echo ""
    echo "Select language / Choisissez votre langue :"
    echo "  [1] English (default / defaut)"
    echo "  [2] Francais"
    # Avec `curl ... | bash`, stdin contient le script lui-même : lire la
    # réponse depuis /dev/tty évite de consommer les lignes suivantes du script.
    if [[ -r /dev/tty ]]; then
        read -rp "Choice / Choix [1-2]: " choice </dev/tty || choice=""
    else
        choice=""
    fi
    if [[ "$choice" == "2" || "$choice" == "fr" || "$choice" == "Français" ]]; then
        LANGUAGE="fr"
    else
        LANGUAGE="en"
    fi
fi
case "$LANGUAGE" in
    en|fr) ;;
    *) echo "Langue invalide : $LANGUAGE (valeurs attendues : en ou fr)." >&2; exit 1 ;;
esac

echo "=== Installation d'EveryCli / EveryCli Setup ==="

# --- 1. Obtenir et vérifier les fichiers (bundle local ou release GitHub) ---
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [[ -n "$LOCAL_SOURCE" ]]; then
    if [[ ! -d "$LOCAL_SOURCE" ]]; then
        echo "Dossier source introuvable : $LOCAL_SOURCE" >&2
        exit 1
    fi
    SOURCE="$LOCAL_SOURCE"
    echo "Source locale : $SOURCE"
elif [[ -d "$SCRIPT_DIR/bin" ]]; then
    SOURCE="$SCRIPT_DIR"
    echo "Bundle local détecté à côté de l'installeur : $SOURCE"
else
    if [[ "$VERSION" == "latest" ]]; then
        RELEASE_BASE="https://github.com/$REPOSITORY/releases/latest/download"
    else
        RELEASE_TAG="${VERSION#v}"
        if [[ -z "$RELEASE_TAG" ]]; then
            echo "Version invalide : $VERSION" >&2
            exit 1
        fi
        RELEASE_BASE="https://github.com/$REPOSITORY/releases/download/v$RELEASE_TAG"
    fi

    ARCHIVE="everycli-linux-x86_64.tar.gz"
    TEMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/everycli-install.XXXXXX")"
    ARCHIVE_PATH="$TEMP_DIR/$ARCHIVE"
    CHECKSUMS_PATH="$TEMP_DIR/SHA256SUMS"
    EXTRACT_DIR="$TEMP_DIR/extracted"
    mkdir -p "$EXTRACT_DIR"

    download() {
        local url="$1"
        local destination="$2"
        if command -v curl >/dev/null 2>&1; then
            curl --fail --location --retry 3 --proto '=https' --tlsv1.2 "$url" -o "$destination"
        elif command -v wget >/dev/null 2>&1; then
            wget --https-only --tries=3 --output-document="$destination" "$url"
        else
            echo "curl ou wget est requis pour télécharger EveryCli." >&2
            exit 1
        fi
    }

    echo "Téléchargement de EveryCli $VERSION pour Linux x86_64..."
    download "$RELEASE_BASE/$ARCHIVE" "$ARCHIVE_PATH"
    download "$RELEASE_BASE/SHA256SUMS" "$CHECKSUMS_PATH"

    expected_hash="$(awk -v name="$ARCHIVE" '$2 == name { print $1; exit }' "$CHECKSUMS_PATH")"
    if [[ ! "$expected_hash" =~ ^[[:xdigit:]]{64}$ ]]; then
        echo "SHA-256 introuvable pour $ARCHIVE dans SHA256SUMS." >&2
        exit 1
    fi

    if command -v sha256sum >/dev/null 2>&1; then
        actual_hash="$(sha256sum "$ARCHIVE_PATH" | awk '{print $1}')"
    elif command -v shasum >/dev/null 2>&1; then
        actual_hash="$(shasum -a 256 "$ARCHIVE_PATH" | awk '{print $1}')"
    else
        echo "sha256sum ou shasum est requis pour vérifier l'archive." >&2
        exit 1
    fi
    if [[ "${actual_hash,,}" != "${expected_hash,,}" ]]; then
        echo "Échec de vérification SHA-256 pour $ARCHIVE." >&2
        exit 1
    fi
    echo "Archive vérifiée (SHA-256)."

    tar -xzf "$ARCHIVE_PATH" -C "$EXTRACT_DIR"
    SOURCE="$EXTRACT_DIR"
    shopt -s nullglob
    extracted_entries=("$SOURCE"/*)
    if [[ ! -d "$SOURCE/bin" && "${#extracted_entries[@]}" -eq 1 && -d "${extracted_entries[0]}" ]]; then
        SOURCE="${extracted_entries[0]}"
    fi
    shopt -u nullglob
fi

# Refuser de supprimer une installation existante si la source est incomplète.
required_paths=(
    "bin/everycli"
    "bin/everycli-daemon"
    "model/model.onnx"
    "model/tokenizer.json"
    "runtime/libonnxruntime.so"
    "data/commands"
)
for relative_path in "${required_paths[@]}"; do
    if [[ ! -e "$SOURCE/$relative_path" ]]; then
        echo "Bundle incomplet : fichier ou dossier absent : $relative_path" >&2
        exit 1
    fi
done

# --- 2. Copier vers le dossier d'installation ---
echo "Installation dans $INSTALL_DIR..."
# Arrête l'ancienne instance avant de remplacer ses binaires.
systemctl --user stop everycli-daemon.service 2>/dev/null || true
rm -rf "$INSTALL_DIR"
mkdir -p "$INSTALL_DIR/logs"
cp -r "$SOURCE/bin" "$INSTALL_DIR/"
cp -r "$SOURCE/model" "$INSTALL_DIR/"
cp -r "$SOURCE/runtime" "$INSTALL_DIR/"
cp -r "$SOURCE/data" "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/bin/everycli" "$INSTALL_DIR/bin/everycli-daemon"

# --- 3. Symlinks dans ~/.local/bin ---
mkdir -p "$HOME/.local/bin"
ln -sf "$INSTALL_DIR/bin/everycli" "$HOME/.local/bin/everycli"
ln -sf "$INSTALL_DIR/bin/everycli-daemon" "$HOME/.local/bin/everycli-daemon"

# --- 4. PATH et variables persistantes dans ~/.profile ---
PROFILE="$HOME/.profile"
PATH_LINE='export PATH="$HOME/.local/bin:$PATH"'
PATH_MARKER="# EveryCli PATH (managed by installer)"
touch "$PROFILE"
if ! grep -Fq "$PATH_LINE" "$PROFILE"; then
    echo "Ajout de ~/.local/bin au PATH dans $PROFILE..."
    { echo ""; echo "$PATH_MARKER"; echo "$PATH_LINE"; } >> "$PROFILE"
fi

ENV_LINES="export EVERYCLI_MODEL_DIR=\"$INSTALL_DIR/model\"
export EVERYCLI_ONNXRUNTIME_DYLIB=\"$INSTALL_DIR/runtime/libonnxruntime.so\"
export EVERYCLI_DATA_DIR=\"$INSTALL_DIR/data/commands\"
export EVERYCLI_USER_DATA_DIR=\"$HOME/.everycli/commands\""
ENV_MARKER="# EveryCli environment (managed by installer)"
if ! grep -Fq "$ENV_MARKER" "$PROFILE"; then
    { echo ""; echo "$ENV_MARKER"; echo "$ENV_LINES"; } >> "$PROFILE"
fi
mkdir -p "$HOME/.everycli/commands"

# --- 5. Service systemd --user ---
echo "Installation du service systemd --user..."
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"
mkdir -p "$SYSTEMD_USER_DIR"
cat > "$SYSTEMD_USER_DIR/everycli-daemon.service" <<EOF
[Unit]
Description=EveryCli daemon (recherche semantique de commandes)
After=network.target

[Service]
Type=simple
ExecStart=$INSTALL_DIR/bin/everycli-daemon
Environment=EVERYCLI_MODEL_DIR=$INSTALL_DIR/model
Environment=EVERYCLI_ONNXRUNTIME_DYLIB=$INSTALL_DIR/runtime/libonnxruntime.so
Environment=EVERYCLI_DATA_DIR=$INSTALL_DIR/data/commands
Environment=EVERYCLI_USER_DATA_DIR=$HOME/.everycli/commands
StandardOutput=append:$INSTALL_DIR/logs/daemon.log
StandardError=append:$INSTALL_DIR/logs/daemon.log
Restart=on-failure
RestartSec=2

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable --now everycli-daemon.service

# --- 6. Attendre que le daemon réponde vraiment ---
wait_for_daemon() {
    # Le chargement du modèle float32 peut dépasser 30 secondes sur une
    # machine modeste ou dans WSL. On attend jusqu'à 3 minutes sans afficher
    # les diagnostics bruyants de /dev/tcp à chaque tentative.
    local timeout_attempts=360
    local attempt=0
    while [[ $attempt -lt $timeout_attempts ]]; do
        local response=""
        if response=$(timeout 3 bash -c '
            exec 3<>/dev/tcp/127.0.0.1/51821 || exit 1
            printf "%s\n" '\''{"action":"ping"}'\'' >&3
            head -n1 <&3
        ' 2>/dev/null); then
            if [[ "$response" == *'"pong":true'* ]]; then
                return 0
            fi
        fi
        sleep 0.5
        attempt=$((attempt + 1))
    done
    return 1
}

echo "Attente que le daemon soit prêt (calcul des embeddings du corpus, jusqu'à ~3 min au premier démarrage)..."
if wait_for_daemon; then
    echo "Daemon prêt, cache d'embeddings calculé et écrit sur disque."
else
    echo "Le daemon ne répond pas encore après 3 min -- vérifie : systemctl --user status everycli-daemon.service"
    echo "et les logs : $INSTALL_DIR/logs/daemon.log"
    echo "everycli fonctionnera quand même en mode recherche locale en attendant."
fi

# --- 7. Enregistrer la préférence de langue ---
USER_CONFIG_DIR="$HOME/.everycli"
mkdir -p "$USER_CONFIG_DIR"
USER_CONFIG_FILE="$USER_CONFIG_DIR/config.toml"
if [[ -f "$USER_CONFIG_FILE" ]]; then
    if ! grep -q 'language[[:space:]]*=' "$USER_CONFIG_FILE"; then
        echo "language = \"$LANGUAGE\"" >> "$USER_CONFIG_FILE"
    else
        sed -i -E "s/language[[:space:]]*=[[:space:]]*\"[^\"]*\"/language = \"$LANGUAGE\"/" "$USER_CONFIG_FILE"
    fi
else
    echo "language = \"$LANGUAGE\"" > "$USER_CONFIG_FILE"
fi

echo ""
echo "=== Installation terminée / Setup complete ==="
echo "Rust n'était pas nécessaire : l'archive contient les binaires, le modèle et le runtime."
echo "Language / Langue : $( [[ "$LANGUAGE" == "fr" ]] && echo "Français" || echo "English" )"
echo "Ouvre un NOUVEAU terminal (ou lance : source ~/.profile) et tape / Open a NEW terminal and type : everycli search <query>"
echo "Logs du daemon : $INSTALL_DIR/logs/daemon.log"
echo "Statut du service : systemctl --user status everycli-daemon.service"
