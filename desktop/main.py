"""Masaüstü arayüz:  uv run python -m desktop.main"""
import sys

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QApplication, QButtonGroup, QFileDialog, QHBoxLayout, QLabel,
                               QLineEdit, QListWidget, QMainWindow, QMessageBox, QProgressBar,
                               QPushButton, QRadioButton, QSpinBox, QVBoxLayout, QWidget)

from src import config

from . import services
from .chat_view import ChatView
from .workers import Worker


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kişisel Not Arama")
        self.resize(1000, 680)
        self._workers = set()   # çalışan iş parçacıklarını canlı tut
        self._busy = 0
        self._model_ready = False
        self._build_ui()
        self.refresh_side()
        # Embedding modelini arka planda, bir kez yükle
        self.run(services.load_embed_model, self._on_model_loaded, self._on_model_failed,
                 "Embedding modeli yükleniyor...")

    # ---------- arayüz ----------
    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        row = QHBoxLayout(root)

        # Sol panel
        side = QVBoxLayout()
        self.notes_label = QLabel()
        self.notes_list = QListWidget()
        self.btn_add = QPushButton("Not ekle")
        self.btn_open = QPushButton("Notlar klasörünü aç")
        self.btn_reindex = QPushButton("Yeniden indeksle")
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)   # belirsiz ilerleme
        self.progress.setVisible(False)
        self.index_label = QLabel()
        self.index_label.setWordWrap(True)
        self.top_k = QSpinBox(minimum=1, maximum=10, value=config.TOP_K)
        self.rb_numpy, self.rb_chroma = QRadioButton("numpy"), QRadioButton("chroma")
        (self.rb_chroma if config.INDEX_BACKEND == "chroma" else self.rb_numpy).setChecked(True)
        self.btn_clear = QPushButton("Sohbeti temizle")
        for w in (self.notes_label, self.notes_list, self.btn_add, self.btn_open,
                  self.btn_reindex, self.progress, self.index_label):
            side.addWidget(w)
        side.addWidget(QLabel("Kaç parça getirilsin (top_k)"))
        side.addWidget(self.top_k)
        side.addWidget(QLabel("İndeks yöntemi"))
        bk = QHBoxLayout()
        bk.addWidget(self.rb_numpy)
        bk.addWidget(self.rb_chroma)
        side.addLayout(bk)
        side.addWidget(self.btn_clear)
        side_w = QWidget()
        side_w.setLayout(side)
        side_w.setFixedWidth(280)
        row.addWidget(side_w)

        # Sohbet
        chat = QVBoxLayout()
        self.chat = ChatView()
        self.input = QLineEdit(placeholderText="Notlarına bir soru sor")
        self.btn_send = QPushButton("Gönder")
        inp = QHBoxLayout()
        inp.addWidget(self.input)
        inp.addWidget(self.btn_send)
        chat.addWidget(self.chat)
        chat.addLayout(inp)
        row.addLayout(chat, 1)

        self.input.returnPressed.connect(self.send)
        self.btn_send.clicked.connect(self.send)
        self.btn_add.clicked.connect(self.add_note)
        self.btn_open.clicked.connect(self.open_folder)
        self.btn_reindex.clicked.connect(self.reindex)
        self.btn_clear.clicked.connect(self.chat.clear)
        self.statusBar().showMessage("Hazır")

    def backend(self):
        return "chroma" if self.rb_chroma.isChecked() else "numpy"

    def refresh_side(self):
        notes = services.list_notes()
        self.notes_label.setText(f"Notlar ({len(notes)})")
        self.notes_list.clear()
        self.notes_list.addItems([p.name for p in notes])
        ts = services.index_status()
        self.index_label.setText(
            f"Model: {config.EMBED_MODEL}\nParça boyutu: {config.CHUNK_SIZE} karakter\n"
            + (f"Son indeksleme: {ts:%Y-%m-%d %H:%M}" if ts else
               "Henüz indeks yok. 'Yeniden indeksle'ye bas."))

    # ---------- iş parçacığı yönetimi ----------
    def set_busy(self, delta):
        self._busy += delta
        busy = self._busy > 0
        for w in (self.btn_send, self.input, self.btn_reindex, self.btn_add):
            w.setEnabled(not busy)
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
        self.chat.add("user", q)
        self.run(services.ask, self._on_answer, self._on_ask_failed,
                 "Notlarda aranıyor ve cevap üretiliyor...", q, self.top_k.value(), self.backend())

    def _on_answer(self, res):
        ans, results = res
        self.chat.add("assistant", ans, results)
        self.statusBar().showMessage("Cevap hazır", 5000)

    def _on_ask_failed(self, e):
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
        self.progress.setVisible(True)
        self.run(services.reindex, self._on_reindexed, self._on_reindex_failed,
                 "İndeksleniyor (okuma, parçalama, embed)...")

    def _on_reindexed(self, res):
        self.progress.setVisible(False)
        self.refresh_side()
        msg = f"{res[0]} not → {res[1]} parça indekslendi"
        self.statusBar().showMessage(msg, 8000)
        QMessageBox.information(self, "İndeksleme bitti", msg)

    def _on_reindex_failed(self, e):
        self.progress.setVisible(False)
        self.statusBar().showMessage("İndeksleme başarısız")
        QMessageBox.critical(self, "İndeksleme başarısız", str(e))

    def add_note(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Not seç", "", "Notlar (*.md *.txt)")
        saved = [services.import_note(p) for p in paths]
        ok = sum(1 for s in saved if s)
        if paths:
            self.statusBar().showMessage(f"{ok} dosya eklendi. Şimdi yeniden indeksle.", 8000)
        if ok < len(saved):
            QMessageBox.warning(self, "Uyarı", "Geçersiz dosya atlandı (yalnızca .md/.txt).")
        self.refresh_side()

    def open_folder(self):
        config.NOTES_DIR.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(config.NOTES_DIR)))

    def closeEvent(self, ev):
        for w in list(self._workers):   # çalışan işler bitene kadar bekle
            w.wait()
        super().closeEvent(ev)


def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
