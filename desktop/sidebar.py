"""Sol kenar çubuğu: saf arayüz bileşeni (iş mantığı yok)."""
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QFontMetrics, QIcon, QPixmap
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QLineEdit, QMenu, QPushButton,
                               QScrollArea, QSizePolicy, QStyle, QVBoxLayout, QWidget)

WIDTH = 280
ICON = Path(__file__).with_name("icon.svg")


def relative_time(iso: str, now: datetime | None = None) -> str:
    try:
        t = datetime.fromisoformat(iso)
    except (TypeError, ValueError):
        return ""
    now = now or datetime.now(t.tzinfo)
    days = (now.date() - t.date()).days
    if days <= 0:
        return f"bugün {t:%H:%M}"
    if days == 1:
        return "dün"
    return f"{days} gün önce"


class ElidedLabel(QLabel):
    def __init__(self, text="", parent=None):
        super().__init__(parent)
        self._full = ""
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.set_full_text(text)

    def set_full_text(self, text):
        self._full = text
        self._elide()

    def full_text(self):
        return self._full

    def _elide(self):
        w = max(self.width(), 10)
        self.setText(QFontMetrics(self.font()).elidedText(self._full, Qt.ElideRight, w))

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._elide()


class ChatRow(QFrame):
    selected = Signal(str)
    delete_requested = Signal(str)
    rename_done = Signal(str, str)

    def __init__(self, chat: dict):
        super().__init__()
        self.setObjectName("chatRow")
        self.setCursor(Qt.PointingHandCursor)
        self.chat_id = chat["id"]
        self.title = chat.get("title") or "Yeni sohbet"
        self.setProperty("current", False)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 6, 6, 6)
        col = QVBoxLayout()
        col.setSpacing(0)
        self.title_lbl = ElidedLabel(self.title)
        self.title_lbl.setObjectName("chatTitle")
        self.time_lbl = QLabel(relative_time(chat.get("updated", "")))
        self.time_lbl.setObjectName("muted")
        col.addWidget(self.title_lbl)
        col.addWidget(self.time_lbl)
        lay.addLayout(col, 1)
        self.edit = QLineEdit()
        self.edit.setObjectName("renameEdit")
        self.edit.hide()
        self.edit.editingFinished.connect(self._finish_edit)
        col.insertWidget(0, self.edit)
        self.del_btn = QPushButton()
        self.del_btn.setObjectName("rowDelete")
        self.del_btn.setIcon(self.style().standardIcon(QStyle.SP_TrashIcon))
        self.del_btn.setToolTip("Sil")
        self.del_btn.setCursor(Qt.PointingHandCursor)
        self.del_btn.setFixedSize(26, 26)
        self.del_btn.hide()
        self.del_btn.clicked.connect(lambda: self.delete_requested.emit(self.chat_id))
        lay.addWidget(self.del_btn)
        self.setToolTip(self.title)
        self._editing = False

    def set_current(self, cur: bool):
        self.setProperty("current", cur)
        self.style().unpolish(self)
        self.style().polish(self)

    def start_rename(self):
        self._editing = True
        self.title_lbl.hide()
        self.edit.setText(self.title)
        self.edit.show()
        self.edit.setFocus()
        self.edit.selectAll()

    def _finish_edit(self):
        if not self._editing:
            return
        self._editing = False
        new = self.edit.text().strip()
        self.edit.hide()
        self.title_lbl.show()
        if new and new != self.title:
            self.title = new
            self.title_lbl.set_full_text(new)
            self.setToolTip(new)
            self.rename_done.emit(self.chat_id, new)

    def cancel_rename(self):
        self._editing = False
        self.edit.hide()
        self.title_lbl.show()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape and self._editing:
            self.cancel_rename()
        else:
            super().keyPressEvent(e)

    def enterEvent(self, e):
        if not self._editing:
            self.del_btn.show()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self.del_btn.hide()
        super().leaveEvent(e)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and not self._editing:
            self.selected.emit(self.chat_id)
        super().mousePressEvent(e)

    def contextMenuEvent(self, e):
        m = QMenu(self)
        a_ren = m.addAction("Yeniden adlandır")
        a_del = m.addAction("Sil")
        act = m.exec(e.globalPos())
        if act is a_ren:
            self.start_rename()
        elif act is a_del:
            self.delete_requested.emit(self.chat_id)


