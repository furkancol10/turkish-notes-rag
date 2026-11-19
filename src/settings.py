"""Kalıcı kullanıcı ayarları (~/.config/kisisel-not-arama/settings.json) ve etkin not klasörü."""
import json
import os
from pathlib import Path

DEFAULT_NOTES_DIR = Path(__file__).resolve().parent.parent / "data" / "notes"
_override: Path | None = None   # tek seferlik (CLI --notes-dir), dosyaya yazılmaz


def settings_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "kisisel-not-arama" / "settings.json"


def _read() -> dict:
    try:
        data = json.loads(settings_path().read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def get(key: str, default=None):
    return _read().get(key, default)


def set(key: str, value) -> None:  # noqa: A001
    """value None ise anahtarı siler."""
    data = _read()
    if value is None:
        data.pop(key, None)
    else:
        data[key] = value
    p = settings_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def set_override(path) -> None:
    global _override
    _override = Path(path).expanduser() if path else None


def notes_dir() -> Path:
    """Etkin klasör: tek seferlik override > ayar (varsa ve klasörse) > örnek notlar."""
    if _override is not None:
        return _override
    v = get("notes_dir")
    if isinstance(v, str) and v:
        p = Path(v).expanduser()
        if p.is_dir():
            return p
    return DEFAULT_NOTES_DIR


def is_default() -> bool:
    return notes_dir() == DEFAULT_NOTES_DIR


def validate_dir(path) -> Path:
    """Klasörü doğrular; geçersizse ValueError (kullanıcıya gösterilebilir mesajla)."""
    p = Path(str(path)).expanduser()
    if not p.exists():
        raise ValueError(f"Klasör bulunamadı: {p}")
    if not p.is_dir():
        raise ValueError(f"Bu bir klasör değil: {p}")
    if not os.access(p, os.R_OK | os.X_OK):
        raise ValueError(f"Klasör okunamıyor (izin yok): {p}")
    return p.resolve()


def set_notes_dir(path) -> Path:
    p = validate_dir(path)
    set("notes_dir", str(p))
    return p


def reset_notes_dir() -> None:
    set("notes_dir", None)
