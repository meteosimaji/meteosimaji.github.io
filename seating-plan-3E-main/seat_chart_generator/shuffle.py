"""Simple seat shuffling utilities."""

from __future__ import annotations

import random
from typing import Dict, List, Optional

from reportlab.lib import colors

from .models import Student


def simple_shuffle(
    students_data: List[Dict[str, str]],
    seat_rows: List[List[Optional[int]]],
    fixed: Dict[str, int] | None = None,
    empty_seats: List[int] | None = None,
    seed: int | None = None,
) -> List[Student]:
    """Shuffle students randomly without amidakuji.

    ``fixed`` maps student names to seat numbers that should not be
    changed. ``empty_seats`` is a list of seat numbers that must remain
    unassigned. Students marked as "休学" are skipped unless a fixed seat is
    provided for them.
    """

    rng = random.Random(seed)
    seats = [n for row in seat_rows for n in row if isinstance(n, int)]
    fixed = fixed or {}
    empty = set(empty_seats or [])

    assigned: List[Student] = []
    remaining_students: List[Dict[str, str]] = []
    remaining_seats = [s for s in seats if s not in empty]

    for data in students_data:
        name = data["name_kanji"]
        colour = colors.red if data.get("status") == "休学" else None
        if name in fixed:
            seat = fixed[name]
            if seat in remaining_seats:
                remaining_seats.remove(seat)
            assigned.append(
                Student(
                    seat_number=seat,
                    serial=data["serial"],
                    student_id=data["student_id"],
                    name_kanji=name,
                    name_kana=data["name_kana"],
                    gender=data.get("gender", "M"),
                    color=colour,
                )
            )
        else:
            if data.get("status") == "休学":
                # Skip students on leave unless a seat is fixed for them
                continue
            remaining_students.append(data)

    rng.shuffle(remaining_students)
    rng.shuffle(remaining_seats)
    if len(remaining_students) > len(remaining_seats):
        raise ValueError("席が足りません")

    for data, seat in zip(remaining_students, remaining_seats):
        colour = colors.red if data.get("status") == "休学" else None
        assigned.append(
            Student(
                seat_number=seat,
                serial=data["serial"],
                student_id=data["student_id"],
                name_kanji=data["name_kanji"],
                name_kana=data["name_kana"],
                gender=data.get("gender", "M"),
                color=colour,
            )
        )

    return assigned