class Sidebar(QWidget):
    new_chat_requested = Signal()
    chat_selected = Signal(str)
    chat_delete_requested = Signal(str)
    chat_rename_requested = Signal(str, str)
    delete_all_requested = Signal()
    settings_requested = Signal()
    choose_folder_requested = Signal()
    reset_folder_requested = Signal()
    add_note_requested = Signal()
    open_folder_requested = Signal()
    reindex_requested = Signal()
    notes_list_toggled = Signal(bool)
    folder_section_toggled = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedWidth(WIDTH)
        st = self.style()
        self._busy = False
        self._current = None
        self._rows: dict[str, ChatRow] = {}
        self._notes_count = 0
        self._folder_open = False
        self._notes_open = False
        self._path = ""

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 14, 12, 12)
        root.setSpacing(8)

        head = QHBoxLayout()
        ic = QLabel()
        ic.setPixmap(QIcon(str(ICON)).pixmap(QSize(26, 26)))
        title = QLabel("Not Arama")
        title.setObjectName("appTitle")
        head.addWidget(ic)
        head.addWidget(title, 1)
        root.addLayout(head)

        self.btn_new = QPushButton("＋  Yeni sohbet")
        self.btn_new.setObjectName("newChat")
        self.btn_new.setCursor(Qt.PointingHandCursor)
        self.btn_new.clicked.connect(self.new_chat_requested)
        root.addWidget(self.btn_new)

        # --- Not klasörü akordeonu
        self.folder_head = QPushButton()
        self.folder_head.setObjectName("folderHead")
        self.folder_head.setCursor(Qt.PointingHandCursor)
        self.folder_head.clicked.connect(lambda: self.set_folder_section_open(
            not self._folder_open, emit=True))
        hl = QHBoxLayout(self.folder_head)
        hl.setContentsMargins(10, 0, 10, 0)
        fi = QLabel()
        fi.setPixmap(st.standardIcon(QStyle.SP_DirIcon).pixmap(18, 18))
        self.folder_name = ElidedLabel("-")
        self.folder_name.setObjectName("folderName")
        self.count_lbl = QLabel("0")
        self.count_lbl.setObjectName("muted")
        self.stale_dot = QLabel("●")
        self.stale_dot.setObjectName("staleDot")
        self.stale_dot.setToolTip("İndeks güncel değil")
        self.stale_dot.hide()
        self.chevron = QLabel("▾")
        self.chevron.setObjectName("muted")
        for w in (fi,):
            w.setAttribute(Qt.WA_TransparentForMouseEvents)
        for w in (self.folder_name, self.count_lbl, self.stale_dot, self.chevron):
            w.setAttribute(Qt.WA_TransparentForMouseEvents)
        hl.addWidget(fi)
        hl.addWidget(self.folder_name, 1)
        hl.addWidget(self.count_lbl)
        hl.addWidget(self.stale_dot)
        hl.addWidget(self.chevron)
        self.folder_head.setFixedHeight(38)
        root.addWidget(self.folder_head)

        self.folder_body = QFrame()
        self.folder_body.setObjectName("folderBody")
        bl = QVBoxLayout(self.folder_body)
        bl.setContentsMargins(8, 6, 8, 8)
        bl.setSpacing(2)
        self.path_lbl = QLabel()
        self.path_lbl.setObjectName("muted")
        self.path_lbl.setWordWrap(True)
        self.path_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        bl.addWidget(self.path_lbl)

        def act(text, icon, sig):
            b = QPushButton(text)
            b.setObjectName("action")
            b.setIcon(st.standardIcon(icon))
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(sig)
            bl.addWidget(b)
            return b
        self.btn_choose = act("Klasör seç", QStyle.SP_DirOpenIcon, self.choose_folder_requested)
        self.btn_reset = act("Örnek notlara dön", QStyle.SP_BrowserReload,
                             self.reset_folder_requested)
        self.btn_add = act("Not ekle", QStyle.SP_FileDialogNewFolder, self.add_note_requested)
        self.btn_open = act("Klasörü aç", QStyle.SP_DirLinkIcon, self.open_folder_requested)
        self.btn_reindex = act("Yeniden indeksle", QStyle.SP_BrowserReload,
                               self.reindex_requested)
        self._reindex_text = "Yeniden indeksle"
        self.status_lbl = QLabel()
        self.status_lbl.setObjectName("muted")
        self.status_lbl.setWordWrap(True)
        bl.addWidget(self.status_lbl)

        self.notes_toggle = QPushButton()
        self.notes_toggle.setObjectName("notesToggle")
        self.notes_toggle.setCursor(Qt.PointingHandCursor)
        self.notes_toggle.clicked.connect(
            lambda: self.set_notes_list_open(not self._notes_open, emit=True))
        bl.addWidget(self.notes_toggle)
        self.notes_lbl = QLabel()
        self.notes_lbl.setObjectName("notesList")
        self.notes_lbl.setWordWrap(True)
        self.notes_lbl.setContentsMargins(10, 0, 0, 0)
        bl.addWidget(self.notes_lbl)
        root.addWidget(self.folder_body)

        # --- Sohbetler
        sec = QLabel("SOHBETLER")
        sec.setObjectName("section")
        root.addWidget(sec)
        self.scroll = QScrollArea()
        self.scroll.setObjectName("chatList")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        inner = QWidget()
        inner.setObjectName("chatListInner")
        self.list_lay = QVBoxLayout(inner)
        self.list_lay.setContentsMargins(0, 0, 4, 0)
        self.list_lay.setSpacing(2)
        self.empty_lbl = QLabel("Henüz sohbet yok")
        self.empty_lbl.setObjectName("muted")
        self.empty_lbl.setAlignment(Qt.AlignCenter)
        self.list_lay.addWidget(self.empty_lbl)
        self.list_lay.addStretch(1)
        self.scroll.setWidget(inner)
        root.addWidget(self.scroll, 1)

        self.btn_delall = QPushButton("Tümünü sil")
        self.btn_delall.setObjectName("link")
        self.btn_delall.setCursor(Qt.PointingHandCursor)
        self.btn_delall.clicked.connect(self.delete_all_requested)
        root.addWidget(self.btn_delall, 0, Qt.AlignLeft)

        self.btn_settings = QPushButton("⚙  Ayarlar")
        self.btn_settings.setObjectName("settings")
        self.btn_settings.setCursor(Qt.PointingHandCursor)
        self.btn_settings.clicked.connect(self.settings_requested)
        root.addWidget(self.btn_settings)

        self.set_folder("", True)
        self.set_notes([])
        self.set_chats([])
        self.set_folder_section_open(False)
        self.set_notes_list_open(False)

    # ---- API
    def set_folder(self, path: str, is_default: bool):
        self._path = path
        name = (Path(path).name or path) if path else "-"
        if is_default:
            name = f"{name} (örnek)"
        self.folder_name.set_full_text(name)
        self.folder_head.setToolTip(path)
        self.path_lbl.setText(path)
        self.path_lbl.setToolTip(path)
        self.btn_reset.setVisible(not is_default)

    def set_notes(self, names: list[str]):
        self._notes_count = len(names)
        self.count_lbl.setText(str(len(names)))
        self.notes_lbl.setText("\n".join(names))
        self._refresh_notes_toggle()

    def set_index_status(self, text: str, stale: bool):
        self.status_lbl.setText(text)
        self.stale_dot.setVisible(stale)

    def set_chats(self, chats: list[dict]):
        for r in self._rows.values():
            self.list_lay.removeWidget(r)
            r.setParent(None)
            r.deleteLater()
        self._rows = {}
        for i, c in enumerate(chats):
            r = ChatRow(c)
            r.selected.connect(self.chat_selected)
            r.delete_requested.connect(self.chat_delete_requested)
            r.rename_done.connect(self.chat_rename_requested)
            self.list_lay.insertWidget(i, r)
            self._rows[c["id"]] = r
        self.empty_lbl.setVisible(not chats)
        self.btn_delall.setVisible(bool(chats))
        self.set_current_chat(self._current)

    def set_current_chat(self, chat_id):
        self._current = chat_id
        for cid, r in self._rows.items():
            r.set_current(cid == chat_id)

    def set_busy(self, busy: bool):
        self._busy = busy
        for b in (self.btn_choose, self.btn_reset, self.btn_add, self.btn_reindex):
            b.setEnabled(not busy)
        self.btn_reindex.setText("İndeksleniyor…" if busy else self._reindex_text)

    def set_notes_list_open(self, open: bool, emit: bool = False):
        self._notes_open = open
        self.notes_lbl.setVisible(open)
        self._refresh_notes_toggle()
        if emit:
            self.notes_list_toggled.emit(open)

    def set_folder_section_open(self, open: bool, emit: bool = False):
        self._folder_open = open
        self.folder_body.setVisible(open)
        self.chevron.setText("▴" if open else "▾")
        if emit:
            self.folder_section_toggled.emit(open)

    def _refresh_notes_toggle(self):
        self.notes_toggle.setText(
            f"{'▾' if self._notes_open else '▸'} Notlar ({self._notes_count})")
