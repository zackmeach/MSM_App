"""MSM Awakening Tracker — application entry point."""

import logging
import sys

from PySide6.QtCore import QLockFile
from PySide6.QtWidgets import QApplication, QMessageBox

from app.bootstrap import bootstrap

logger = logging.getLogger(__name__)


def _install_excepthook() -> None:
    """Log unhandled exceptions (incl. those escaping Qt slots) instead of
    letting them vanish in the windowed PyInstaller build."""
    default_hook = sys.excepthook

    def hook(exc_type, exc, tb):
        logging.getLogger("unhandled").error(
            "Unhandled exception", exc_info=(exc_type, exc, tb)
        )
        default_hook(exc_type, exc, tb)

    sys.excepthook = hook


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("MSM Awakening Tracker")
    app.setOrganizationName("MSMAwakeningTracker")

    _install_excepthook()

    # Single-instance guard: a second instance would contend for userstate.db
    # writes and show stale state.
    from app.bootstrap import _detect_data_dir

    lock = QLockFile(str(_detect_data_dir() / "app.lock"))
    if not lock.tryLock(0):
        QMessageBox.information(
            None,
            "MSM Awakening Tracker",
            "MSM Awakening Tracker is already running.",
        )
        return 0

    try:
        context = bootstrap()
    except Exception as exc:
        logger.exception("Fatal startup error")
        QMessageBox.critical(
            None,
            "MSM Awakening Tracker",
            "The app failed to start:\n\n"
            f"{exc}\n\n"
            "Details are in the log folder:\n"
            "%APPDATA%\\MSMAwakeningTracker\\logs",
        )
        return 1

    from app.ui.main_window import MainWindow

    window = MainWindow(context)
    window.show()

    rc = app.exec()

    # Close DB connections explicitly so WAL checkpoints at shutdown rather
    # than relying on crash recovery on next launch.
    for conn in (context.conn_content, context.conn_userstate):
        try:
            conn.close()
        except Exception:
            pass

    return rc


if __name__ == "__main__":
    sys.exit(main())
