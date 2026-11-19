"""Ayarlar penceresi: top_k, indeks yöntemi ve salt-okunur model bilgisi."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import (QApplication, QDialog, QFrame, QGridLayout, QHBoxLayout, QLabel,
                               QPushButton, QSpinBox, QVBoxLayout, QCheckBox,
                               QDoubleSpinBox)

try:
    from . import style
except ImportError:  # doğrudan çalıştırma
    import style

DEFAULT_TOP_K = 10
DEFAULT_BACKEND = "chroma"
DEFAULT_THRESHOLD = 0.40
DEFAULT_THRESHOLD_ENABLED = True
TH_MIN, TH_MAX = 0.20, 0.90
TOP_K_MIN, TOP_K_MAX = 1, 15
_INFO_ROWS = (("embed_model", "Gömme modeli"), ("llm_model", "Dil modeli"),
              ("chunk_size", "Parça boyutu"), ("num_ctx", "Bağlam (num_ctx)"),
              ("notes_dir", "Not klasörü"))


def _qss(c: dict) -> str:
    return f"""
SettingsDialog {{ background: {c['bg']}; }}
SettingsDialog QLabel {{ color: {c['fg']}; }}
SettingsDialog QLabel#section {{ color: {c['muted']}; font-size: 8pt; font-weight: 600;
    letter-spacing: 1px; padding-top: 8px; }}
SettingsDialog QLabel#hint {{ color: {c['muted']}; font-size: 9pt; }}
SettingsDialog QLabel#infoKey {{ color: {c['muted']}; }}
SettingsDialog QFrame#sep {{ background: {c['border']}; max-height: 1px; border: none; }}
SettingsDialog QSpinBox, SettingsDialog QDoubleSpinBox {{ color: {c['fg']}; background: {c['surface']};
    border: 1px solid {c['border']}; border-radius: 8px; padding: 4px 8px; min-height: 20px; }}
SettingsDialog QSpinBox::up-button, SettingsDialog QSpinBox::down-button,
SettingsDialog QDoubleSpinBox::up-button, SettingsDialog QDoubleSpinBox::down-button {{ width: 0; border: none; }}
SettingsDialog QPushButton {{ color: {c['fg']}; background: {c['surface']};
    border: 1px solid {c['border']}; border-radius: 8px; padding: 6px 14px; }}
SettingsDialog QPushButton:hover {{ background: {c['surface2']}; border-color: {c['accent']}; }}
SettingsDialog QPushButton#step {{ padding: 0; min-width: 28px; max-width: 28px;
    min-height: 28px; max-height: 28px; font-size: 12pt; font-weight: 600; }}
SettingsDialog QPushButton#seg {{ border-radius: 8px; }}
SettingsDialog QPushButton#seg:checked {{ background: {c['accent']}; color: {c['on_accent']};
    border-color: {c['accent']}; font-weight: 600; }}
SettingsDialog QPushButton#save {{ background: {c['accent']}; color: {c['on_accent']};
    border-color: {c['accent']}; font-weight: 600; }}
