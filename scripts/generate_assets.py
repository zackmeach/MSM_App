"""Generate bundled assets: UI placeholder, ding audio, and placeholder PNGs
for every egg/monster image path referenced in the seed data.

Official assets from the BBB Fan Kit should replace the generated egg/monster
placeholders before final release. The generator will skip files that already
exist so hand-placed official assets are preserved.

Run:  python scripts/generate_assets.py
"""

from __future__ import annotations

import math
import sqlite3
import struct
import wave
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESOURCES = ROOT / "resources"


def _generate_placeholder_png(path: Path, size: int = 64, label: str = "?") -> None:
    """Write a minimal valid PNG with a solid dark square and centered initials."""
    bg = (0x45, 0x47, 0x5A)
    fg = (0x89, 0xB4, 0xFA)

    rows = []
    for y in range(size):
        row = bytearray()
        row.append(0)
        for x in range(size):
            cx, cy = x - size // 2, y - size // 2
            dist = math.sqrt(cx * cx + cy * cy)
            if dist < size * 0.35 and dist > size * 0.25:
                row.extend(fg)
            elif abs(cx) < 2 and size * 0.05 < cy < size * 0.2:
                row.extend(fg)
            elif abs(cx) < 3 and abs(cy) < 3 and cy > size * 0.22:
                row.extend(fg)
            else:
                row.extend(bg)
        rows.append(bytes(row))

    raw = b"".join(rows)
    compressed = zlib.compress(raw)

    def _chunk(ctype: bytes, data: bytes) -> bytes:
        c = ctype + data
        crc = struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
        return struct.pack(">I", len(data)) + c + crc

    ihdr = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += _chunk(b"IHDR", ihdr)
    png += _chunk(b"IDAT", compressed)
    png += _chunk(b"IEND", b"")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png)


def _generate_ding_wav(path: Path) -> None:
    """Write a short pleasant ding sound as a WAV file."""
    sample_rate = 44100
    duration = 0.3
    frequency = 880.0
    n_samples = int(sample_rate * duration)

    path.parent.mkdir(parents=True, exist_ok=True)

    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        frames = bytearray()
        for i in range(n_samples):
            t = i / sample_rate
            envelope = max(0.0, 1.0 - t / duration)
            sample = math.sin(2.0 * math.pi * frequency * t) * envelope * 0.6
            frames.extend(struct.pack("<h", int(sample * 32767)))
        wf.writeframes(bytes(frames))


def _generate_db_referenced_assets(db_path: Path) -> int:
    """Generate placeholder PNGs for every image path in the content DB.

    Skips files that already exist so hand-placed official assets are
    preserved. Returns the number of files created.
    """
    if not db_path.exists():
        print(f"  SKIP  content.db not found at {db_path} — run seed_content_db.py first")
        return 0

    conn = sqlite3.connect(str(db_path))
    paths: set[str] = set()

    for row in conn.execute("SELECT image_path FROM monsters WHERE image_path != ''"):
        paths.add(row[0])
    for row in conn.execute("SELECT egg_image_path FROM egg_types WHERE egg_image_path != ''"):
        paths.add(row[0])
    conn.close()

    created = 0
    for rel_path in sorted(paths):
        target = RESOURCES / rel_path
        if target.exists():
            continue
        _generate_placeholder_png(target, size=96)
        created += 1

    return created


def main() -> None:
    placeholder = RESOURCES / "images" / "ui" / "placeholder.png"
    _generate_placeholder_png(placeholder)
    print(f"  Created {placeholder}")

    ding = RESOURCES / "audio" / "ding.wav"
    _generate_ding_wav(ding)
    print(f"  Created {ding}")

    db_path = RESOURCES / "db" / "content.db"
    count = _generate_db_referenced_assets(db_path)
    if count:
        print(f"  Generated {count} placeholder image(s) for DB-referenced asset paths")
    else:
        print("  All DB-referenced asset paths already present (or DB not yet seeded)")

    print("Asset generation complete.")


if __name__ == "__main__":
    main()
