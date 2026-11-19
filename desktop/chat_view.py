"""Sohbet alanı: mesaj balonları, kaynak çipleri, yazıyor göstergesi ve boş durum."""
import math
import time
from types import SimpleNamespace

from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPainter, QTextOption
from PySide6.QtWidgets import (QFrame, QSizePolicy, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton,
                               QScrollArea, QTextBrowser, QToolButton, QVBoxLayout, QWidget)

from src.chunker import chunk_label

from . import style

COLUMN_MAX = 820      # ortalanmış içerik sütununun en büyük genişliği
MIN_MARGIN = 12       # pencere daraldıkça yan boşluk bu değere kadar küçülür
NARROW = 560          # sütun bundan darsa balonlar tüm genişliği kullanabilir
USER_FRAC, BOT_FRAC = 0.78, 0.88
AVATAR_W = 34         # avatar (24) + aralık (10)
class MsgView(QTextBrowser):
    """Salt okunur, seçilebilir mesaj metni; uzun sözcükler her yerden kırılır, yükseklik içeriğe eşit."""
    def __init__(self, text, markdown):
        super().__init__()
        self.setFrameShape(QFrame.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
        self.setOpenExternalLinks(True)
        self.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.LinksAccessibleByMouse)
        self.setContextMenuPolicy(Qt.DefaultContextMenu)
        self.document().setDocumentMargin(0)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        if markdown:
            self.setMarkdown(text)
        else:
            self.setPlainText(text)
        self.document().setDefaultStyleSheet("a { text-decoration: underline; }")

    def text(self):
        return self.toPlainText()

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, w):
        doc = self.document().clone()
        doc.setTextWidth(max(1, w))
        return int(math.ceil(doc.size().height())) + 2

    def sizeHint(self):
        return QSize(200, self.heightForWidth(200))

    def minimumSizeHint(self):
        return QSize(40, self.heightForWidth(self.width() or 200))

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        h = self.heightForWidth(self.viewport().width())
        if self.minimumHeight() != h:
            self.setMinimumHeight(h)
            self.setMaximumHeight(h)
            self.updateGeometry()




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
        self._user = user = role == "user"
        self._text = text
        self._colw = COLUMN_MAX
        self._results = bool(results)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)
        frame = QFrame()
        frame.setObjectName("bubbleUser" if user else "bubbleBot")
        self._frame = frame
        self._msg = self._toggle_btn = None
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(8)
        if typing:
            lay.addWidget(TypingDots())
        else:
            # Asistan cevabı Markdown (kalın, liste) olarak gösterilir; kullanıcı metni düz kalır
            msg = MsgView(text, markdown=not user)
            msg.setObjectName("msg")
            self._msg = msg
            lay.addWidget(msg)
        if results:
            # Kaynaklar varsayılan olarak gizli; tek düğmeyle açılır/kapanır
            n = len(results)
            toggle = QToolButton(text=f"▸ Kaynakları göster ({n})")
            toggle.setObjectName("chip")
            toggle.setCheckable(True)
            toggle.setCursor(Qt.PointingHandCursor)
            self._toggle_btn = toggle
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
                    self._frame.setMaximumWidth(self._max_w())
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
                # genişliğe göre doğru hesaplar; genişliği set_column_width sınırlar.
                col.addWidget(frame)
            col.addStretch(1)
            left = QVBoxLayout()
            left.addWidget(av)
            left.addStretch()
            row.addLayout(left)
            row.addLayout(col, 1)
            row.addStretch(0)
        self.set_column_width(COLUMN_MAX)

    def _max_w(self):
        colw = self._colw
        avail = colw if self._user else colw - AVATAR_W
        if colw < NARROW:
            return max(80, avail)
        return max(80, int((USER_FRAC if self._user else BOT_FRAC) * colw))

    def set_column_width(self, colw):
        """Sütun genişliğine göre balonun üst sınırını yeniden hesaplar; içeriğe göre daralır."""
        self._colw = colw
        mx = self._max_w()
        if self._msg is not None:
            fm = self._msg.fontMetrics()
            lines = self._msg.toPlainText().splitlines() or [" "]
            natural = max(fm.horizontalAdvance(line) for line in lines) + 6
            if self._toggle_btn is not None:
                natural = max(natural, self._toggle_btn.sizeHint().width())
            mx = min(mx, natural + 34)
        if self._open_sources():
            mx = self._max_w()
        self._frame.setMaximumWidth(mx)
        self._frame.updateGeometry()

    def _open_sources(self):
        return self._toggle_btn is not None and self._toggle_btn.isChecked()


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
    margins_changed = Signal(int, int)   # giriş çubuğunu sütunla hizalamak için (sol, sağ)

    def __init__(self):
        super().__init__()
        self.setObjectName("chat")
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._inner = QWidget()
        self._inner.setObjectName("chatInner")
        self._lay = QVBoxLayout(self._inner)
        self._lay.setContentsMargins(MIN_MARGIN, 24, MIN_MARGIN, 24)
        self._lay.setSpacing(18)
        self._lay.addStretch()
        self.setWidget(self._inner)
        self._typing = None
        self._empty = EmptyState()
        self._empty.picked.connect(self.suggestion)
        self._lay.insertWidget(0, self._empty, 1)

    def set_examples(self, qs):
        self._empty.set_examples(qs)

    def column_width(self):
        return max(1, self.viewport().width() - 2 * self._margin())

    def _margin(self):
        return max(MIN_MARGIN, (self.viewport().width() - COLUMN_MAX) // 2)

    def _relayout(self):
        m = self._margin()
        self._lay.setContentsMargins(m, 24, m, 24)
        colw = self.column_width()
        for i in range(self._lay.count()):
            w = self._lay.itemAt(i).widget()
            if isinstance(w, Bubble):
                w.set_column_width(colw)

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        self._relayout()
        m = self._margin()
        self.margins_changed.emit(m, m + self.width() - self.viewport().width())

    def _insert(self, w):
        self._empty.hide()
        if isinstance(w, Bubble):
            w.set_column_width(self.column_width())
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
            res = []
            for s in m.get("sources") or []:
                if not isinstance(s, dict):
                    continue
                try:
                    score = float(s.get("score", 0.0))
                except (TypeError, ValueError):
                    score = 0.0
                res.append((SimpleNamespace(source=s.get("source", ""), heading=s.get("heading", ""),
                                            page=s.get("page"), text=s.get("text", "")), score))
            self.add(m.get("role", "assistant"), str(m.get("text", "")), res)
