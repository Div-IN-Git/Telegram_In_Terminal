from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        print("PySide6 is not installed. Run `pip install -e .[gui]`.")
        return 1

    from bits_gui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("bits")
    window = MainWindow()
    qss = Path(__file__).parent / "theme" / "dark.qss"
    if qss.exists():
        app.setStyleSheet(qss.read_text(encoding="utf-8"))
    window.resize(1100, 680)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
