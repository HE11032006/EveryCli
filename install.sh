#!/usr/bin/env bash
# EveryCli - installeur Linux. Miroir de install.ps1 (Windows).
#
# Usage :
#   Test local (avant qu'une vraie release existe) :
#     ./install.sh --local-source "dist/linux"
#
# Ce que ça fait :
#   1. Place les binaires/modèle/runtime/corpus dans ~/.local/share/everycli
#   2. Symlink les binaires dans ~/.local/bin (déjà dans le PATH sur la
#      plupart des distributions récentes), + ajout en secours dans
#      ~/.profile pour les cas où ce ne serait pas déjà le cas
#   3. Installe et active un service systemd --user (démarre au login,
#      redémarre automatiquement en cas de crash) — pas d'équivalent au
#      blocage de permissions rencontré avec le Planificateur de tâches
#      Windows, systemd --user est prévu pour ce cas d'usage
#   4. Attend que le daemon réponde réellement avant d'annoncer le succès
#      (pas un délai fixe arbitraire)

set -euo pipefail

LOCAL_SOURCE=""
INSTALL_DIR="$HOME/.local/share/everycli"
LANGUAGE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --local-source) LOCAL_SOURCE="$2"; shift 2 ;;
        --install-dir) INSTALL_DIR="$2"; shift 2 ;;
        --language|--lang) LANGUAGE="$2"; shift 2 ;;
        *) echo "Option inconnue : $1" >&2; exit 1 ;;
    esac
done

echo "=== Installation d'EveryCli / EveryCli Setup ==="

if [[ -z "$LANGUAGE" ]]; then
    echo ""
    echo "Select language / Choisissez votre langue :"
    echo "  [1] English (default / defaut)"
    echo "  [2] Francais"
    read -rp "Choice / Choix [1-2]: " choice || choice=""
    if [[ "$choice" == "2" || "$choice" == "fr" || "$choice" == "Français" ]]; then
        LANGUAGE="fr"
    else
        LANGUAGE="en"
    fi
fi

# --- 1. Obtenir les fichiers (local ou téléchargement) ---
if [[ -n "$LOCAL_SOURCE" ]]; then
    if [[ ! -d "$LOCAL_SOURCE" ]]; then
        echo "Dossier source introuvable : $LOCAL_SOURCE" >&2
        exit 1
    fi
    echo "Source locale : $LOCAL_SOURCE"
    SOURCE="$LOCAL_SOURCE"
else
    # NOTE : pas encore de release GitHub publique avec les binaires Rust.
    # Utilise --local-source avec un dossier préparé par
    # scripts/linux/stage-release.sh en attendant.
    echo "Le téléchargement depuis une release GitHub n'est pas encore disponible. Utilise --local-source." >&2
    exit 1
fi

# --- 2. Copier vers le dossier d'installation ---
echo "Installation dans $INSTALL_DIR..."
# Arrête l’ancienne instance avant de remplacer ses binaires.
systemctl --user stop everycli-daemon.service 2>/dev/null || true
rm -rf "$INSTALL_DIR"
mkdir -p "$INSTALL_DIR/logs"
cp -r "$SOURCE/bin" "$INSTALL_DIR/"
cp -r "$SOURCE/model" "$INSTALL_DIR/"
cp -r "$SOURCE/runtime" "$INSTALL_DIR/"
cp -r "$SOURCE/data" "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/bin/everycli" "$INSTALL_DIR/bin/everycli-daemon"

# --- 3. Symlinks dans ~/.local/bin (convention XDG, déjà dans le PATH sur
# la plupart des distributions récentes par défaut) ---
mkdir -p "$HOME/.local/bin"
ln -sf "$INSTALL_DIR/bin/everycli" "$HOME/.local/bin/everycli"
ln -sf "$INSTALL_DIR/bin/everycli-daemon" "$HOME/.local/bin/everycli-daemon"

# --- 4. Filet de sécurité : ajoute quand même au PATH via ~/.profile (idempotent) ---
# Ne fait rien si ~/.local/bin est déjà dans le PATH (cas fréquent) ou si la
# ligne a déjà été ajoutée lors d'une install précédente.
PROFILE="$HOME/.profile"
PATH_LINE='export PATH="$HOME/.local/bin:$PATH"'
PATH_MARKER="# EveryCli PATH (managed by installer)"
touch "$PROFILE"
if ! grep -Fq "$PATH_LINE" "$PROFILE"; then
    echo "Ajout de ~/.local/bin au PATH dans $PROFILE..."
    { echo ""; echo "$PATH_MARKER"; echo "$PATH_LINE"; } >> "$PROFILE"
fi

# Variables d'environnement persistantes — utiles pour lancer
# everycli-daemon manuellement depuis un terminal pour déboguer. Le service
# systemd (plus bas) ne dépend PAS de ces lignes : il a ses propres
# Environment= dans l'unit file.
ENV_LINES="export EVERYCLI_MODEL_DIR=\"$INSTALL_DIR/model\"
export EVERYCLI_ONNXRUNTIME_DYLIB=\"$INSTALL_DIR/runtime/libonnxruntime.so\"
export EVERYCLI_DATA_DIR=\"$INSTALL_DIR/data/commands\"
export EVERYCLI_USER_DATA_DIR=\"$HOME/.everycli/commands\""
ENV_MARKER="# EveryCli environment (managed by installer)"
if [[ -f "$PROFILE" ]] && ! grep -Fq "$ENV_MARKER" "$PROFILE"; then
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

# --- 6. Attendre que le daemon réponde vraiment (pas un délai fixe) ---
wait_for_daemon() {
    local timeout_attempts=60  # 60 * 0.5s = 30s
    local attempt=0
    while [[ $attempt -lt $timeout_attempts ]]; do
        if exec 3<>/dev/tcp/127.0.0.1/51821 2>/dev/null; then
            echo '{"action":"ping"}' >&3
            local response
            response=$(timeout 2 head -n1 <&3 || true)
            exec 3<&- 3>&- 2>/dev/null || true
            if [[ "$response" == *'"pong":true'* ]]; then
                return 0
            fi
        fi
        sleep 0.5
        attempt=$((attempt + 1))
    done
    return 1
}

echo "Attente que le daemon soit prêt (calcul des embeddings du corpus, jusqu'à ~30s au premier démarrage)..."
if wait_for_daemon; then
    echo "Daemon prêt, cache d'embeddings calculé et écrit sur disque."
else
    echo "Le daemon ne répond pas encore après 30s -- vérifie : systemctl --user status everycli-daemon.service"
    echo "et les logs : $INSTALL_DIR/logs/daemon.log"
    echo "everycli fonctionnera quand même en mode recherche locale en attendant."
fi

# --- Enregistrer la preference de langue dans config.toml ---
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
echo "Language / Langue : $( [[ "$LANGUAGE" == "fr" ]] && echo "Français" || echo "English" )"
echo "Ouvre un NOUVEAU terminal (ou lance : source ~/.profile) et tape / Open a NEW terminal and type : everycli search <query>"
echo "Logs du daemon : $INSTALL_DIR/logs/daemon.log"
echo "Statut du service : systemctl --user status everycli-daemon.service"