SettingsDialog QPushButton#save:hover {{ background: {c['accent_hover']}; }}
"""


class SettingsDialog(QDialog):
    def __init__(self, parent=None, *, top_k: int, backend: str, info: dict,
                 score_threshold: float = DEFAULT_THRESHOLD,
                 threshold_enabled: bool = DEFAULT_THRESHOLD_ENABLED):
        super().__init__(parent)
        self.setWindowTitle("Ayarlar")
        self.setModal(True)
        self.setFixedWidth(360)
        info = info or {}

        pal = QApplication.palette() if QApplication.instance() else QPalette()
        self.setStyleSheet(_qss(style.colors(pal)))

        self.top_k = QSpinBox(minimum=TOP_K_MIN, maximum=TOP_K_MAX)
        self.top_k.setAlignment(Qt.AlignCenter)
        self.top_k.setValue(max(TOP_K_MIN, min(TOP_K_MAX, int(top_k))))

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(6)

        root.addWidget(self._label("ARAMA", "section"))
        root.addWidget(QLabel("Kaç parça getirilsin (top_k)"))
        row = QHBoxLayout()
        row.setSpacing(6)
        for sym, d in (("−", -1), ("+", 1)):
            b = QPushButton(sym)
            b.setObjectName("step")
            b.setCursor(Qt.PointingHandCursor)
            b.setAutoRepeat(True)
            b.setAutoDefault(False)
            b.clicked.connect(lambda _=False, d=d: self.top_k.stepBy(d))
            row.addWidget(b)
            if d < 0:
                row.addWidget(self.top_k, 1)
        root.addLayout(row)
        root.addWidget(self._hint("Soru başına modele verilen parça sayısı. "
                                  "Fazlası daha kapsamlı ama yavaş."))

        root.addSpacing(6)
        root.addWidget(QLabel("İndeks yöntemi"))
        seg = QHBoxLayout()
        seg.setSpacing(6)
        self.btn_chroma = self._seg("chroma")
        self.btn_numpy = self._seg("numpy")
        seg.addWidget(self.btn_chroma)
        seg.addWidget(self.btn_numpy)
        root.addLayout(seg)
        root.addWidget(self._hint("chroma: vektör veritabanı, numpy: elle kosinüs, "
                                  "öğrenme amaçlı"))
        self._set_backend(backend)
        self.btn_chroma.clicked.connect(lambda: self._set_backend("chroma"))
        self.btn_numpy.clicked.connect(lambda: self._set_backend("numpy"))

        root.addSpacing(6)
        root.addWidget(self._label("CEVAP EŞİĞİ", "section"))
        self.th_enabled = QCheckBox("Düşük benzerlikte 'notlarda yok' de")
        self.th_enabled.setChecked(bool(threshold_enabled))
        root.addWidget(self.th_enabled)
        self.th = QDoubleSpinBox(minimum=TH_MIN, maximum=TH_MAX, singleStep=0.01, decimals=2)
        self.th.setAlignment(Qt.AlignCenter)
        self.th.setValue(max(TH_MIN, min(TH_MAX, float(score_threshold))))
        self.th.setEnabled(self.th_enabled.isChecked())
        self.th_enabled.toggled.connect(self.th.setEnabled)
        root.addWidget(self.th)
        root.addWidget(self._hint("Yüksek: daha çok 'notlarda yok', düşük: daha çok cevap denemesi"))

        root.addSpacing(6)
        root.addWidget(self._label("MODELLER", "section"))
        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(4)
        r = 0
        for key, title in _INFO_ROWS:
            if info.get(key) in (None, ""):
                continue
            grid.addWidget(self._label(title, "infoKey"), r, 0, Qt.AlignTop)
            v = QLabel(str(info[key]))
            v.setWordWrap(True)
            v.setTextInteractionFlags(Qt.TextSelectableByMouse)
            grid.addWidget(v, r, 1)
            r += 1
        grid.setColumnStretch(1, 1)
        root.addLayout(grid)

        root.addSpacing(10)
        btns = QHBoxLayout()
        self.btn_reset = QPushButton("Varsayılana dön")
        self.btn_cancel = QPushButton("İptal")
        self.btn_save = QPushButton("Kaydet")
        self.btn_save.setObjectName("save")
        self.btn_save.setDefault(True)
        for b in (self.btn_reset, self.btn_cancel, self.btn_save):
            b.setCursor(Qt.PointingHandCursor)
        self.btn_reset.setAutoDefault(False)
        self.btn_cancel.setAutoDefault(False)
        btns.addWidget(self.btn_reset)
        btns.addStretch(1)
        btns.addWidget(self.btn_cancel)
        btns.addWidget(self.btn_save)
        root.addLayout(btns)
        self.btn_reset.clicked.connect(self.reset)
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_save.clicked.connect(self.accept)

    @staticmethod
    def _label(text, name):
        l = QLabel(text)
        l.setObjectName(name)
        return l

    def _hint(self, text):
        l = self._label(text, "hint")
        l.setWordWrap(True)
        return l

    def _seg(self, name):
        b = QPushButton(name)
        b.setObjectName("seg")
        b.setCheckable(True)
        b.setAutoDefault(False)
        b.setCursor(Qt.PointingHandCursor)
        return b

    def _set_backend(self, backend: str):
        self._backend = "numpy" if backend == "numpy" else "chroma"
        self.btn_chroma.setChecked(self._backend == "chroma")
        self.btn_numpy.setChecked(self._backend == "numpy")

    def reset(self):
        self.top_k.setValue(DEFAULT_TOP_K)
        self._set_backend(DEFAULT_BACKEND)
        self.th.setValue(DEFAULT_THRESHOLD)
        self.th_enabled.setChecked(DEFAULT_THRESHOLD_ENABLED)

    def values(self) -> dict:
        return {"top_k": self.top_k.value(), "backend": self._backend,
                "score_threshold": round(self.th.value(), 2),
                "threshold_enabled": self.th_enabled.isChecked()}
