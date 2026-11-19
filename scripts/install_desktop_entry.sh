#!/usr/bin/env bash
# Uygulama menüsüne kısayol ekler; proje yolu kurulum anında hesaplanır.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UV="$(command -v uv || echo "$HOME/.local/bin/uv")"
DEST="$HOME/.local/share/applications/kisisel-not-arama.desktop"
mkdir -p "$(dirname "$DEST")"
cat > "$DEST" <<DESKTOP
[Desktop Entry]
Type=Application
Name=Kişisel Not Arama
Comment=Notlarına soru sor (yerel RAG)
Path=$ROOT
Exec=$UV run python -m desktop.main
Terminal=false
Categories=Office;Utility;
DESKTOP
chmod +x "$DEST"
echo "Yazıldı: $DEST"
