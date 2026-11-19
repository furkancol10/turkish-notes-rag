"""Masaüstü arayüz:  uv run python -m desktop.main"""
import sys

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QApplication, QFileDialog, QFrame, QHBoxLayout, QLineEdit,
                               QMainWindow, QMessageBox, QPushButton, QWidget, QVBoxLayout)

from src import config, history, settings
from src.formats import DIALOG_FILTER, LABEL_TEXT, NO_NOTES_MSG

from . import services
from .chat_view import ChatView
from .settings_dialog import SettingsDialog
from .sidebar import Sidebar
from . import style
from .workers import Worker


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kişisel Not Arama")
        self.resize(1000, 680)
        self._workers = set()   # çalışan iş parçacıklarını canlı tut
        self._busy = 0
        self._model_ready = False
        self._asking = False
        self.top_k = settings.get_top_k()
        self.threshold = settings.get_score_threshold()
        self.threshold_enabled = settings.get_threshold_enabled()
        self.backend = settings.get_backend()
        self.cur = history.new_chat("")
        app = QApplication.instance()
        style.apply_font(app)
        app.setStyleSheet(style.build_stylesheet(app.palette())
                          + style.build_sidebar_stylesheet(app.palette()))
        self._build_ui()
        self.refresh_side()
        self._start_fresh()
        # Embedding modelini arka planda, bir kez yükle
        self.run(services.load_embed_model, self._on_model_loaded, self._on_model_failed,
                 "Embedding modeli yükleniyor...")

    # ---------- arayüz ----------
    def _build_ui(self):
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        row = QHBoxLayout(root)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)
        self.side = Sidebar()
        self.side.setFixedWidth(290)
        self.side.set_folder_section_open(settings.get_folder_section_open())
        self.side.set_notes_list_open(bool(settings.get("notes_list_open", False)))
        row.addWidget(self.side)

        # Sohbet
        chat = QVBoxLayout()
        chat.setContentsMargins(0, 0, 0, 0)
        chat.setSpacing(0)
        self.chat = ChatView()
        self.input = QLineEdit(placeholderText="Notlarına bir soru sor")
        self.input.setObjectName("input")
        self.btn_send = QPushButton("➤")
        self.btn_send.setObjectName("send")
        self.btn_send.setToolTip("Gönder")
        self.btn_send.setCursor(Qt.PointingHandCursor)
        bar = QWidget()
        bar.setObjectName("inputBar")
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(28, 8, 28, 18)
        wrap = QFrame()
        wrap.setObjectName("inputWrap")
        iw = QHBoxLayout(wrap)
        iw.setContentsMargins(16, 5, 5, 5)
        iw.addWidget(self.input)
        iw.addWidget(self.btn_send)
        bl.addWidget(wrap)
        self.chat.margins_changed.connect(lambda l, r: bl.setContentsMargins(l, 8, r, 18))
        chat.addWidget(self.chat, 1)
        chat.addWidget(bar)
        row.addLayout(chat, 1)

        self.input.returnPressed.connect(self.send)
        self.btn_send.clicked.connect(self.send)
        self.chat.suggestion.connect(self.ask_example)
        sd = self.side
        sd.add_note_requested.connect(self.add_note)
        sd.open_folder_requested.connect(self.open_folder)
        sd.choose_folder_requested.connect(self.choose_folder)
        sd.reset_folder_requested.connect(self.use_sample)
        sd.reindex_requested.connect(self.reindex)
        sd.new_chat_requested.connect(self.new_chat)
        sd.chat_selected.connect(self.open_chat)
        sd.chat_delete_requested.connect(self.delete_chat)
        sd.chat_rename_requested.connect(self.rename_chat)
        sd.delete_all_requested.connect(self.delete_all_chats)
        sd.settings_requested.connect(self.open_settings)
        sd.notes_list_toggled.connect(lambda v: self._persist(settings.set, "notes_list_open", v))
        sd.folder_section_toggled.connect(
            lambda v: self._persist(settings.set_folder_section_open, v))
        self.statusBar().showMessage("Hazır")

    def ask_example(self, q):
        if not self._busy:
            self.input.setText(q)
            self.send()

    @staticmethod
    def _persist(fn, *args):
        try:
            fn(*args)
        except OSError:
            pass

    def refresh_side(self):
        d = services.notes_dir()
        self.side.set_folder(str(d), settings.is_default())
        notes = services.list_notes()
        self.chat.set_examples(services.example_questions())
        self.side.set_notes(notes)
        problem = services.folder_problem()
        ts = services.index_status()
        stale = False
        if problem:
            tail = problem
        elif not notes:
            tail = NO_NOTES_MSG
        elif not ts:
            tail = "Henüz indeks yok. 'Yeniden indeksle'ye bas."
        else:
            tail = f"Son indeksleme: {ts:%Y-%m-%d %H:%M}"
            stale = services.notes_changed()
            if stale:
                tail += "\nNotlar değişti, yeniden indeksle."
        self.side.set_index_status(tail, stale)

    # ---------- ayarlar ----------
    def open_settings(self):
        info = {"embed_model": config.EMBED_MODEL, "llm_model": config.LLM_MODEL,
                "chunk_size": f"{config.CHUNK_SIZE} karakter",
                "num_ctx": config.LLM_OPTIONS.get("num_ctx"),
                "notes_dir": str(services.notes_dir())}
        dlg = SettingsDialog(self, top_k=self.top_k, backend=self.backend, info=info,
                             score_threshold=self.threshold, threshold_enabled=self.threshold_enabled)
        if dlg.exec():
            v = dlg.values()
            self.top_k, self.backend = v["top_k"], v["backend"]
            self._persist(settings.set_top_k, self.top_k)
            self._persist(settings.set_backend, self.backend)
            self.threshold, self.threshold_enabled = v["score_threshold"], v["threshold_enabled"]
            self._persist(settings.set_score_threshold, self.threshold)
            self._persist(settings.set_threshold_enabled, self.threshold_enabled)

    # ---------- sohbet geçmişi ----------
    def _refresh_chats(self):
        self.side.set_chats(history.list_chats())
        self.side.set_current_chat(self.cur["id"])

    def _fresh(self):
        self.cur = history.new_chat(str(services.notes_dir()))
        self.chat.clear()
        self.side.set_current_chat(self.cur["id"])

    def new_chat(self):
        if self._asking:
            return self.statusBar().showMessage("Cevap bekleniyor...", 3000)
        self._fresh()
        self._persist(settings.set_last_chat_id, None)

    def open_chat(self, cid):
        if self._asking:
            self.side.set_current_chat(self.cur["id"])
            return self.statusBar().showMessage("Cevap bekleniyor...", 3000)
        c = history.load_chat(cid)
        if c is None:
            self._refresh_chats()
            return
        self.cur = c
        self.chat.load_messages(c["messages"])
        self.side.set_current_chat(cid)
        self._persist(settings.set_last_chat_id, cid)

    def delete_chat(self, cid):
        if self._asking:
            return self.statusBar().showMessage("Cevap bekleniyor...", 3000)
        if QMessageBox.question(self, "Sohbeti sil", "Bu sohbet silinsin mi?") != QMessageBox.Yes:
            return
        history.delete_chat(cid)
        if cid == self.cur["id"]:
            self._fresh()
            self._persist(settings.set_last_chat_id, None)
        self._refresh_chats()

    def delete_all_chats(self):
        if self._asking:
            return self.statusBar().showMessage("Cevap bekleniyor...", 3000)
        if QMessageBox.question(self, "Tümünü sil",
                                "Tüm sohbetler silinsin mi?") != QMessageBox.Yes:
            return
        history.delete_all()
        self._fresh()
        self._persist(settings.set_last_chat_id, None)
        self._refresh_chats()

    def rename_chat(self, cid, title):
        history.rename_chat(cid, title)
        if cid == self.cur["id"]:
            c = history.load_chat(cid)
            if c:
                self.cur["title"] = c.get("title", "")
        self._refresh_chats()

    def _record(self, role, text, sources=None, query=None, intent=None, extra=None):
        msg = {"role": role, "text": text, "sources": sources or []}
        if intent:
            msg["intent"] = intent
        if query:
            msg["query"] = query
        if extra:
            msg.update(extra)
        self.cur["messages"].append(msg)
        try:
            history.save_chat(self.cur)
            settings.set_last_chat_id(self.cur["id"])
        except (OSError, ValueError):
            return
        self._refresh_chats()

    def _start_fresh(self):
        # Açılışta her zaman boş yeni sohbet; ilk mesaj gelene kadar kaydedilmez.
        # Eski sohbetler soldaki listeden açılır.
        self._refresh_chats()

    # ---------- iş parçacığı yönetimi ----------
    def set_busy(self, delta):
        self._busy += delta
        busy = self._busy > 0
        for w in (self.btn_send, self.input):
            w.setEnabled(not busy)
        self.side.set_busy(busy)
        if not busy:
            self.input.setFocus()

    def run(self, fn, on_done, on_fail, message, *args):
        """fn'i arka planda çalıştır; bitince on_done/on_fail ana iş parçacığında çağrılır."""
        w = Worker(fn, *args, parent=self)
        self._workers.add(w)
        self.set_busy(1)
        self.statusBar().showMessage(message)

        def finish():
            self._workers.discard(w)
            self.set_busy(-1)
            w.deleteLater()
        w.done.connect(lambda r: (finish(), on_done(r)))
        w.failed.connect(lambda e: (finish(), on_fail(e)))
        w.start()

    # ---------- olaylar ----------
    def _on_model_loaded(self, _):
        self._model_ready = True
        self.statusBar().showMessage("Model hazır", 5000)

    def _on_model_failed(self, e):
        self.statusBar().showMessage("Model yüklenemedi")
        QMessageBox.warning(self, "Model yüklenemedi", f"Embedding modeli yüklenemedi:\n{e}")

    def send(self):
        q = self.input.text().strip()
        if not q or self._busy:
            return
        self.input.clear()
        prior = list(self.cur["messages"])   # bu sorudan önceki mesajlar (hafıza)
        self.chat.add("user", q)
        self._record("user", q)
        self.chat.show_typing()
        self._asking = True
        self.run(services.ask, self._on_answer, self._on_ask_failed,
                 "Notlarda aranıyor ve cevap üretiliyor...", q, self.top_k, self.backend, prior,
                 self.threshold, self.threshold_enabled)

    def _on_answer(self, res):
        ans, results, info = res
        q = info.get("query")
        asked = self.cur["messages"][-1].get("text") if self.cur["messages"] else None
        q = q if q and q != asked else None
        self._asking = False
        self.chat.hide_typing()
        self.chat.add("assistant", ans, results, q, info.get("note"))
        self._record("assistant", ans, history.sources_from_results(results), q,
                     info.get("intent"),
                     {k: info[k] for k in ("below_threshold", "top_score", "threshold", "note")
                      if k in info})
        self.statusBar().showMessage("Cevap hazır", 5000)

    def _on_ask_failed(self, e):
        self._asking = False
        self.chat.hide_typing()
        kind = getattr(e, "kind", "other")
        self.statusBar().showMessage("Hata")
        if kind == "index":
            QMessageBox.information(self, "İndeks yok",
                                    "İndeks bulunamadı. 'Yeniden indeksle'ye bas.")
        elif kind == "ollama":
            QMessageBox.warning(self, "Ollama çalışmıyor",
                                "Ollama'ya bağlanılamadı. Servisi başlat (`ollama serve`) "
                                "ve tekrar dene.")
        else:
            QMessageBox.critical(self, "Hata", str(e))

    def reindex(self):
        self.run(services.reindex, self._on_reindexed, self._on_reindex_failed,
                 "İndeksleniyor (okuma, parçalama, embed)...")

    def _on_reindexed(self, res):
        self.refresh_side()
        msg = res.summary()
        self.statusBar().showMessage(msg, 8000)
        QMessageBox.information(self, "İndeksleme bitti", msg)

    def _on_reindex_failed(self, e):
        self.statusBar().showMessage("İndeksleme başarısız")
        QMessageBox.critical(self, "İndeksleme başarısız", str(e))

    def add_note(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Not seç", "", DIALOG_FILTER)
        saved = [services.import_note(p) for p in paths]
        ok = sum(1 for s in saved if s)
        if paths:
            self.statusBar().showMessage(f"{ok} dosya eklendi. Şimdi yeniden indeksle.", 8000)
        if ok < len(saved):
            QMessageBox.warning(self, "Uyarı", f"Geçersiz dosya atlandı (desteklenen: {LABEL_TEXT}).")
        self.refresh_side()

    def open_folder(self):
        d = services.notes_dir()
        d.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(d)))

    def choose_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Not klasörü seç", str(services.notes_dir()))
        if not path:
            return
        try:
            services.set_folder(path)
        except ValueError as e:
            QMessageBox.warning(self, "Klasör seçilemedi", str(e))
            return
        self._folder_changed()

    def use_sample(self):
        services.reset_folder()
        self._folder_changed()

    def _folder_changed(self):
        self.refresh_side()
        n = len(services.list_notes())
        self.statusBar().showMessage(f"Not klasörü değişti: {n} not", 8000)
        if n == 0:
            QMessageBox.information(self, "Not bulunamadı",
                                    NO_NOTES_MSG)
            return
        msg = f"{n} not bulundu. Şimdi indekslensin mi?"
        if n > 2000:
            msg += "\nKlasör büyük, biraz sürebilir."
        if QMessageBox.question(self, "Yeniden indeksle", msg) == QMessageBox.Yes:
            self.reindex()

    def shutdown(self):
        """Tüm arka plan iş parçacıklarını (model yükleyici dahil) bitene kadar bekler."""
        for w in list(self._workers):
            w.wait()

    def closeEvent(self, ev):
        self.shutdown()
        super().closeEvent(ev)


APP_ID = "kisisel-not-arama"  # .desktop dosya adıyla aynı olmalı (dock adı/ikonu buradan eşleşir)


def main():
    from pathlib import Path
    from PySide6.QtGui import QIcon

    QApplication.setApplicationName(APP_ID)
    QApplication.setApplicationDisplayName("Kişisel Not Arama")
    QApplication.setDesktopFileName(APP_ID)  # Wayland app_id / X11 WM_CLASS
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(str(Path(__file__).with_name("icon.svg"))))
    win = MainWindow()
    app.aboutToQuit.connect(win.shutdown)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
