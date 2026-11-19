"""Sohbet geçmişi deposu: ${XDG_DATA_HOME:-~/.local/share}/kisisel-not-arama/chats/<id>.json"""
import json
import os
import re
import uuid
from datetime import datetime
from pathlib import Path

_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def chats_dir() -> Path:
    base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base) / "kisisel-not-arama" / "chats"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _path(chat_id) -> Path | None:
    if not isinstance(chat_id, str) or not _ID_RE.match(chat_id):
        return None
    return chats_dir() / f"{chat_id}.json"


def title_from(question: str) -> str:
    lines = (question or "").strip().splitlines()
    line = " ".join(lines[0].split()) if lines else ""
    if len(line) <= 40:
        return line
    cut = line[:40]
    if line[40] != " " and " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    return cut.rstrip(" ,.;:-") + "…"


def new_chat(notes_dir: str) -> dict:
    now = _now()
    return {
        "id": datetime.now().strftime("%Y%m%d%H%M%S") + "-" + uuid.uuid4().hex[:6],
        "title": "", "created": now, "updated": now,
        "notes_dir": str(notes_dir), "messages": [],
    }


def save_chat(chat: dict) -> None:
    p = _path(chat.get("id"))
    if p is None:
        raise ValueError(f"Geçersiz sohbet kimliği: {chat.get('id')!r}")
    if not chat.get("title"):
        first = next((m for m in chat.get("messages", []) if m.get("role") == "user"), None)
        if first:
            chat["title"] = title_from(first.get("text", ""))
    chat["updated"] = _now()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(f".{uuid.uuid4().hex[:6]}.tmp")
    tmp.write_text(json.dumps(chat, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, p)


def load_chat(chat_id: str) -> dict | None:
    p = _path(chat_id)
    if p is None:
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or not isinstance(data.get("messages"), list):
        return None
    data["messages"] = [m for m in data["messages"] if isinstance(m, dict)]
    for k in ("title", "updated"):
        if not isinstance(data.get(k), str):
            data[k] = ""
    data["id"] = chat_id
    return data


def list_chats() -> list[dict]:
    out = []
    d = chats_dir()
    if not d.is_dir():
        return out
    for f in d.glob("*.json"):
        c = load_chat(f.stem)
        if not c or not c["messages"]:
            continue
        out.append({"id": c["id"], "title": c.get("title", ""),
                    "updated": c.get("updated", ""), "n_messages": len(c["messages"])})
    out.sort(key=lambda c: c["updated"], reverse=True)
    return out


def delete_chat(chat_id: str) -> None:
    p = _path(chat_id)
    if p is not None:
        p.unlink(missing_ok=True)


def delete_all() -> None:
    d = chats_dir()
    if d.is_dir():
        for f in d.glob("*.json"):
            f.unlink(missing_ok=True)


def rename_chat(chat_id: str, title: str) -> None:
    c = load_chat(chat_id)
    if c is None:
        return
    c["title"] = title.strip()
    updated = c.get("updated")
    save_chat(c)
    if updated:  # yeniden adlandırma sıralamayı değiştirmesin
        c["updated"] = updated
        p = _path(chat_id)
        p.write_text(json.dumps(c, ensure_ascii=False, indent=2), encoding="utf-8")


def sources_from_results(results) -> list[dict]:
    out = []
    for chunk, score in results:
        page = getattr(chunk, "page", None)
        out.append({
            "source": getattr(chunk, "source", ""),
            "heading": getattr(chunk, "heading", "") or "",
            "page": int(page) if page is not None else None,
            "score": float(score),
            "text": getattr(chunk, "text", ""),
        })
    return out


def last_notes_message(messages) -> dict | None:
    """Takip/kaynak sorusunun dayanacağı son asistan mesajı: niyeti notes/followup (niyetsiz = eski kayıt)
    ve kaynağı olan. Kaynak listesi (sources) ve meta cevapları atlanır."""
    for m in reversed(messages or []):
        if m.get("role") != "assistant" or m.get("intent", "notes") not in ("notes", "followup"):
            continue
        if m.get("below_threshold"):
            continue
        if any(isinstance(s, dict) for s in (m.get("sources") or [])):
            return m
    return None
