#!/usr/bin/env bash
# EveryCli - désinstalleur Linux.
#
# Usage :
#   ./uninstall.sh
#   ./uninstall.sh --remove-user-commands
#
# Par défaut, les commandes personnalisées et la configuration dans
# ~/.everycli sont conservées. Utilise --remove-user-commands uniquement si tu
# veux supprimer ces données explicitement.

set -euo pipefail

INSTALL_DIR="${EVERYCLI_INSTALL_DIR:-$HOME/.local/share/everycli}"
REMOVE_USER_COMMANDS=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --remove-user-commands|--remove-user-data)
            REMOVE_USER_COMMANDS=true
            shift
            ;;
        --install-dir)
            [[ $# -ge 2 ]] || { echo "--install-dir nécessite un chemin." >&2; exit 1; }
            INSTALL_DIR="$2"
            shift 2
            ;;
        *)
            echo "Option inconnue : $1" >&2
            exit 1
            ;;
    esac
done

echo "=== Désinstallation d'EveryCli ==="

echo "Dossier d'installation : $INSTALL_DIR"

# --- 1. Arrêter et retirer le service systemd utilisateur ---
if systemctl --user is-enabled everycli-daemon.service >/dev/null 2>&1 || \
   systemctl --user is-active everycli-daemon.service >/dev/null 2>&1; then
    echo "Arrêt du service systemd utilisateur..."
    systemctl --user disable --now everycli-daemon.service >/dev/null 2>&1 || true
fi

SERVICE_FILE="$HOME/.config/systemd/user/everycli-daemon.service"
if [[ -f "$SERVICE_FILE" ]]; then
    rm -f "$SERVICE_FILE"
    systemctl --user daemon-reload >/dev/null 2>&1 || true
fi

# --- 2. Retirer les liens créés par EveryCli ---
for name in everycli everycli-daemon; do
    link="$HOME/.local/bin/$name"
    if [[ -L "$link" ]]; then
        target=$(readlink -f "$link" 2>/dev/null || true)
        if [[ "$target" == "$INSTALL_DIR/bin/$name" ]]; then
            rm -f "$link"
        fi
    fi
done

# --- 3. Retirer uniquement les blocs ajoutés par l'installeur du profil ---
PROFILE="$HOME/.profile"
PATH_MARKER="# EveryCli PATH (managed by installer)"
ENV_MARKER="# EveryCli environment (managed by installer)"
if [[ -f "$PROFILE" ]] && { grep -Fq "$PATH_MARKER" "$PROFILE" || grep -Fq "$ENV_MARKER" "$PROFILE"; }; then
    tmp_profile=$(mktemp)
    awk -v path_marker="$PATH_MARKER" -v env_marker="$ENV_MARKER" '
        $0 == path_marker { skip_path = 1; next }
        skip_path && $0 ~ /^[[:space:]]*$/ { skip_path = 0; next }
        skip_path { next }
        $0 == env_marker { skip_env = 1; next }
        skip_env && $0 ~ /^[[:space:]]*$/ { skip_env = 0; next }
        skip_env { next }
        { print }
    ' "$PROFILE" > "$tmp_profile"
    mv "$tmp_profile" "$PROFILE"
fi

# --- 4. Supprimer les fichiers d'installation ---
if [[ -d "$INSTALL_DIR" ]]; then
    echo "Suppression de $INSTALL_DIR..."
    rm -rf "$INSTALL_DIR"
fi

# --- 5. Données personnelles : conservées par défaut ---
if [[ "$REMOVE_USER_COMMANDS" == true ]]; then
    if [[ -d "$HOME/.everycli" ]]; then
        echo "Suppression des commandes et de la configuration utilisateur..."
        rm -rf "$HOME/.everycli"
    fi
else
    echo "Les commandes personnalisées sont conservées dans $HOME/.everycli"
    echo "Relance avec --remove-user-commands pour les supprimer explicitement."
fi

echo ""
echo "=== EveryCli désinstallé ==="
echo "Ouvre un nouveau terminal pour actualiser le PATH."
