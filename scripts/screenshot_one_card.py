"""Render a single CatalogMonsterCard with active count = 1 at large scale.

Used to debug badge clipping that's hard to see in the full catalog screenshot.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout  # noqa: E402

from app.bootstrap import bootstrap  # noqa: E402


def main() -> int:
    app = QApplication(sys.argv)
    bootstrap()  # configures resolver + applies pragmas

    from app.ui import themes  # noqa: E402
    from app.ui.widgets.catalog_monster_card import CatalogMonsterCard  # noqa: E402

    container = QWidget()
    container.setObjectName("pageCanvas")
    container.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    container.setStyleSheet(themes.build_stylesheet())
    container.resize(400, 500)

    layout = QVBoxLayout(container)
    layout.setContentsMargins(40, 40, 40, 40)

    card = CatalogMonsterCard(
        monster_id=1,
        name="Blipsqueak",
        image_path="",
        monster_type="wublin",
        is_placeholder=True,
    )
    card.set_active_count(1)
    layout.addWidget(card, alignment=Qt.AlignmentFlag.AlignCenter)

    container.show()
    for _ in range(15):
        QApplication.processEvents()

    out = ROOT / "screenshots" / "one_card.png"
    out.parent.mkdir(exist_ok=True)
    container.grab().save(str(out))
    print(f"Saved {out}")
    print(f"Card size: {card.size()}")
    print(f"Badge size: {card._badge.size()}, pos: {card._badge.pos()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
