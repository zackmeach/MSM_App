"""Build automation — orchestrates the full release pipeline.

Steps:
  1. (Optional) Inject version string
  2. Run tests
  3. Regenerate bundled content.db
  4. Generate assets (placeholder, icon)
  5. Verify bundle integrity
  6. Package with PyInstaller
  7. (Optional) Build Inno Setup installer

Run:
  python scripts/build.py                          # standard build
  python scripts/build.py --version 1.2.0          # inject version first
  python scripts/build.py --installer              # build + installer
  python scripts/build.py --installer --version 1.2.0  # full release build
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VENV_PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"

ISCC_PATHS = [
    Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"),
    Path(r"C:\Program Files\Inno Setup 6\ISCC.exe"),
]


def _run(cmd: list[str], label: str) -> bool:
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    result = subprocess.run(cmd, cwd=str(ROOT))
    if result.returncode != 0:
        print(f"\nFAILED: {label} (exit code {result.returncode})")
        return False
    return True


def _find_iscc() -> Path | None:
    for p in ISCC_PATHS:
        if p.exists():
            return p
    return None


def _read_app_version() -> str:
    """Read current APP_VERSION from viewmodels.py as fallback."""
    text = (ROOT / "app" / "ui" / "viewmodels.py").read_text(encoding="utf-8")
    match = re.search(r'APP_VERSION\s*=\s*"([^"]*)"', text)
    return match.group(1) if match else "0.0.0"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build MSM Awakening Tracker")
    parser.add_argument("--version", help="Version to inject (e.g. 1.2.0)")
    parser.add_argument("--installer", action="store_true", help="Build Inno Setup installer after PyInstaller")
    args = parser.parse_args()

    python = str(VENV_PYTHON) if VENV_PYTHON.exists() else sys.executable

    # Step 0: Inject version if requested
    if args.version:
        if not _run(
            [python, "scripts/inject_version.py", "--version", args.version],
            f"Inject version {args.version}",
        ):
            return 1

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

    # Step 7: Build installer if requested
    if args.installer:
        if not has_pyinstaller:
            print("\nCannot build installer without PyInstaller output.")
            return 1

        iscc = _find_iscc()
        if not iscc:
            print("\nInno Setup not found. Install from https://jrsoftware.org/issetup.exe")
            print("Expected locations:")
            for p in ISCC_PATHS:
                print(f"  {p}")
            return 1

        version = args.version or _read_app_version()
        iss_path = ROOT / "installer" / "msm_tracker.iss"
        if not _run(
            [str(iscc), f"/DMyAppVersion={version}", str(iss_path)],
            "Build Inno Setup installer",
        ):
            return 1

        setup_exe = ROOT / "dist" / f"MSMAwakeningTracker-Setup-{version}.exe"
        print(f"\nInstaller: {setup_exe}")

    print(f"\n{'='*60}")
    print("  BUILD COMPLETE")
    print(f"{'='*60}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
