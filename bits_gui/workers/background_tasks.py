from __future__ import annotations

try:
    from PySide6.QtCore import QObject, QRunnable, Signal, Slot
except ImportError:  # pragma: no cover
    QObject = object
    QRunnable = object
    Signal = lambda *args, **kwargs: None
    Slot = lambda *args, **kwargs: (lambda fn: fn)


class WorkerSignals(QObject):
    finished = Signal(object)
    failed = Signal(str)


class ApiTask(QRunnable):
    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    @Slot()
    def run(self):
        try:
            self.signals.finished.emit(self.fn(*self.args, **self.kwargs))
        except Exception as exc:
            self.signals.failed.emit(str(exc))
