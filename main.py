"""
星衡量化平台 - 主入口
"""
import sys
import os
import traceback
from datetime import datetime
from pathlib import Path

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

if getattr(sys, "frozen", False):
    sys.path.insert(0, os.path.join(sys._MEIPASS))

from ui.main_window import MainWindow


def _get_runtime_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _log_startup_exception(exc: Exception):
    base_dir = _get_runtime_dir()
    log_dir = base_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "startup.log"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 启动异常\n")
        traceback.print_exc(file=f)
        f.write("\n")


def main():
    try:
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

        app = QApplication(sys.argv)
        app.setApplicationName("星衡量化平台")
        app.setStyle("Fusion")

        window = MainWindow()
        window.show()

        sys.exit(app.exec_())
    except Exception as exc:
        _log_startup_exception(exc)
        raise


if __name__ == "__main__":
    main()
