"""Sohbet alanı: mesaj balonları, kaynak çipleri, yazıyor göstergesi ve boş durum."""
import math
import time
from types import SimpleNamespace

from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (QFrame, QSizePolicy, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton,
                               QScrollArea, QToolButton, QVBoxLayout, QWidget)

from src.chunker import chunk_label

from . import style

MAX_W = 620


class SourceItem(QWidget):
    """Tek kaynak: çipe tıklayınca parça metni açılır."""
    def __init__(self, i, chunk, score):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        self.btn = QToolButton(text=f"▸ [{i}] {chunk_label(chunk)}  ·  {score:.2f}")
        self.btn.setObjectName("chip")
        self.btn.setCheckable(True)
        self.btn.setCursor(Qt.PointingHandCursor)
        self.body = QPlainTextEdit(chunk.text, readOnly=True)
        self.body.setObjectName("chunk")
        self.body.setMaximumHeight(160)
        self.body.setVisible(False)
        self._label = self.btn.text()[2:]
        self.btn.toggled.connect(self._toggle)
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self.btn)
        row.addStretch()
        lay.addLayout(row)
        lay.addWidget(self.body)

    def _toggle(self, on):
        self.btn.setText(("▾ " if on else "▸ ") + self._label)
        self.body.setVisible(on)


class TypingDots(QWidget):
    """Üç noktalı, zıplayıp solan animasyon (~400 ms döngü)."""
    CYCLE = 0.4

    def __init__(self):
        super().__init__()
        self.setFixedSize(QSize(46, 22))
        self._timer = QTimer(self, interval=16)
        self._timer.timeout.connect(self.update)
        self._timer.start()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        base = QColor(style.colors(self.palette())["dot"])
        t = time.monotonic() / self.CYCLE
        for k in range(3):
            ph = (t - k * 0.18) % 1.0
            s = max(0.0, math.sin(ph * math.pi))   # 0..1 zıplama
            col = QColor(base)
            col.setAlphaF(0.35 + 0.65 * s)
            p.setBrush(col)
            p.setPen(Qt.NoPen)
            p.drawEllipse(round(8 + k * 15 - 4), round(15 - 4 - 7 * s), 8, 8)


class Bubble(QWidget):
    """Tek mesaj satırı: kullanıcı sağda, asistan solda avatarlı."""
    def __init__(self, role, text="", results=None, typing=False):
        super().__init__()
        self.typing = typing
        user = role == "user"
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)
        frame = QFrame()
        frame.setObjectName("bubbleUser" if user else "bubbleBot")
        frame.setMaximumWidth(MAX_W)
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(8)
        if typing:
            lay.addWidget(TypingDots())
        else:
            msg = QLabel(text)
            # Asistan cevabı Markdown (kalın, liste) olarak gösterilir; kullanıcı metni düz kalır
            msg.setTextFormat(Qt.PlainText if user else Qt.MarkdownText)
            msg.setWordWrap(True)
            msg.setTextInteractionFlags(Qt.TextSelectableByMouse)
            lay.addWidget(msg)
        if results:
            # Kaynaklar varsayılan olarak gizli; tek düğmeyle açılır/kapanır
            n = len(results)
            toggle = QToolButton(text=f"▸ Kaynakları göster ({n})")
            toggle.setObjectName("chip")
            toggle.setCheckable(True)
            toggle.setCursor(Qt.PointingHandCursor)
            box = QWidget()
            box_lay = QVBoxLayout(box)
            box_lay.setContentsMargins(0, 0, 0, 0)
            box_lay.setSpacing(6)
            for i, (c, s) in enumerate(results, 1):
                box_lay.addWidget(SourceItem(i, c, s))
            box.setVisible(False)

            def _toggle_sources(on):
                # Açınca balon tam genişliğe çıkar ve kapatınca da öyle kalır (metin yeniden kesilmez)
                if on:
                    frame.setMaximumWidth(MAX_W)
                box.setVisible(on)
                toggle.setText(("▾ Kaynakları gizle" if on else "▸ Kaynakları göster") + f" ({n})")

            toggle.toggled.connect(_toggle_sources)
            lay.addWidget(toggle, 0, Qt.AlignLeft)
            lay.addWidget(box)
        if user:
            row.addStretch(1)
            row.addWidget(frame, 0)
        else:
            av = QLabel("A")
            av.setObjectName("avatar")
            av.setAlignment(Qt.AlignCenter)
            av.setFixedSize(24, 24)
            col = QVBoxLayout()
            col.setSpacing(4)
            who = QLabel("Asistan")
            who.setObjectName("who")
            col.addWidget(who)
            if typing:
                col.addWidget(frame, 0, Qt.AlignLeft)
            else:
                # Hizalama verilmeden eklenince Qt satır kaydırmalı metnin yüksekliğini
                # genişliğe göre doğru hesaplar; balon genişliğini metne göre sınırlıyoruz.
                fm = msg.fontMetrics()
                natural = max(fm.horizontalAdvance(line) for line in (text or " ").splitlines() or [" "])
                if results:
                    natural = max(natural, toggle.sizeHint().width())
                frame.setMaximumWidth(min(MAX_W, natural + 40))
                col.addWidget(frame)
            col.addStretch(1)
            left = QVBoxLayout()
            left.addWidget(av)
            left.addStretch()
            row.addLayout(left)
            row.addLayout(col, 1)
            row.addStretch(0)


