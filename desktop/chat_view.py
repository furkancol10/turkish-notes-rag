"""Sohbet alanı: mesaj balonları ve açılır kaynak listesi."""
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QFrame, QLabel, QPlainTextEdit, QScrollArea, QToolButton,
                               QVBoxLayout, QWidget)


class SourceItem(QWidget):
    """Tek kaynak: başlığa tıklayınca parça metni açılır."""
    def __init__(self, i, chunk, score):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.btn = QToolButton(text=f"[{i}] {chunk.source} / {chunk.heading}  (skor {score:.2f})")
        self.btn.setCheckable(True)
        self.btn.setArrowType(Qt.RightArrow)
        self.btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.btn.setStyleSheet("QToolButton{border:none;text-align:left;}")
        self.body = QPlainTextEdit(chunk.text, readOnly=True)
        self.body.setMaximumHeight(160)
        self.body.setVisible(False)
        self.btn.toggled.connect(self._toggle)
        lay.addWidget(self.btn)
        lay.addWidget(self.body)

    def _toggle(self, on):
        self.btn.setArrowType(Qt.DownArrow if on else Qt.RightArrow)
        self.body.setVisible(on)


class Bubble(QFrame):
    def __init__(self, role, text, results=None):
        super().__init__()
        user = role == "user"
        self.setStyleSheet(
            f"Bubble{{background:palette({'button' if user else 'alternate-base'});"
            "border:1px solid palette(mid);border-radius:10px;}")
        lay = QVBoxLayout(self)
        who = QLabel("Sen" if user else "Asistan")
        who.setStyleSheet("font-weight:bold;")
        msg = QLabel(text)
        msg.setWordWrap(True)
        msg.setTextInteractionFlags(Qt.TextSelectableByMouse)
        lay.addWidget(who)
        lay.addWidget(msg)
        if results:
            lay.addWidget(QLabel("Kaynaklar:"))
            for i, (c, s) in enumerate(results, 1):
                lay.addWidget(SourceItem(i, c, s))


class ChatView(QScrollArea):
    def __init__(self):
        super().__init__()
        self.setWidgetResizable(True)
        self._inner = QWidget()
        self._lay = QVBoxLayout(self._inner)
        self._lay.addStretch()
        self.setWidget(self._inner)

    def add(self, role, text, results=None):
        b = Bubble(role, text, results)
        self._lay.insertWidget(self._lay.count() - 1, b)
        QTimer.singleShot(50, lambda: self.verticalScrollBar().setValue(
            self.verticalScrollBar().maximum()))
        return b

    def clear(self):
        while self._lay.count() > 1:
            w = self._lay.takeAt(0).widget()
            if w:
                w.deleteLater()
