"""MSM Awakening Tracker — application entry point."""

import sys

from PySide6.QtWidgets import QApplication

from app.bootstrap import bootstrap


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("MSM Awakening Tracker")
    app.setOrganizationName("MSMAwakeningTracker")

    context = bootstrap()

    from app.ui.main_window import MainWindow

    window = MainWindow(context)
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
