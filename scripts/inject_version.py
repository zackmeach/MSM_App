"""Inject a version string into APP_VERSION at build time.

Usage:  python scripts/inject_version.py --version 1.2.3

The script patches ``app/services/viewmodels.py`` so that the packaged binary
reports the correct version.  A leading ``v`` prefix is stripped
automatically (``v1.2.3`` → ``1.2.3``).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VIEWMODELS = ROOT / "app" / "services" / "viewmodels.py"

_VERSION_RE = re.compile(r'^APP_VERSION\s*=\s*"[^"]*"', re.MULTILINE)


def inject(version: str) -> None:
    text = VIEWMODELS.read_text(encoding="utf-8")
    new_line = f'APP_VERSION = "{version}"'

    if not _VERSION_RE.search(text):
        print(f"ERROR: Could not find APP_VERSION line in {VIEWMODELS}", file=sys.stderr)
        sys.exit(1)

    updated = _VERSION_RE.sub(new_line, text)
    VIEWMODELS.write_text(updated, encoding="utf-8")
    print(f"Injected APP_VERSION = \"{version}\" into {VIEWMODELS.relative_to(ROOT)}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject version into APP_VERSION constant")
    parser.add_argument("--version", required=True, help="Semantic version (e.g. 1.2.3 or v1.2.3)")
    args = parser.parse_args()

    version = args.version.lstrip("v")
    if not version:
        print("ERROR: Version string is empty after stripping 'v' prefix", file=sys.stderr)
        return 1

    inject(version)
    return 0


if __name__ == "__main__":
    sys.exit(main())
