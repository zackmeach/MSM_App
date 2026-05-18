"""Capture full-page screenshots of every UI page into docs/screenshots/.

Runs the real app against an ISOLATED temp data dir (a throwaway %APPDATA%),
so it never touches the user's real save state. Seeds a few representative
targets and partial egg progress so the Breed List (element pips), In-Work
rail, and Catalog active rail are all populated, then grabs each top-level
page (Home, Catalog, Settings) to a labeled PNG.

Run:
  python scripts/capture_ui_screenshots.py
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Use the native Windows platform plugin (NOT offscreen): offscreen has no
# font provider, so every glyph renders as a .notdef tofu box. The native
# plugin loads Segoe UI and renders text correctly even without a visible
# session; QWidget.grab() still works off-screen.

# Isolate the app's data dir so we never read or mutate the real save.
_TMP_APPDATA = tempfile.mkdtemp(prefix="msm_ui_shots_")
os.environ["APPDATA"] = _TMP_APPDATA

from PySide6.QtWidgets import QApplication  # noqa: E402

from app.bootstrap import bootstrap  # noqa: E402

OUT_DIR = ROOT / "docs" / "screenshots"
WINDOW_W, WINDOW_H = 1500, 950

# (nav index, catalog tab or None, filename, human label)
PAGES = [
    (0, None, "01-home.png", "Home — Breed List + In-Work Monsters"),
    (1, "wublin", "02-catalog-wublins.png", "Catalog — Wublins tab"),
    (1, "celestial", "03-catalog-celestials.png", "Catalog — Celestials tab"),
    (1, "amber", "04-catalog-amber-vessels.png", "Catalog — Amber Vessels tab"),
    (2, None, "05-settings.png", "Settings — Updates + UI options"),
]


def _pump(app: QApplication, times: int = 6) -> None:
    for _ in range(times):
        app.processEvents()


def _settle(app: QApplication, ms: int) -> None:
    """Advance the event loop for real wall-clock time so animations and the
    auto-fading toast fully finish — grabbing mid-animation double-renders text.
    """
    import time

    deadline = time.monotonic() + ms / 1000.0
    while time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.02)


def _seed_sample_state(window) -> None:
    """Add a spread of targets + partial egg progress so pages aren't empty."""
    service = window._service
    catalog = service.get_catalog_items()

    # Up to 2 real (non-placeholder) monsters per type, capped at 6 total.
    picked: list[int] = []
    per_type: dict[str, int] = {}
    for item in catalog:
        if item.is_placeholder:
            continue
        if per_type.get(item.monster_type, 0) >= 2:
            continue
        per_type[item.monster_type] = per_type.get(item.monster_type, 0) + 1
        picked.append(item.monster_id)
        if len(picked) >= 6:
            break

    for mid in picked:
        service.handle_add_target(mid)

    # Partially progress the first few breed-list eggs so In-Work populates
    # and progress bars/pips render in a realistic mid-completion state.
    state = service.get_app_state()
    for row in state.breed_list_rows[:5]:
        bumps = max(1, row.total_needed // 2)
        for _ in range(bumps):
            service.handle_increment_egg(row.egg_type_id)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    app = QApplication(sys.argv)
    app.setApplicationName("MSM Awakening Tracker")
    app.setOrganizationName("MSMAwakeningTracker")

    context = bootstrap()

    from app.ui.main_window import MainWindow

    window = MainWindow(context)
    window.resize(WINDOW_W, WINDOW_H)
    window.show()
    _pump(app)

    _seed_sample_state(window)
    # Seeding fires "Added … to tracker" toasts (2000ms + 400ms fade). Wait
    # them out so the UI is fully idle before any capture.
    _settle(app, 2800)

    saved: list[str] = []
    for index, catalog_tab, filename, label in PAGES:
        window._navigate_to(index)
        if catalog_tab is not None:
            window._catalog._browser._on_tab(catalog_tab)
        _settle(app, 600)
        pixmap = window.grab()
        out_path = OUT_DIR / filename
        if not pixmap.save(str(out_path), "PNG"):
            print(f"  FAILED to save {out_path}")
            return 1
        saved.append(f"  {filename:<16} {label}  ({pixmap.width()}x{pixmap.height()})")

    print(f"Saved {len(saved)} screenshots to {OUT_DIR}:")
    for line in saved:
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
