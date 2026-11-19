"""Ağır işleri arayüz iş parçacığının dışında çalıştıran basit QThread sarmalayıcı."""
from PySide6.QtCore import QThread, Signal


class Worker(QThread):
    done = Signal(object)    # başarılı sonuç
    failed = Signal(object)  # fırlatılan istisna

    def __init__(self, fn, *args, parent=None):
        super().__init__(parent)
        self._fn, self._args = fn, args

    def run(self):
        try:
            self.done.emit(self._fn(*self._args))
        except Exception as e:  # noqa: BLE001 - arayüze iletilir
            self.failed.emit(e)
