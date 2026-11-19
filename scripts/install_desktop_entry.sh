#!/usr/bin/env bash
# Uygulama menüsüne kısayol + ikon ekler; proje yolu kurulum anında hesaplanır.
set -euo pipefail
APP_ID="kisisel-not-arama"   # desktop/main.py içindeki APP_ID ile aynı olmalı
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UV="$(command -v uv || echo "$HOME/.local/bin/uv")"
DATA="${XDG_DATA_HOME:-$HOME/.local/share}"

# İkonu kullanıcı ikon temasına ada göre kur (GNOME yol yerine adla daha iyi önbellekler)
ICON_DIR="$DATA/icons/hicolor/scalable/apps"
mkdir -p "$ICON_DIR"
cp "$ROOT/desktop/icon.svg" "$ICON_DIR/$APP_ID.svg"

DEST="$DATA/applications/$APP_ID.desktop"
mkdir -p "$(dirname "$DEST")"
cat > "$DEST" <<DESKTOP
[Desktop Entry]
Type=Application
Name=Kişisel Not Arama
Comment=Notlarına soru sor (yerel RAG)
Path=$ROOT
Exec="$UV" run --project "$ROOT" python -m desktop.main
Icon=$APP_ID
Terminal=false
Categories=Office;Utility;
StartupWMClass=$APP_ID
DESKTOP
chmod +x "$DEST"

# Önbellekleri tazele (araç yoksa sessizce geç)
touch "$DATA/icons/hicolor"
gtk-update-icon-cache -f -t "$DATA/icons/hicolor" >/dev/null 2>&1 || true
update-desktop-database "$DATA/applications" >/dev/null 2>&1 || true
echo "Kuruldu: $DEST"
