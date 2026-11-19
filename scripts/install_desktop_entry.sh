#!/usr/bin/env bash
# Uygulama menüsüne kısayol ekler; proje yolu kurulum anında hesaplanır.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UV="$(command -v uv || echo "$HOME/.local/bin/uv")"
ICON="accessories-text-editor"   # tema ikonu (yedek)
for f in "$ROOT"/desktop/icon.svg "$ROOT"/desktop/icon.png; do [ -f "$f" ] && ICON="$f" && break; done
DEST="$HOME/.local/share/applications/kisisel-not-arama.desktop"
mkdir -p "$(dirname "$DEST")"
cat > "$DEST" <<DESKTOP
[Desktop Entry]
Type=Application
Name=Kişisel Not Arama
Comment=Notlarına soru sor (yerel RAG)
Path=$ROOT
Exec="$UV" run --project "$ROOT" python -m desktop.main
Icon=$ICON
Terminal=false
Categories=Office;Utility;
StartupWMClass=kisisel-not-arama
DESKTOP
chmod +x "$DEST"
echo "Yazıldı: $DEST"
