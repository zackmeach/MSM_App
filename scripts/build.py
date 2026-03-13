"""Build automation — orchestrates the full release pipeline.

Steps:
  1. Verify prerequisites (Python, PyInstaller, etc.)
  2. Run tests
  3. Regenerate bundled content.db
  4. Generate assets (placeholder, icon, ding)
  5. Verify bundle integrity
  6. Package with PyInstaller

Run:  python scripts/build.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VENV_PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"


def _run(cmd: list[str], label: str) -> bool:
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    result = subprocess.run(cmd, cwd=str(ROOT))
    if result.returncode != 0:
        print(f"\nFAILED: {label} (exit code {result.returncode})")
        return False
    return True


def main() -> int:
    python = str(VENV_PYTHON) if VENV_PYTHON.exists() else sys.executable

    steps: list[tuple[list[str], str]] = [
        ([python, "-m", "pytest", "tests/", "-v", "--tb=short"], "Run test suite"),
        ([python, "scripts/seed_content_db.py"], "Seed content database"),
        ([python, "scripts/generate_assets.py"], "Generate bundled assets"),
        ([python, "scripts/generate_icon.py"], "Generate app icon"),
        ([python, "scripts/verify_bundle.py"], "Verify resource bundle"),
    ]

    for cmd, label in steps:
        if not _run(cmd, label):
            return 1

    try:
        import PyInstaller  # noqa: F401
        has_pyinstaller = True
    except ImportError:
        has_pyinstaller = False

    if has_pyinstaller:
        if not _run(
            [python, "-m", "PyInstaller", "msm_tracker.spec", "--clean", "--noconfirm"],
            "Package with PyInstaller",
        ):
            return 1
        print(f"\nBuild output: {ROOT / 'dist' / 'MSMAwakeningTracker'}")
    else:
        print("\nPyInstaller not installed — skipping packaging step.")
        print("Install with: pip install pyinstaller")
        print("Then re-run this script, or run: pyinstaller msm_tracker.spec")

    print(f"\n{'='*60}")
    print("  BUILD COMPLETE")
    print(f"{'='*60}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
