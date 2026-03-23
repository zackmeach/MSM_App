"""Import official BBB Fan Kit images to replace generated placeholders.

Copies monster portrait squares and egg images from the Fan Kit directory
(Monsters/) into resources/images/, renaming to match the app's canonical
slug convention.  Optionally resizes to 256x256 for bundle efficiency.

Official assets from the BBB Fan Kit are used under their Fan Content Policy.
The generator (generate_assets.py) skips files that already exist, so these
imported images are preserved on subsequent runs.

Run:  python scripts/import_fankit_images.py
      python scripts/import_fankit_images.py --dry-run
      python scripts/import_fankit_images.py --no-resize
      python scripts/import_fankit_images.py --force
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESOURCES = ROOT / "resources"
FANKIT_DIR = ROOT / "Monsters"
PORTRAITS_DIR = FANKIT_DIR / "Monster Portrait Squares"
EGGS_DIR = FANKIT_DIR / "Monster Eggs"

NORMALIZED_DIR = ROOT / "pipeline" / "normalized"

# Fan Kit filenames that differ from the app's display_name.
FANKIT_NAME_OVERRIDES: dict[str, str] = {
    "Blow't": "Blow_t",
    "PomPom": "Pompom",
}

# Attempt to import Pillow for optional resizing.
try:
    from PIL import Image

    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False


# ── Helpers ────────────────────────────────────────────────────────────


def _canonical_slug(name: str) -> str:
    """Derive a canonical slug from a display name.

    Mirrors app/domain/models.py:canonical_slug() to avoid importing app code.
    """
    import re

    s = name.lower().replace(" ", "-")
    s = re.sub(r"[^a-z0-9\-]", "", s)
    s = re.sub(r"-{2,}", "-", s)
    return s.strip("-")


def _fankit_filename(display_name: str) -> str:
    """Resolve the Fan Kit filename for a given display name."""
    resolved = FANKIT_NAME_OVERRIDES.get(display_name, display_name)
    return f"{resolved}.png"


def _sha256(path: Path) -> str:
    """Compute SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _copy_image(
    src: Path,
    dest: Path,
    *,
    resize: bool = True,
    max_size: int = 256,
) -> bool:
    """Copy an image from src to dest, optionally resizing.

    Returns True if the file was written successfully.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)

    if resize and _HAS_PIL:
        img = Image.open(src)
        img.thumbnail((max_size, max_size), Image.LANCZOS)
        # Ensure RGBA mode for PNG transparency support
        if img.mode not in ("RGBA", "RGB"):
            img = img.convert("RGBA")
        img.save(dest, "PNG", optimize=True)
    else:
        shutil.copy2(src, dest)

    # Validate PNG magic bytes
    with open(dest, "rb") as f:
        magic = f.read(4)
    if magic != b"\x89PNG":
        dest.unlink(missing_ok=True)
        return False
    return True


# ── Main logic ─────────────────────────────────────────────────────────


def _import_monsters(
    *, dry_run: bool, force: bool, resize: bool
) -> tuple[int, int, int]:
    """Import monster portrait images. Returns (copied, skipped, missing)."""
    monsters_path = NORMALIZED_DIR / "monsters.json"
    if not monsters_path.exists():
        print(f"  ERROR: {monsters_path} not found")
        return 0, 0, 0

    monsters = json.loads(monsters_path.read_text(encoding="utf-8"))
    copied = skipped = missing = 0

    for monster in monsters:
        display_name = monster["display_name"]
        image_path = monster["image_path"]  # e.g. "images/monsters/zynth.png"
        dest = RESOURCES / image_path

        if dest.exists() and not force:
            skipped += 1
            continue

        fankit_file = PORTRAITS_DIR / _fankit_filename(display_name)
        if not fankit_file.exists():
            print(f"  MISS  {display_name} -> {fankit_file.name} not found")
            missing += 1
            continue

        if dry_run:
            print(f"  COPY  {fankit_file.name} -> {image_path}")
            copied += 1
            continue

        if _copy_image(fankit_file, dest, resize=resize):
            copied += 1
        else:
            print(f"  FAIL  {display_name} -> invalid PNG after copy")
            missing += 1

    return copied, skipped, missing


def _import_eggs(
    *, dry_run: bool, force: bool, resize: bool
) -> tuple[int, int, int]:
    """Import egg images. Returns (copied, skipped, missing)."""
    eggs_path = NORMALIZED_DIR / "eggs.json"
    if not eggs_path.exists():
        print(f"  ERROR: {eggs_path} not found")
        return 0, 0, 0

    eggs = json.loads(eggs_path.read_text(encoding="utf-8"))
    copied = skipped = missing = 0

    for egg in eggs:
        display_name = egg["display_name"]
        egg_image_path = egg["egg_image_path"]  # e.g. "images/eggs/noggin_egg.png"
        dest = RESOURCES / egg_image_path

        if dest.exists() and not force:
            skipped += 1
            continue

        fankit_file = EGGS_DIR / _fankit_filename(display_name)
        if not fankit_file.exists():
            print(f"  MISS  {display_name} -> {fankit_file.name} not found")
            missing += 1
            continue

        if dry_run:
            print(f"  COPY  {fankit_file.name} -> {egg_image_path}")
            copied += 1
            continue

        if _copy_image(fankit_file, dest, resize=resize):
            copied += 1
        else:
            print(f"  FAIL  {display_name} -> invalid PNG after copy")
            missing += 1

    return copied, skipped, missing


def _update_metadata(*, dry_run: bool) -> None:
    """Update assets.json, monsters.json, and eggs.json metadata."""
    if dry_run:
        return

    # --- Update assets.json ---
    assets_path = NORMALIZED_DIR / "assets.json"
    if assets_path.exists():
        assets = json.loads(assets_path.read_text(encoding="utf-8"))
        for asset in assets:
            dest = RESOURCES / asset["relative_path"]
            if dest.exists() and dest.stat().st_size > 500:
                asset["status"] = "official"
                asset["asset_source"] = "bbb_fan_kit"
                asset["is_placeholder"] = False
                asset["sha256"] = _sha256(dest)
                asset["byte_size"] = dest.stat().st_size
                asset["license_basis"] = "bbb_fan_kit_policy"
        assets_path.write_text(
            json.dumps(assets, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"  Updated {assets_path.name}")

    # --- Update monsters.json ---
    monsters_path = NORMALIZED_DIR / "monsters.json"
    if monsters_path.exists():
        monsters = json.loads(monsters_path.read_text(encoding="utf-8"))
        for monster in monsters:
            dest = RESOURCES / monster["image_path"]
            if dest.exists() and dest.stat().st_size > 500:
                monster["is_placeholder"] = False
                monster["asset_source"] = "bbb_fan_kit"
        monsters_path.write_text(
            json.dumps(monsters, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"  Updated {monsters_path.name}")

    # --- Update eggs.json ---
    eggs_path = NORMALIZED_DIR / "eggs.json"
    if eggs_path.exists():
        eggs = json.loads(eggs_path.read_text(encoding="utf-8"))
        for egg in eggs:
            dest = RESOURCES / egg["egg_image_path"]
            if dest.exists() and dest.stat().st_size > 500:
                egg["is_placeholder"] = False
                egg["asset_source"] = "bbb_fan_kit"
        eggs_path.write_text(
            json.dumps(eggs, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"  Updated {eggs_path.name}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import BBB Fan Kit images to replace placeholders."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be copied without writing files.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing images (default: skip).",
    )
    parser.add_argument(
        "--no-resize",
        action="store_true",
        help="Copy originals without resizing (default: resize to 256x256).",
    )
    args = parser.parse_args()

    resize = not args.no_resize
    if resize and not _HAS_PIL:
        print("  NOTE: Pillow not installed — copying originals without resize")
        resize = False

    if not FANKIT_DIR.exists():
        print(f"  ERROR: Fan Kit directory not found at {FANKIT_DIR}")
        print("  Download the BBB Fan Kit and extract to Monsters/ in the project root.")
        sys.exit(1)

    print(f"Fan Kit: {FANKIT_DIR}")
    print(f"Target:  {RESOURCES / 'images'}")
    if args.dry_run:
        print("Mode:    DRY RUN (no files will be written)\n")
    elif args.force:
        print("Mode:    FORCE (overwriting existing files)\n")
    else:
        print("Mode:    Normal (skipping existing files)\n")

    # Import monsters
    print("--- Monster Portraits ---")
    m_copied, m_skipped, m_missing = _import_monsters(
        dry_run=args.dry_run, force=args.force, resize=resize
    )
    print(f"  Copied: {m_copied}  Skipped: {m_skipped}  Missing: {m_missing}\n")

    # Import eggs
    print("--- Egg Images ---")
    e_copied, e_skipped, e_missing = _import_eggs(
        dry_run=args.dry_run, force=args.force, resize=resize
    )
    print(f"  Copied: {e_copied}  Skipped: {e_skipped}  Missing: {e_missing}\n")

    # Update metadata
    if m_copied + e_copied > 0 or args.force:
        print("--- Updating Metadata ---")
        _update_metadata(dry_run=args.dry_run)
        print()

    total_copied = m_copied + e_copied
    total_missing = m_missing + e_missing
    if total_missing:
        print(f"Done. {total_copied} images imported, {total_missing} missing.")
        sys.exit(1)
    else:
        print(f"Done. {total_copied} images imported successfully.")


if __name__ == "__main__":
    main()
