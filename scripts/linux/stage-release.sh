#!/usr/bin/env bash
# Assemble un dossier "dist/linux" qui imite ce qu'une vraie release GitHub
# contiendrait — sert à tester install.sh localement, et deviendra la base
# du job de packaging CI plus tard. Miroir de scripts/windows/stage-release.ps1.
#
# Usage (depuis la racine du repo) :
#   ./scripts/linux/stage-release.sh
#
# Prérequis : avoir déjà compilé en release et exporté le modèle (Axe 1) :
#   cd rust && cargo build --release -p everycli-rs -p everycli-daemon

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DIST="$REPO_ROOT/dist/linux"

echo "Nettoyage de $DIST..."
rm -rf "$DIST"
mkdir -p "$DIST/bin" "$DIST/model" "$DIST/runtime" "$DIST/data/commands"

echo "Copie des binaires..."
RELEASE_DIR="$REPO_ROOT/rust/target/release"
cp "$RELEASE_DIR/everycli-rs" "$DIST/bin/everycli"
cp "$RELEASE_DIR/everycli-daemon" "$DIST/bin/everycli-daemon"

echo "Copie du modèle ONNX..."
MODEL_SRC="$REPO_ROOT/rust/onnx-bench/models/everycli-minilm-ft"
cp "$MODEL_SRC/model.onnx" "$DIST/model/"
cp "$MODEL_SRC/tokenizer.json" "$DIST/model/"

echo "Copie du runtime ONNX..."
cp "$REPO_ROOT/rust/onnx-bench/runtime/libonnxruntime.so"* "$DIST/runtime/libonnxruntime.so"

echo "Copie du corpus de commandes..."
cp "$REPO_ROOT/everycli/data/commands/"*.yaml "$DIST/data/commands/"

SIZE=$(du -sh "$DIST" | cut -f1)
echo ""
echo "Assemblé dans $DIST ($SIZE)"
echo "Teste l'installeur avec :"
echo "  ./install.sh --local-source \"$DIST\""