class ExampleButton(QPushButton):
    """Örnek soru düğmesi: metin sığmazsa ortadan kısaltılır (tooltip'te tam metin), asla kırpılmaz."""
    MAX_W = 380

    def __init__(self, text):
        super().__init__()
        self._full = text
        self.setToolTip(text)
        self.setMaximumWidth(self.MAX_W)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self._elide()

    def minimumSizeHint(self):
        return QSize(60, super().minimumSizeHint().height())

    def sizeHint(self):
        fm = self.fontMetrics()
        h = super().sizeHint().height()
        return QSize(min(self.MAX_W, fm.horizontalAdvance(self._full) + 40), h)

    def _elide(self):
        avail = max(40, self.width() - 36) if self.width() > 1 else self.MAX_W - 36
        self.setText(self.fontMetrics().elidedText(self._full, Qt.ElideRight, avail))

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        self._elide()


class EmptyState(QWidget):
    picked = Signal(str)

    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignCenter)
        lay.setSpacing(10)
        t = QLabel("Notlarına sor")
        t.setObjectName("welcomeTitle")
        t.setAlignment(Qt.AlignCenter)
        s = QLabel("Notlarında arama yapar, cevabı kaynaklarıyla birlikte verir.\n"
                   "Bir örnekle başla ya da kendi sorunu yaz.")
        s.setObjectName("muted")
        s.setAlignment(Qt.AlignCenter)
        lay.addStretch()
        lay.addWidget(t)
        lay.addWidget(s)
        lay.addSpacing(10)
        self._sub = s
        self._btns = []
        self._lay = lay
        lay.addStretch()

    def set_examples(self, qs):
        for b in self._btns:
            self._lay.removeWidget(b)
            b.deleteLater()
        self._btns = []
        if qs:
            self._sub.setText("Notlarında arama yapar, cevabı kaynaklarıyla birlikte verir.\n"
                              "Bir örnekle başla ya da kendi sorunu yaz.")
        else:
            self._sub.setText("Henüz not yok. Soldan bir klasör seç veya 'Not ekle' ile not ekle.")
        for q in qs:
            b = ExampleButton(q)
            b.setObjectName("example")
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, q=q: self.picked.emit(q))
            self._lay.insertWidget(self._lay.count() - 1, b, 0, Qt.AlignCenter)
            self._btns.append(b)


class ChatView(QScrollArea):
    suggestion = Signal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName("chat")
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._inner = QWidget()
        self._inner.setObjectName("chatInner")
        self._lay = QVBoxLayout(self._inner)
        self._lay.setContentsMargins(28, 24, 28, 24)
        self._lay.setSpacing(18)
        self._lay.addStretch()
        self.setWidget(self._inner)
        self._typing = None
        self._empty = EmptyState()
        self._empty.picked.connect(self.suggestion)
        self._lay.insertWidget(0, self._empty, 1)

    def set_examples(self, qs):
        self._empty.set_examples(qs)

    def _insert(self, w):
        self._empty.hide()
        self._lay.insertWidget(self._lay.count() - 1, w)
        self.scroll_bottom()

    def scroll_bottom(self):
        sb = self.verticalScrollBar()
        QTimer.singleShot(50, lambda: sb.setValue(sb.maximum()))

    def add(self, role, text, results=None):
        b = Bubble(role, text, results)
        self._insert(b)
        return b

    def show_typing(self):
        if self._typing is None:
            self._typing = Bubble("assistant", typing=True)
            self._insert(self._typing)

    def hide_typing(self):
        if self._typing is not None:
            self._lay.removeWidget(self._typing)
            self._typing.deleteLater()
            self._typing = None

    def clear(self):
        self.hide_typing()
        while self._lay.count() > 2:
            w = self._lay.takeAt(1).widget()
            if w:
                w.deleteLater()
        self._empty.show()

    def load_messages(self, messages):
        """Kayıtlı mesajları (history biçimi) yeniden çizer; kaynaklar açılır/kapanır kalır."""
        self.clear()
        for m in messages:
            res = [(SimpleNamespace(source=s.get("source", ""), heading=s.get("heading", ""),
                                    page=s.get("page"), text=s.get("text", "")),
                    float(s.get("score", 0.0))) for s in m.get("sources") or []]
            self.add(m.get("role", "assistant"), m.get("text", ""), res)
