"""Seat layout utilities and defaults."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

# Default seat layout with a simple 10x5 grid (5 columns x 10 rows).
# Numbers represent seat identifiers while ``None`` indicates that no seat
# exists at that position.
DEFAULT_SEAT_ROWS: List[List[int]] = [
    list(range(1, 6)),
    list(range(6, 11)),
    list(range(11, 16)),
    list(range(16, 21)),
    list(range(21, 26)),
    list(range(26, 31)),
    list(range(31, 36)),
    list(range(36, 41)),
    list(range(41, 46)),
    list(range(46, 51)),
]


def generate_layout(rows: int, cols: int) -> List[List[int]]:
    """Generate a rectangular seat layout.

    Seat numbers are assigned sequentially from left to right, top to bottom.
    """

    layout: List[List[int]] = []
    seat = 1
    for _ in range(rows):
        row = list(range(seat, seat + cols))
        layout.append(row)
        seat += cols
    return layout


def load_layout(path: str | Path = "seat_layout.json") -> List[List[Optional[int]]]:
    """Load seat layout from JSON file or return default layout.

    Legacy entries marked with strings (such as former teacher desks) are
    treated as empty positions.
    """
    p = Path(path)
    if p.is_file():
        with p.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        for r, row in enumerate(data):
            for c, cell in enumerate(row):
                if not isinstance(cell, int) and cell is not None:
                    data[r][c] = None
        return data
    return DEFAULT_SEAT_ROWS


def save_layout(
    layout: List[List[Optional[int]]],
    path: str | Path = "seat_layout.json",
) -> None:
    """Save layout to JSON file."""
    p = Path(path)
    with p.open("w", encoding="utf-8") as fh:
        json.dump(layout, fh, ensure_ascii=False, indent=2)
