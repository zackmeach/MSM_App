"""Render each top-level page at 1920x1080 and save PNGs to /tmp.

Used for visual-polish review. Boots the real app via bootstrap() so the
screenshots reflect actual seeded data, real ViewModels, and the live QSS.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QSize  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

OUT_DIR = ROOT / "screenshots"


def _grab(window, name: str) -> Path:
    QApplication.processEvents()
    time.sleep(0.15)  # let any pending layout settle
    QApplication.processEvents()
    pix = window.grab()
    OUT_DIR.mkdir(exist_ok=True)
    out = OUT_DIR / f"{name}.png"
    pix.save(str(out))
    return out


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("MSM Awakening Tracker")
    app.setOrganizationName("MSMAwakeningTracker")

    from app.bootstrap import bootstrap

    ctx = bootstrap()

    from app.ui.main_window import MainWindow

    window = MainWindow(ctx)
    window.resize(QSize(1920, 1080))
    window.show()

    # Pump events until the first paint completes.
    for _ in range(10):
        QApplication.processEvents()
        time.sleep(0.05)

    pages = [
        ("home",     0),
        ("catalog",  1),
        ("settings", 2),
    ]
    saved: list[Path] = []
    for name, index in pages:
        window._navigate_to(index)
        for _ in range(8):
            QApplication.processEvents()
            time.sleep(0.05)
        saved.append(_grab(window, name))

    print("Saved:")
    for p in saved:
        print(f"  {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
