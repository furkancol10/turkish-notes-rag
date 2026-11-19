#!/usr/bin/env bash
# Menü kısayolunu ve ikonu kaldırır (proje dosyalarına dokunmaz).
set -euo pipefail
APP_ID="kisisel-not-arama"
DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
rm -f "$DATA/applications/$APP_ID.desktop" "$DATA/icons/hicolor/scalable/apps/$APP_ID.svg"
gtk-update-icon-cache -f -t "$DATA/icons/hicolor" >/dev/null 2>&1 || true
update-desktop-database "$DATA/applications" >/dev/null 2>&1 || true
echo "Kaldırıldı: $APP_ID"
