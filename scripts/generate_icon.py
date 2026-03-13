"""Generate a placeholder app icon in ICO format.

Creates a multi-resolution ICO with a simple MSM-themed design.
Should be replaced with an official icon before final release.

Run:  python scripts/generate_icon.py
"""

from __future__ import annotations

import math
import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ICON_PATH = ROOT / "resources" / "images" / "ui" / "app_icon.ico"


def _make_png(size: int) -> bytes:
    """Generate a PNG image for one icon resolution."""
    bg = (0x1E, 0x1E, 0x2E)
    accent = (0x89, 0xB4, 0xFA)
    green = (0xA6, 0xE3, 0xA1)

    rows = []
    cx, cy = size / 2, size / 2
    outer_r = size * 0.42
    inner_r = size * 0.28

    for y in range(size):
        row = bytearray()
        row.append(0)  # PNG filter byte
        for x in range(size):
            dx, dy = x - cx, y - cy
            dist = math.sqrt(dx * dx + dy * dy)
            if inner_r < dist <= outer_r:
                row.extend(accent)
                row.append(255)
            elif dist <= inner_r:
                note_cx, note_cy = cx - size * 0.05, cy + size * 0.05
                ndx, ndy = x - note_cx, y - note_cy
                note_dist = math.sqrt(ndx * ndx + ndy * ndy)
                if note_dist < size * 0.12:
                    row.extend(green)
                    row.append(255)
                elif abs(ndx - size * 0.08) < size * 0.025 and ndy < -size * 0.02 and ndy > -size * 0.22:
                    row.extend(green)
                    row.append(255)
                else:
                    row.extend(bg)
                    row.append(255)
            else:
                row.extend((0, 0, 0, 0))
        rows.append(bytes(row))

    raw = b"".join(rows)
    compressed = zlib.compress(raw)

    def _chunk(ctype: bytes, data: bytes) -> bytes:
        c = ctype + data
        crc = struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
        return struct.pack(">I", len(data)) + c + crc

    ihdr = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += _chunk(b"IHDR", ihdr)
    png += _chunk(b"IDAT", compressed)
    png += _chunk(b"IEND", b"")
    return png


def _make_ico(sizes: list[int]) -> bytes:
    """Create a multi-resolution ICO file from PNG images."""
    images = [(s, _make_png(s)) for s in sizes]

    header = struct.pack("<HHH", 0, 1, len(images))

    offset = 6 + 16 * len(images)
    entries = bytearray()
    data = bytearray()

    for size, png_data in images:
        w = 0 if size >= 256 else size
        h = 0 if size >= 256 else size
        entries.extend(struct.pack(
            "<BBBBHHII",
            w, h, 0, 0, 1, 32, len(png_data), offset,
        ))
        data.extend(png_data)
        offset += len(png_data)

    return header + bytes(entries) + bytes(data)


def main() -> None:
    ICON_PATH.parent.mkdir(parents=True, exist_ok=True)
    ico_data = _make_ico([16, 32, 48, 256])
    ICON_PATH.write_bytes(ico_data)
    print(f"  Created {ICON_PATH}")


if __name__ == "__main__":
    main()
